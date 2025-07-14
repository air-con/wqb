


import os
import logging
import requests
import json
import hashlib
import asyncio
import nest_asyncio
from celery.schedules import crontab
from .celery import app
from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest, ListAppTableRecordResponse, BatchDeleteAppTableRecordRequest, BatchDeleteAppTableRecordResponse
import lark_oapi as lark

# Import the correct session manager and URL
from wqb.tasks import get_wqb_session
from wqb.wqb_urls import URL_SIMULATIONS

# Apply nest_asyncio to allow running an event loop inside another (e.g., Celery worker)
nest_asyncio.apply()

# Configure logger
logger = logging.getLogger(__name__)




def get_lark_client():
    if not all([os.environ.get("LARK_APP_TOKEN"), os.environ.get("LARK_TABLE_ID"), os.environ.get("LARK_APP_ID"), os.environ.get("LARK_APP_SECRET")]):
        logger.warning(
            "Lark client for periodic task is not fully configured. "
            "Please set LARK_APP_ID, LARK_APP_SECRET, LARK_APP_TOKEN, and LARK_TABLE_ID environment variables."
        )
        return None
    return lark.Client.builder().app_id(os.environ.get("LARK_APP_ID")).app_secret(os.environ.get("LARK_APP_SECRET")).build()


def get_all_records(lark_client, app_token, table_id):
    """Fetch all records from the table."""
    records = []
    page_token = None
    while True:
        request = ListAppTableRecordRequest.builder() \
            .app_token(app_token) \
            .table_id(table_id) \
            .page_size(500)
        if page_token:
            request = request.page_token(page_token)
        
        response: ListAppTableRecordResponse = lark_client.bitable.v1.app_table_record.list(request.build())

        if not response.success():
            logger.error(f"Lark API operation 'list_records' failed. Code: {response.code}, Msg: {response.msg}")
            break
        
        if response.data.items:
            records.extend(response.data.items)
        
        if response.data.has_more:
            page_token = response.data.page_token
        else:
            break
    return records

def batch_delete_lark_records(lark_client, app_token, table_id, record_ids):
    """Delete multiple records from the Lark table in a single batch request."""
    if not record_ids:
        return
    
    request = BatchDeleteAppTableRecordRequest.builder() \
        .app_token(app_token) \
        .table_id(table_id) \
        .request_body(record_ids) \
        .build()
    
    response: BatchDeleteAppTableRecordResponse = lark_client.bitable.v1.app_table_record.batch_delete(request)
    
    if not response.success():
        logger.error(f"Failed to batch delete records. Code: {response.code}, Msg: {response.msg}")
    else:
        logger.info(f"Successfully deleted {len(record_ids)} records.")


def get_status_for_single_item(record):
    """Determines the task status for a single JSON object based on the record's state and traceback."""
    state = record.fields.get("state")
    if state == "SUCCESS":
        return "SUCCESS"

    traceback = record.fields.get("traceback", "").lower()
    technical_error_keywords = [
        "requestexception", "maxretryerror", "timeout", "connectionerror", 
        "httperror", "sslerror", "proxyerror"
    ]

    if any(keyword in traceback for keyword in technical_error_keywords):
        return "PENDING"
    
    return "FAILED"

async def _get_child_status_async(session, child_id):
    """Asynchronously gets the status of a single child simulation."""
    url = f"{URL_SIMULATIONS}/{child_id}"
    try:
        resp = await session.retry('GET', url, max_tries=5, delay_key_error=1.0)
        if resp and resp.ok:
            sim_data = resp.json()
            return sim_data.get("status")
    except Exception as e:
        logger.error(f"Error fetching simulation status for {child_id}: {e}")
    return None

async def _get_detailed_statuses_async(wqb_session, child_ids):
    """Asynchronously gets all child statuses and determines the final status list."""
    tasks = [_get_child_status_async(wqb_session, child_id) for child_id in child_ids]
    child_statuses = await asyncio.gather(*tasks)
    
    final_statuses = []
    for status in child_statuses:
        if status == "ERROR":
            final_statuses.append("FAILED")
        else:
            final_statuses.append("PENDING")
    return final_statuses

@app.task
def check_and_process_task_results():
    """
    Checks task results from Lark, sends status to an API, and deletes the records in a batch.
    """
    logger.info("Starting to check and process task results.")
    lark_client = get_lark_client()
    if not lark_client:
        logger.error("Cannot process task results, Lark client not available.")
        return

    app_token = os.environ.get("LARK_APP_TOKEN")
    table_id = os.environ.get("LARK_TABLE_ID")
    
    records = get_all_records(lark_client, app_token, table_id)
    if not records:
        logger.info("No records to process.")
        return
        
    logger.info(f"Found {len(records)} records to process.")

    updates = []
    processed_lark_record_ids = []
    
    wqb_session = get_wqb_session(logger)

    for record in records:
        lark_record_id = record.record_id
        original_input_str = record.fields.get("input")
        response_json_str = record.fields.get("response_json")

        if not original_input_str:
            logger.warning(f"Skipping record {lark_record_id} due to missing input.")
            continue

        try:
            input_data = json.loads(original_input_str)
            is_array = isinstance(input_data, list)

            items_to_process = input_data if is_array else [input_data]
            item_statuses = []

            if is_array:
                if not response_json_str:
                    logger.warning(f"Skipping array record {lark_record_id} due to missing response_json.")
                    continue
                
                response_data = json.loads(response_json_str)
                top_level_status = response_data.get("status")

                if top_level_status in ["COMPLETE", "WARNING"]:
                    item_statuses = ["SUCCESS"] * len(items_to_process)
                else:
                    child_ids = response_data.get("children", [])
                    if len(child_ids) != len(items_to_process):
                        logger.error(f"Mismatch between input items and child simulations for {lark_record_id}")
                        continue
                    
                    item_statuses = asyncio.run(_get_detailed_statuses_async(wqb_session, child_ids))
            else:
                status = get_status_for_single_item(record)
                item_statuses.append(status)

            for i, item in enumerate(items_to_process):
                canonical_json_str = json.dumps(item, sort_keys=True, ensure_ascii=False)
                identifier = hashlib.md5(canonical_json_str.encode('utf-8')).hexdigest()
                updates.append({
                    "record_id": identifier,
                    "status": item_statuses[i]
                })
            
            processed_lark_record_ids.append(lark_record_id)

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Could not process record {lark_record_id}. Error: {e}", exc_info=True)
            continue

    if not updates:
        logger.info("No valid records to send to the status API.")
        return

    API_ENDPOINT = os.environ.get("STATUS_API_ENDPOINT")
    API_KEY = os.environ.get("STATUS_API_KEY")

    if not API_ENDPOINT or not API_KEY:
        logger.error("STATUS_API_ENDPOINT or STATUS_API_KEY environment variables not set. Cannot send status.")
        return

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    try:
        response = requests.post(API_ENDPOINT, json=updates, headers=headers, timeout=30)
        response.raise_for_status()
        
        logger.info(f"Successfully sent status for {len(updates)} tasks to API.")

        batch_delete_lark_records(lark_client, app_token, table_id, processed_lark_record_ids)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send status updates to API. Error: {e}")


app.conf.beat_schedule = {
    'check-results-every-two-hours': {
        'task': 'wqb.periodic_tasks.check_and_process_task_results',
        'schedule': crontab(minute='0', hour='*/2'),
        'options': {'queue': 'periodic_queue'}
    },
}



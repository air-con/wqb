

import os
import logging
import requests
import json
import hashlib
from celery import Celery
from celery.schedules import crontab
from lark_oapi.api.bitable.v1 import ListAppTableRecordRequest, ListAppTableRecordResponse, BatchDeleteAppTableRecordRequest, BatchDeleteAppTableRecordResponse
import lark_oapi as lark

# Configure logger
logger = logging.getLogger(__name__)

app = Celery('wqb')
app.config_from_object('celeryconfig')


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


def get_status_from_record(record):
    """Determines the task status based on the record's state and traceback."""
    state = record.fields.get("state")
    if state == "SUCCESS":
        return "SUCCESS"

    traceback = record.fields.get("traceback", "").lower()
    # Keywords indicating a technical, possibly transient, error
    technical_error_keywords = [
        "requestexception", "maxretryerror", "timeout", "connectionerror", 
        "httperror", "sslerror", "proxyerror"
    ]

    if any(keyword in traceback for keyword in technical_error_keywords):
        return "PENDING" # It's a technical issue, so we mark it for retry/later check
    
    return "FAILED" # Otherwise, it's a business logic failure


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

    for record in records:
        lark_record_id = record.record_id
        original_input_str = record.fields.get("input")

        if not original_input_str:
            logger.warning(f"Skipping record {lark_record_id} due to missing input.")
            continue

        try:
            input_data = json.loads(original_input_str)
            
            # Determine if the input is a list (JSON array) or a dict (JSON object)
            items_to_process = input_data if isinstance(input_data, list) else [input_data]
            
            status = get_status_from_record(record)

            for item in items_to_process:
                # Dump each item to a string with sorted keys for a canonical representation
                canonical_json_str = json.dumps(item, sort_keys=True, ensure_ascii=False)
                # Generate the identifier from the canonical string
                identifier = hashlib.md5(canonical_json_str.encode('utf-8')).hexdigest()
                
                updates.append({
                    "record_id": identifier,
                    "status": status
                })

            processed_lark_record_ids.append(lark_record_id)

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Could not process record {lark_record_id}. Invalid input JSON or other error: {e}")
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

        # If API call is successful, batch delete the records from Lark
        batch_delete_lark_records(lark_client, app_token, table_id, processed_lark_record_ids)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send status updates to API. Error: {e}")


# Configure Celery Beat schedule
app.conf.beat_schedule = {
    'check-results-every-two-hours': {
        'task': 'wqb.periodic_tasks.check_and_process_task_results',
        'schedule': crontab(minute='0', hour='*/2'), # Every 2 hours
    },
}


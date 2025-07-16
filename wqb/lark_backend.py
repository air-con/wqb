import os
import json
import logging
import asyncio
from celery.backends.base import BaseBackend
from lark_oapi.api.bitable.v1 import (
    AppTableRecord,
    BatchCreateAppTableRecordRequest,
    BatchCreateAppTableRecordRequestBody,
    BatchCreateAppTableRecordResponse,
)

import lark_oapi as lark

# Import WQB session and URL
from wqb.tasks import get_wqb_session
from wqb.wqb_urls import URL_SIMULATIONS

# Configure logger
logger = logging.getLogger(__name__)

class LarkBackend(BaseBackend):
    def __init__(self, app, **kwargs):
        super().__init__(app, **kwargs)
        self.app_token = os.environ.get("LARK_APP_TOKEN")
        self.table_id = os.environ.get("LARK_TABLE_ID")

        if not all([self.app_token, self.table_id, os.environ.get("LARK_APP_ID"), os.environ.get("LARK_APP_SECRET")]):
            logger.warning(
                "LarkBackend is not fully configured. "
                "Please set LARK_APP_ID, LARK_APP_SECRET, LARK_APP_TOKEN, and LARK_TABLE_ID environment variables."
            )
            self.lark_client = None
        else:
            self.lark_client = (
                lark.Client.builder()
                .app_id(os.environ.get("LARK_APP_ID"))
                .app_secret(os.environ.get("LARK_APP_SECRET"))
                .build()
            )

    def _log_lark_error(self, response, operation):
        error_message = (
            f"Lark API operation '{operation}' failed. "
            f"Code: {response.code}, Msg: {response.msg}, Log ID: {response.get_log_id()}\n"
            f"Response Body: {json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        )
        logger.error(error_message)

    def _build_record_fields(self, task_id, item_input, item_state, item_success, response_data, traceback=None, error=None, exception=None):
        """A centralized helper to build the dictionary of fields for a Lark record."""
        return {
            "task_id": task_id,
            "state": item_state,
            "success": str(item_success),
            "input": json.dumps(item_input, ensure_ascii=False, default=str),
            "response_json": json.dumps(response_data, ensure_ascii=False, default=str),
            "traceback": str(traceback) if traceback else "",
            "error": str(error) if error else "",
            "exception": str(exception) if exception else "",
        }

    async def _get_child_simulation_status(self, session, child_id):
        url = f"{URL_SIMULATIONS}/{child_id}"
        try:
            resp = await session.retry('GET', url, max_tries=5, delay_key_error=1.0)
            if resp and resp.ok:
                return resp.json() # Return the full response
        except Exception as e:
            logger.error(f"Error fetching simulation status for {child_id}: {e}")
        return None # Return None on failure

    async def _store_result_async(self, task_id, result, state, traceback=None):
        if not self.lark_client:
            return

        results_list = result if isinstance(result, list) else [result]
        records_to_create = []

        for res in results_list:
            if not isinstance(res, dict):
                logger.warning(f"Skipping result of unexpected type: {type(res)}")
                fields = self._build_record_fields(task_id, {}, "FAILED", False, {'error': f'Result item is not a dictionary, but {type(res)}'})
                records_to_create.append(AppTableRecord.builder().fields(fields).build())
                continue

            input_data = res.get('input', '')
            response_json = res.get('response_json', {})
            is_array_input = isinstance(input_data, list)

            if is_array_input:
                top_level_status = response_json.get("status")
                items_to_process = input_data

                if top_level_status in ["COMPLETE", "WARNING"]:
                    for item in items_to_process:
                        fields = self._build_record_fields(task_id, item, "SUCCESS", True, response_json)
                        records_to_create.append(AppTableRecord.builder().fields(fields).build())
                
                elif top_level_status and 'children' in response_json:
                    wqb_session = get_wqb_session(logger)
                    child_ids = response_json.get("children", [])
                    if len(child_ids) == len(items_to_process):
                        child_tasks = [self._get_child_simulation_status(wqb_session, child_id) for child_id in child_ids]
                        child_results = await asyncio.gather(*child_tasks)

                        for i, item in enumerate(items_to_process):
                            child_res = child_results[i]
                            child_status = child_res.get("status") if child_res else "ERROR"
                            item_state = "SUCCESS" if child_status in ["COMPLETE", "WARNING"] else "FAILED"
                            item_success = item_state == "SUCCESS"
                            if child_status == "CANCELLED": item_state = "FAILED"

                            fields = self._build_record_fields(task_id, item, item_state, item_success, child_res or {})
                            records_to_create.append(AppTableRecord.builder().fields(fields).build())
                    else: # Fallback for mismatch
                        for item in items_to_process:
                            fields = self._build_record_fields(task_id, item, "FAILED", False, response_json, error="Child ID mismatch")
                            records_to_create.append(AppTableRecord.builder().fields(fields).build())
                else: # Fallback for other array failures
                    for item in items_to_process:
                        fields = self._build_record_fields(task_id, item, "FAILED", False, response_json, error=res.get('error'), exception=res.get('exception'), traceback=traceback)
                        records_to_create.append(AppTableRecord.builder().fields(fields).build())
            else:
                fields = self._build_record_fields(task_id, input_data, state, res.get('success', False), response_json, traceback, res.get('error'), res.get('exception'))
                records_to_create.append(AppTableRecord.builder().fields(fields).build())

        if records_to_create:
            # Correctly build the request body using the dedicated builder
            request_body = BatchCreateAppTableRecordRequestBody.builder().records(records_to_create).build()
            request = BatchCreateAppTableRecordRequest.builder().app_token(self.app_token).table_id(self.table_id).request_body(request_body).build()
            response: BatchCreateAppTableRecordResponse = self.lark_client.bitable.v1.app_table_record.batch_create(request)
            if not response.success():
                self._log_lark_error(response, "batch_create_records")

    def store_result(self, task_id, result, state, traceback=None, request=None, **kwargs):
        if self.lark_client:
            asyncio.run(self._store_result_async(task_id, result, state, traceback))

    def get_state(self, task_id):
        return "PENDING" 

    def get_result(self, task_id):
        return None

    def get_traceback(self, task_id):
        return None

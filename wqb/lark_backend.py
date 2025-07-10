import os
import json
import logging
import threading
from celery.backends.base import BaseBackend
from lark_oapi.api.bitable.v1 import (
    AppTableRecord,
    CreateAppTableRecordRequest,
    ListAppTableRecordRequest,
    ListAppTableRecordResponse,
    UpdateAppTableRecordRequest,
    UpdateAppTableRecordResponse,
    CreateAppTableRecordResponse,
)

import lark_oapi as lark

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
                # The log level is now controlled by the global Celery logger
                .build()
            )

    def _log_lark_error(self, response, operation):
        error_message = (
            f"Lark API operation '{operation}' failed. "
            f"Code: {response.code}, Msg: {response.msg}, Log ID: {response.get_log_id()}\n"
            f"Response Body: {json.dumps(json.loads(response.raw.content), indent=4, ensure_ascii=False)}"
        )
        logger.error(error_message)

    def _get_record_by_task_id(self, task_id):
        if not self.lark_client:
            return None

        request: ListAppTableRecordRequest = (
            ListAppTableRecordRequest.builder()
            .app_token(self.app_token)
            .table_id(self.table_id)
            .filter(f'CurrentValue.[task_id] = "{task_id}"')
            .build()
        )

        response: ListAppTableRecordResponse = self.lark_client.bitable.v1.app_table_record.list(request)

        if not response.success():
            self._log_lark_error(response, "list_records")
            return None

        if not response.data.items:
            return None

        return response.data.items[0]

    def _store_result_async(self, task_id, result, state, traceback=None):
        if not self.lark_client:
            return

        # The 'result' from Celery is now the dictionary from _format_sim_result
        if not isinstance(result, dict):
            logger.warning(f"Received result of unexpected type: {type(result)}")
            # Fallback for unexpected result types
            result = {'error': 'Result is not a dictionary', 'response_json': str(result)}

        record = self._get_record_by_task_id(task_id)

        fields = {
            "task_id": task_id,
            "state": state,
            "traceback": str(traceback) if traceback else "",
            # Safely get values from the result dictionary
            "success": str(result.get('success', False)),
            "error": str(result.get('error', '')),
            "input": str(result.get('input', '')),
            "response_json": str(result.get('response_json', '')),
            "exception": str(result.get('exception', '')),
        }

        # Filter out any keys that are not actual columns in your table if necessary
        # For now, we assume all keys in 'fields' are valid column names.

        app_table_record = AppTableRecord.builder().fields(fields).build()

        if record:
            request: UpdateAppTableRecordRequest = (
                UpdateAppTableRecordRequest.builder()
                .app_token(self.app_token)
                .table_id(self.table_id)
                .record_id(record.record_id)
                .request_body(app_table_record)
                .build()
            )
            response: UpdateAppTableRecordResponse = self.lark_client.bitable.v1.app_table_record.update(request)
            if not response.success():
                self._log_lark_error(response, "update_record")
        else:
            request: CreateAppTableRecordRequest = (
                CreateAppTableRecordRequest.builder()
                .app_token(self.app_token)
                .table_id(self.table_id)
                .request_body(app_table_record)
                .build()
            )
            response: CreateAppTableRecordResponse = self.lark_client.bitable.v1.app_table_record.create(request)
            if not response.success():
                self._log_lark_error(response, "create_record")

    def store_result(self, task_id, result, state, traceback=None, request=None, **kwargs):
        if self.lark_client:
            thread = threading.Thread(target=self._store_result_async, args=(task_id, result, state, traceback))
            thread.start()

    def get_state(self, task_id):
        record = self._get_record_by_task_id(task_id)
        return record.fields.get("state") if record and hasattr(record, 'fields') else None

    def get_result(self, task_id):
        record = self._get_record_by_task_id(task_id)
        return record.fields.get("result") if record and hasattr(record, 'fields') else None

    def get_traceback(self, task_id):
        record = self._get_record_by_task_id(task_id)
        return record.fields.get("traceback") if record and hasattr(record, 'fields') else None
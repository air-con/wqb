from celery import Celery, Task
from . import wqb_session
from celery.signals import worker_process_init
from celery.utils.log import get_task_logger
import threading
import os
import time

# Create a Celery app instance
app = Celery('wqb')

# Load the configuration from the celeryconfig.py file
app.config_from_object('celeryconfig')

# Create a lock to ensure only one simulation task runs at a time per worker process
simulation_lock = threading.Lock()

# Get the logger for this module
logger = get_task_logger(__name__)

def _log_response(logger, response):
    """Tries to log the response as JSON, falls back to text."""
    try:
        logger.debug(f"Response JSON: {response.json()}")
    except Exception:
        logger.debug(f"Response text: {response.text}")

def _format_sim_result(logger, input_data, response):
    """
    Formats the simulation result for the backend based on the response.
    """
    if response is None or not response.ok:
        logger.warning(f"Invalid response for input: {str(input_data)[:200]}...")
        return {
            'success': False,
            'error': 'Invalid response from simulation server',
            'input': input_data,
            'response_json': response.text if response else 'No response'
        }

    _log_response(logger, response)

    try:
        response_json = response.json()
        status = response_json.get('status', 'UNKNOWN').upper()

        if status in ('COMPLETE', 'WARNING'):
            return {'success': True, 'input': input_data, 'response_json': response_json}
        else:
            logger.warning(f"Simulation finished with non-success status: {status}")
            return {
                'success': False,
                'error': f'Simulation failed with status: {status}',
                'input': input_data,
                'response_json': response_json
            }
    except ValueError:  # JSONDecodeError
        logger.error("Failed to decode JSON response.", exc_info=True)
        return {
            'success': False,
            'error': 'Failed to decode JSON response',
            'input': input_data,
            'response_json': response.text
        }

# 改进的全局会话管理
class GlobalWQBSessionManager:
    def __init__(self):
        self._session = None
        self._session_lock = threading.Lock()
        self._created_at = None
        self._process_id = None
        self._session_timeout = 3600 * 4  # 4小时后重新创建会话
    
    def get_session(self, task_logger=None):
        current_process_id = os.getpid()
        current_time = time.time()
        
        log = task_logger or logger

        with self._session_lock:
            # 检查是否需要创建新会话
            need_new_session = (
                self._session is None or
                self._process_id != current_process_id or  # 进程重启了
                (self._created_at and current_time - self._created_at > self._session_timeout)  # 会话过期
            )
            
            if need_new_session:
                log.debug(f"Creating new WQB session for process {current_process_id}")
                self._session = wqb_session.WQBSession(logger=log)
                self._created_at = current_time
                self._process_id = current_process_id
                log.debug(f"WQB session created successfully for process {current_process_id}")
            else:
                log.debug(f"Reusing existing WQB session for process {current_process_id}")
        
        return self._session

# 全局会话管理器
session_manager = GlobalWQBSessionManager()

@worker_process_init.connect
def init_worker(**kwargs):
    """Worker进程初始化时预创建WQB会话"""
    logger.info(f"Worker process {os.getpid()} initializing...")
    session_manager.get_session()
    logger.info(f"Worker process {os.getpid()} initialized with WQB session")

def get_wqb_session(task_logger=None):
    """获取WQB会话实例"""
    return session_manager.get_session(task_logger)

class BaseSimulationTask(Task):
    """
    任务基类，确保在任务开始前获取锁，在任务结束后（无论成功、失败或重试）释放锁。
    """
    abstract = True

    @property
    def logger(self):
        return get_task_logger(self.name)

    def __call__(self, *args, **kwargs):
        simulation_lock.acquire()
        self.logger.debug(f"Acquired lock.")
        try:
            # bind=True makes self the task instance
            return super().__call__(*args, **kwargs)
        finally:
            simulation_lock.release()
            self.logger.debug(f"Released lock.")

@app.task(base=BaseSimulationTask, bind=True)
def simulate_task(self, alpha_or_multi_alpha):
    """
    A Celery task to run a single simulation for an alpha or a multi_alpha.
    """
    try:
        self.logger.info(f"Starting single simulation.")
        wqbs = get_wqb_session(self.logger)
        
        import asyncio
        response = asyncio.run(
            wqbs.simulate(
                alpha_or_multi_alpha,
                max_tries=range(600),
                log=str(self.request.id),
            )
        )

        result = _format_sim_result(self.logger, alpha_or_multi_alpha, response)
        
        self.logger.info(f"Finished single simulation. Success: {result.get('success')}")
        return result

    except Exception as e:
        self.logger.error(f"Task failed unexpectedly: {e}", exc_info=True)
        raise



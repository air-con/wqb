# tasks.py - 在原始版本基础上的最小修改
from celery import Celery, Task
from . import wqb_session
from .backend import save_failed_simulation
from celery.signals import worker_process_init
import threading
import logging
import os
import time
import nest_asyncio

nest_asyncio.apply()

# Create a Celery app instance
app = Celery('wqb')

# Load the configuration from the celeryconfig.py file
app.config_from_object('celeryconfig')

# Create a lock to ensure only one simulation task runs at a time per worker process
simulation_lock = threading.Lock()

logger = logging.getLogger(__name__)

# 改进的全局会话管理
class GlobalWQBSessionManager:
    def __init__(self):
        self._session = None
        self._session_lock = threading.Lock()
        self._created_at = None
        self._process_id = None
        self._session_timeout = 3600  # 1小时后重新创建会话
    
    def get_session(self):
        current_process_id = os.getpid()
        current_time = time.time()
        
        with self._session_lock:
            # 检查是否需要创建新会话
            need_new_session = (
                self._session is None or
                self._process_id != current_process_id or  # 进程重启了
                (self._created_at and current_time - self._created_at > self._session_timeout)  # 会话过期
            )
            
            if need_new_session:
                logger.info(f"Creating new WQB session for process {current_process_id}")
                self._session = wqb_session.WQBSession()
                self._created_at = current_time
                self._process_id = current_process_id
                logger.info(f"WQB session created successfully for process {current_process_id}")
            else:
                logger.debug(f"Reusing existing WQB session for process {current_process_id}")
        
        return self._session

# 全局会话管理器
session_manager = GlobalWQBSessionManager()

@worker_process_init.connect
def init_worker(**kwargs):
    """Worker进程初始化时预创建WQB会话"""
    logger.info(f"Worker process {os.getpid()} initializing...")
    session_manager.get_session()
    logger.info(f"Worker process {os.getpid()} initialized with WQB session")

def get_wqb_session():
    """获取WQB会话实例"""
    return session_manager.get_session()

class BaseSimulationTask(Task):
    abstract = True

    def before_start(self, task_id, args, kwargs):
        # Acquire the lock before starting the task
        simulation_lock.acquire()
        logger.info(f"Task {task_id} acquired lock.")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        # Release the lock after the task returns (success or failure)
        simulation_lock.release()
        logger.info(f"Task {task_id} released lock.")

# 保持原始的任务定义，只替换会话管理
@app.task(base=BaseSimulationTask)
def simulate_alpha_task(alphas):
    """
    A Celery task to run a simulation for a list of alphas sequentially.
    """
    wqbs = get_wqb_session()  # 使用改进的会话管理
    multi_alphas = wqb_session.to_multi_alphas(alphas, 10)

    async def run_simulations_sequentially():
        for multi_alpha in multi_alphas:
            logger.info(f"Simulating multi_alpha: {multi_alpha}")
            response = await wqbs.simulate(multi_alpha)
            if response is None or not response.ok:
                logger.warning(f"Failed to simulate multi_alpha: {multi_alpha}")
                save_failed_simulation(multi_alpha)

    import asyncio
    asyncio.run(run_simulations_sequentially())

    return f"Processed {len(alphas)} alphas sequentially."

@app.task(base=BaseSimulationTask)
def simulate_single_alpha_task(alpha):
    """
    A Celery task to run a simulation for a single alpha.
    """
    wqbs = get_wqb_session()  # 使用改进的会话管理

    async def run_single_simulation():
        logger.info(f"Simulating single alpha: {alpha}")
        response = await wqbs.simulate(alpha)
        if response is None or not response.ok:
            logger.warning(f"Failed to simulate single alpha: {alpha}")
            save_failed_simulation(alpha)

    import asyncio
    asyncio.run(run_single_simulation())

    return f"Processed single alpha."

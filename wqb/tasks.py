# tasks.py - 改进版本
from celery import Celery, Task
from . import wqb_session
from .backend import save_failed_simulation
from celery.signals import worker_process_init
import threading
import logging
import os
import time

app = Celery('wqb')
app.config_from_object('celeryconfig')

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
    
    def invalidate_session(self):
        """手动失效会话，强制下次创建新会话"""
        with self._session_lock:
            logger.info("Invalidating WQB session")
            self._session = None
            self._created_at = None

# 全局会话管理器
session_manager = GlobalWQBSessionManager()

@worker_process_init.connect
def init_worker(**kwargs):
    """Worker进程初始化时预创建WQB会话"""
    logger.info(f"Worker process {os.getpid()} initializing...")
    # 预创建会话
    session_manager.get_session()
    logger.info(f"Worker process {os.getpid()} initialized with WQB session")

def get_wqb_session():
    """获取WQB会话实例"""
    return session_manager.get_session()

# 任务锁 - 每个进程一个
simulation_lock = threading.Lock()

class BaseSimulationTask(Task):
    abstract = True

    def before_start(self, task_id, args, kwargs):
        simulation_lock.acquire()
        logger.info(f"Task {task_id} acquired lock in process {os.getpid()}")

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        simulation_lock.release()
        logger.info(f"Task {task_id} released lock in process {os.getpid()}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理"""
        logger.error(f"Task {task_id} failed: {exc}")
        # 如果是认证相关错误，失效会话
        if "auth" in str(exc).lower() or "login" in str(exc).lower():
            session_manager.invalidate_session()

@app.task(base=BaseSimulationTask, bind=True)
def simulate_alpha_task(self, alphas):
    """改进的模拟任务"""
    process_id = os.getpid()
    task_id = self.request.id
    
    logger.info(f"Task {task_id} starting in process {process_id}")
    
    try:
        wqbs = get_wqb_session()
        multi_alphas = wqb_session.to_multi_alphas(alphas, 10)
        
        logger.info(f"Task {task_id}: Processing {len(multi_alphas)} multi_alphas")

        async def run_simulations_sequentially():
            for i, multi_alpha in enumerate(multi_alphas):
                logger.info(f"Task {task_id}: Simulating multi_alpha {i+1}/{len(multi_alphas)}")
                
                try:
                    response = await wqbs.simulate(multi_alpha)
                    if response is None or not response.ok:
                        logger.warning(f"Task {task_id}: Failed to simulate multi_alpha: {multi_alpha}")
                        save_failed_simulation(multi_alpha)
                except Exception as e:
                    logger.error(f"Task {task_id}: Exception during simulation: {e}")
                    # 如果是认证错误，失效会话
                    if "auth" in str(e).lower() or "401" in str(e):
                        session_manager.invalidate_session()
                    save_failed_simulation(multi_alpha)

        import asyncio
        asyncio.run(run_simulations_sequentially())
        
        logger.info(f"Task {task_id}: Completed processing {len(alphas)} alphas")
        return f"Process {process_id}: Processed {len(alphas)} alphas sequentially."
        
    except Exception as e:
        logger.error(f"Task {task_id}: Task failed with error: {e}")
        raise

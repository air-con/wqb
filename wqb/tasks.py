from celery import Celery, Task
from . import wqb_session
from .backend import save_failed_simulation
import threading
import logging

# Create a Celery app instance
app = Celery('wqb')

# Load the configuration from the celeryconfig.py file
app.config_from_object('celeryconfig')

# Create a lock to ensure only one simulation task runs at a time per worker process
simulation_lock = threading.Lock()

logger = logging.getLogger(__name__)

# 全局变量存储session
wqb_session_instance = None

@worker_process_init.connect
def init_worker(**kwargs):
    """Worker进程初始化时创建WQB会话"""
    global wqb_session_instance
    wqb_session_instance = wqb_session.WQBSession()
    logger.info("Initialized WQBSession for worker process")

def get_wqb_session():
    """获取WQB会话实例"""
    global wqb_session_instance
    if wqb_session_instance is None:
        wqb_session_instance = wqb_session.WQBSession()
        logger.info("Created WQBSession instance")
    return wqb_session_instance

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


@app.task(base=BaseSimulationTask)
def simulate_alpha_task(alphas):
    """
    A Celery task to run a simulation for a list of alphas sequentially.
    """
    wqbs = get_wqb_session()
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
    wqbs = get_wqb_session()

    async def run_single_simulation():
        logger.info(f"Simulating single alpha: {alpha}")
        response = await wqbs.simulate(alpha)
        if response is None or not response.ok:
            logger.warning(f"Failed to simulate single alpha: {alpha}")
            save_failed_simulation(alpha)

    import asyncio
    asyncio.run(run_single_simulation())

    return f"Processed single alpha."

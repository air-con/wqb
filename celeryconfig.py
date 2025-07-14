from wqb.logging_config import setup_logging
from kombu import Queue

# Initialize logging as the first step
setup_logging()

import os

# 基础配置
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
result_backend = 'wqb.lark_backend.LarkBackend'
task_imports = ('wqb.tasks', 'wqb.periodic_tasks')

# 定义队列
task_queues = (
    Queue('celery', routing_key='celery'),
    Queue('periodic_queue', routing_key='periodic'),
)

# 定义任务路由
task_routes = {
    'wqb.tasks.simulate_task': {'queue': 'celery', 'routing_key': 'celery'},
    'wqb.tasks.simulate_tasks': {'queue': 'celery', 'routing_key': 'celery'},
    'wqb.periodic_tasks.check_and_process_task_results': {'queue': 'periodic_queue', 'routing_key': 'periodic'},
}


# 任务安全配置
task_acks_late = True
worker_prefetch_multiplier = 1
task_reject_on_worker_lost = True

# 超时配置
task_annotations = {
    'wqb.tasks.simulate_task': {
        # 不设置 rate_limit，让任务跑满卡槽
        'soft_time_limit': None,
        'time_limit': 1200,       # 20分钟硬超时，强制终止
        # 'retry_policy': {
        #     'max_retries': 2,
        #     'interval_start': 60,
        #     'interval_step': 60,
        # }
    },
    'wqb.tasks.simulate_tasks': {
        'soft_time_limit': None,
        'time_limit': 1200,       # 20分钟硬超时
        # 'retry_policy': {
        #     'max_retries': 3,
        #     'interval_start': 30,
        # }
    }
}

# 其他优化配置
worker_max_tasks_per_child = 2000
worker_max_memory_per_child = 300000  # 300MB

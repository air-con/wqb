from wqb.logging_config import setup_logging

# Initialize logging as the first step
setup_logging()

import os

# 基础配置
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
result_backend = 'wqb.lark_backend.LarkBackend'
task_imports = ('wqb.tasks',)

# 任务安全配置
task_acks_late = True
task_acks_on_failure_or_timeout = True
worker_prefetch_multiplier = 1
task_reject_on_worker_lost = True

# 超时配置
task_annotations = {
    'wqb.tasks.simulate_task': {
        'soft_time_limit': None,
        'time_limit': 6000,       # 1小时硬超时
    }
}

# 其他优化配置
worker_max_tasks_per_child = 2000
worker_max_memory_per_child = 300000  # 300MB
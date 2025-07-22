from wqb.logging_config import setup_logging
from kombu import Exchange, Queue
import os

# Initialize logging as the first step
setup_logging()

# --- Dynamic Queue Configuration ---
# Get the queue name from the existing CELERY_QUEUE environment variable, with 'default' as a fallback.
CELERY_QUEUE_NAME = os.environ.get('CELERY_QUEUE', 'default')

# 基础配置
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
result_backend = 'wqb.lark_backend.LarkBackend'
task_imports = ('wqb.tasks',)
worker_direct = False

# 启用任务优先级
# See: https://docs.celeryq.dev/en/stable/userguide/routing.html#priority
task_create_missing_queues = False # It's a good practice to avoid creating queues by mistake.
task_queues = (
    Queue(
        CELERY_QUEUE_NAME,
        Exchange(CELERY_QUEUE_NAME),  # 👈 显式使用同名 direct exchange
        routing_key=CELERY_QUEUE_NAME,
        # The routing key is now explicitly set in task_routes
        queue_arguments={'x-max-priority': 10},
        durable=True,
        auto_delete=False
    ),
)

# Explicitly route all tasks to our defined queue.
# This is more robust than relying on `task_default_queue`.
task_default_queue = CELERY_QUEUE_NAME
task_routes = {
    'wqb.tasks.*': {
        'queue': CELERY_QUEUE_NAME,
        'routing_key': CELERY_QUEUE_NAME,
    }
}


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

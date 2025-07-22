from wqb.logging_config import setup_logging
from kombu import Exchange, Queue
import os

# Initialize logging as the first step
setup_logging()

# --- Dynamic Queue Configuration ---
# Get the queue name from the existing CELERY_QUEUE environment variable, with 'default' as a fallback.
CELERY_QUEUE_NAME = os.environ.get('CELERY_QUEUE', 'default')

# 新增：紧急队列名称配置
URGENT_QUEUE_NAME = os.environ.get('URGENT_QUEUE', 'urgent')

# 新增：是否启用紧急队列（可选，用于性能优化）
ENABLE_URGENT_QUEUE = os.environ.get('ENABLE_URGENT_QUEUE', 'true').lower() == 'true'

# 基础配置 - 修改为Redis
broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = 'wqb.lark_backend.LarkBackend'
task_imports = ('wqb.tasks',)

# 启用任务优先级 - 修改为Redis双队列模式
task_create_missing_queues = False # It's a good practice to avoid creating queues by mistake.

# 动态队列配置
if ENABLE_URGENT_QUEUE:
    task_queues = (
        # 紧急队列 - 高优先级
        Queue(
            URGENT_QUEUE_NAME,
            Exchange(URGENT_QUEUE_NAME),
            routing_key=URGENT_QUEUE_NAME,
        ),
        # 普通队列
        Queue(
            CELERY_QUEUE_NAME,
            Exchange(CELERY_QUEUE_NAME),
            routing_key=CELERY_QUEUE_NAME,
        ),
    )
else:
    # 只使用普通队列（性能优化选项）
    task_queues = (
        Queue(
            CELERY_QUEUE_NAME,
            Exchange(CELERY_QUEUE_NAME),
            routing_key=CELERY_QUEUE_NAME,
        ),
    )

# Explicitly route all tasks to our defined queue.
# This is more robust than relying on `task_default_queue`.
task_routes = {
    'wqb.tasks.*': {
        'queue': CELERY_QUEUE_NAME,
        'routing_key': CELERY_QUEUE_NAME,
    }
}

# 默认队列设置
task_default_queue = CELERY_QUEUE_NAME

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

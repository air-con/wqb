from wqb.logging_config import setup_logging
from kombu import Exchange, Queue
import os

# Initialize logging as the first step
setup_logging()

# --- Dynamic Queue Configuration ---
CELERY_QUEUE_NAME = os.environ.get('CELERY_QUEUE', 'default')

# 基础配置
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')
result_backend = 'wqb.lark_backend.LarkBackend'
task_imports = ('wqb.tasks',)

# === 最全面的禁用配置 ===
# 禁用所有自动队列创建
task_create_missing_queues = False
worker_direct = False
worker_enable_remote_control = False

# 禁用所有事件系统
worker_send_task_events = False
task_send_sent_event = False
task_track_started = False
task_ignore_result = False
worker_hijack_root_logger = False

# 禁用集群功能
worker_disable_rate_limits = True
worker_pool_restarts = False

# 明确设置所有事件相关配置为 False
CELERY_SEND_EVENTS = False
CELERY_SEND_TASK_EVENTS = False
CELERY_TASK_SEND_SENT_EVENT = False
CELERY_WORKER_SEND_TASK_EVENTS = False

# 队列配置 - 只定义我们需要的队列
task_queues = (
    Queue(
        CELERY_QUEUE_NAME,
        Exchange(CELERY_QUEUE_NAME, type='direct'),
        routing_key=CELERY_QUEUE_NAME,
        queue_arguments={'x-max-priority': 10},
        durable=True,
        auto_delete=False
    ),
)

# 强制所有配置指向我们的队列
task_default_queue = CELERY_QUEUE_NAME
task_default_exchange = CELERY_QUEUE_NAME
task_default_exchange_type = 'direct'
task_default_routing_key = CELERY_QUEUE_NAME

# 强制路由 - 确保所有任务都去指定队列
task_routes = {
    '*': {  # 使用 '*' 匹配所有任务，而不只是 'wqb.tasks.*'
        'queue': CELERY_QUEUE_NAME,
        'routing_key': CELERY_QUEUE_NAME,
    }
}

# 其余配置
task_acks_late = True
task_acks_on_failure_or_timeout = True
worker_prefetch_multiplier = 1
task_reject_on_worker_lost = True

task_annotations = {
    'wqb.tasks.simulate_task': {
        'soft_time_limit': None,
        'time_limit': 6000,
    }
}

worker_max_tasks_per_child = 2000
worker_max_memory_per_child = 300000

# === 最后的保险措施：强制覆盖任何可能的事件配置 ===
import sys
if 'celery' in sys.modules:
    from celery import current_app
    current_app.conf.update(
        worker_send_task_events=False,
        task_send_sent_event=False,
        task_track_started=False,
        worker_enable_remote_control=False,
        worker_direct=False,
    )

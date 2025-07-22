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

# === 精准的事件和结果配置 ===

# 1. 我们关心任务的结果，这样才会触发 result_backend
#    因此，我们不能设置 task_ignore_result = True

# 2. 我们不希望任务在“已发送”时就产生事件
task_send_sent_event = False

# 3. 我们不追踪“任务已开始”的状态，这可以节省一次通信
task_track_started = False

# 4. 我们不向监控工具（如Flower）发送通用的任务事件，这是节省流量的关键
worker_send_task_events = False

# 5. 禁用远程控制和广播，这是节省流量的另一个关键
worker_enable_remote_control = False
worker_direct = False

# 禁用集群功能
worker_disable_rate_limits = True
worker_pool_restarts = False

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
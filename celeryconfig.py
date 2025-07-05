import os

# Get the broker URL from an environment variable.
# Default to a local RabbitMQ instance if the variable is not set.
broker_url = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')

# The backend used to store task results (optional, but good practice)
# We can use RabbitMQ for this as well.
result_backend = 'rpc://'

# The name of the task module to import
task_imports = ('wqb.tasks',)

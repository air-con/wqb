# RabbitMQ broker URL
# This URL points to the RabbitMQ service defined in docker-compose.yml
broker_url = 'amqp://guest:guest@rabbitmq:5672//'

# The backend used to store task results (optional, but good practice)
# We can use RabbitMQ for this as well.
result_backend = 'rpc://'

# The name of the task module to import
task_imports = ('wqb.tasks',)

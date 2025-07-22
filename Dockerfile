FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements and install them
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy the rest of the application code
COPY . .

# Install the wqb library in editable mode
RUN pip install -e .
# 设置环境变量强制禁用事件
ENV CELERY_SEND_EVENTS=false
ENV CELERY_SEND_TASK_EVENTS=false
ENV CELERY_TASK_SEND_SENT_EVENT=false
ENV CELERY_WORKER_SEND_TASK_EVENTS=false

# Set the default command.
# This syntax uses the value of $CELERY_CONCURRENCY if it's set, otherwise defaults to 3.
# The ["/bin/sh", "-c", "..."] format is used to ensure the environment variable is evaluated.
# CMD ["/bin/sh", "-c", "exec celery -A wqb.tasks worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-3} -Q ${CELERY_QUEUE:-celery}"]
# CMD ["/bin/sh", "-c", "exec celery -A wqb.tasks worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-3}"]

CMD ["/bin/sh", "-c", "exec celery -A wqb.tasks worker \
    --loglevel=info \
    --concurrency=${CELERY_CONCURRENCY:-3} \
    --without-gossip \
    --without-mingle \
    --without-heartbeat \
    --pool=prefork \
    -O fair"]

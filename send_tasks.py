# send_tasks.py
import os
from celery import Celery

# --- Configuration --- #
# Explicitly get the broker URL from environment variables.
BROKER_URL = os.environ.get('CELERY_BROKER_URL')
if not BROKER_URL:
    raise ValueError("CELERY_BROKER_URL environment variable not set. Please configure the broker URL.")

# Create a Celery app instance configured with the broker URL.
app = Celery('wqb', broker=BROKER_URL)

# --- Task Definition --- #

# The name of the task to be called
task_name = 'wqb.tasks.simulate_task'

# --- Prepare Task Payload --- #

# This is an example payload. It can be a single alpha (dict) 
# or a list of alphas for a multi-alpha simulation.
alpha_payload = {
    'type': 'REGULAR',
    'settings': {
        'instrumentType': 'EQUITY',
        'region': 'USA',
        'universe': 'TOP3000',
        'delay': 1,
        'decay': 6,
        'neutralization': 'SUBINDUSTRY',
        'truncation': 0.08,
        'pasteurization': 'ON',
        'unitHandling': 'VERIFY',
        'nanHandling': 'OFF',
        'language': 'FASTEXPR',
        'visualization': False
    },
    'regular': 'close - open',
}

# --- Send Task --- #

print(f"Sending task '{task_name}' to the default queue...")

task = app.send_task(task_name, args=[alpha_payload])

print(f"Task sent with ID: {task.id}")
print("\nDone sending tasks.")

# WQB Task Processing Library

This project provides a robust, scalable library for interacting with the WorldQuant BRAIN (WQB) platform. It is designed as an asynchronous task processing system using Celery, allowing for efficient, background execution of WQB simulations.

![wqb logo](https://github.com/rocky-d/wqb/blob/master/img/wqb_1024x1024.png)

## Core Features

- **Asynchronous by Design:** Leverages Celery to manage a queue of simulation tasks, enabling high-throughput, non-blocking processing.
- **Resilient WQB Session:** Features an intelligent, persistent session manager that handles WQB API authentication automatically.
- **Lark/Feishu Result Backend:** Uses a custom Celery result backend to store detailed task results in a Lark Bitable, providing a structured and easily accessible record of all simulations.
- **Dockerized for Production:** Fully containerized with Docker and Docker Compose for easy, repeatable, and scalable deployments.
- **Configurable:** Key operational parameters (concurrency, queue name) and all integration credentials are managed via environment variables.

## How It Works

The system consists of two main components:

1.  **The Celery Worker (This Project):** A Python application that listens for simulation tasks on a message queue. When a task is received, the worker communicates with the WQB API to run the simulation and stores the result in the configured Lark Bitable.

2.  **The Task Producer (Your Script):** Any application that can send a message to the Celery queue. We provide a `send_tasks.py` script as a basic example of how to dispatch a `simulate_task` to the worker.

## Getting Started

### As a Deployed Service (Docker)

This is the primary way to use the project for its task processing capabilities.

For detailed instructions on how to configure, build, and run the Celery worker using Docker, please refer to the official deployment guide:

**[>> WQB Docker Deployment Guide <<](DOCKER_README.md)**

### As a Library User (Local Usage)

If you only need to use the WQB session manager or other utility functions locally without the Celery worker.

**Installation:**
```sh
python -m pip install wqb
```

**Usage:**
```python
from wqb import WQBSession

# The session handles authentication automatically.
# Note: Ensure any required authentication details are handled by your local environment.
wqbs = WQBSession()

# Make authenticated API calls
resp = wqbs.search_operators()
print(resp.ok)
```
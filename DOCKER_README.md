# WQB Project - Docker Deployment Guide

This guide provides instructions on how to deploy the WQB project using Docker and Docker Compose.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Logging](#logging)
- [Deployment Steps](#deployment-steps)
- [Verifying the Deployment](#verifying-the-deployment)
- [Sending Tasks](#sending-tasks)
- [Stopping the Services](#stopping-the-services)

## Prerequisites

- **Docker Engine:** [Install Docker](https://docs.docker.com/engine/install/)
- **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)

## Configuration

The project uses a `.env` file to manage environment variables.

1.  **Create a `.env` file:**
    Copy the example file to create your own configuration:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:**
    Update the variables with your actual credentials and settings:

    ```dotenv
    # Domain for the WorldQuant BRAIN API
    API_DOMAIN=api.worldquantbrain.com

    # Your personal WorldQuant BRAIN API key
    API_KEY=your_api_key_here

    # Connection URL for the Celery message broker (e.g., RabbitMQ)
    CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//

    # (Optional) Number of concurrent Celery worker processes
    CELERY_CONCURRENCY=8

    # (Optional) Lark Bitable configuration for the result backend
    LARK_APP_ID=your_lark_app_id
    LARK_APP_SECRET=your_lark_app_secret
    LARK_APP_TOKEN=your_lark_app_token
    LARK_TABLE_ID=your_lark_table_id
    ```

## Logging

This project uses a centralized logging system configured in `wqb/logging_config.py`.
- **Log Rotation:** Logs are automatically rotated daily, and the last 3 days of logs are kept.
- **Log Files:** All logs are stored in the `logs/` directory at the project root.
- **Console Output:** Logs are also streamed to the console (stdout) for real-time monitoring.

When running with Docker, you can view the consolidated logs from all services using:
```bash
docker-compose logs -f
```

## Deployment Steps

You can either build the Docker images from your local source code or pull pre-built images from a container registry.

### 1. Build and Run Locally (for Development)

This is ideal for testing local changes.

```bash
docker-compose up --build -d
```
- `--build`: Rebuilds the Docker images before starting.
- `-d`: Runs containers in the background.

### 2. Run from a Registry (for Production)

For production, modify `docker-compose.yml` to use an `image` directive instead of `build`.

```yaml
# docker-compose.yml (production example)
services:
  worker:
    image: your-registry/your-image-name:latest # Replace with your image
    # ... other configurations
  app:
    image: your-registry/your-image-name:latest # Replace with your image
    # ... other configurations
```

Then, start the services:
```bash
docker-compose up -d
```

## Verifying the Deployment

1.  **Check Container Status:**
    ```bash
    docker-compose ps
    ```

2.  **View Logs:**
    ```bash
    docker-compose logs -f worker
    ```

3.  **Access Flower UI:**
    The Flower monitoring dashboard is available at [http://localhost:5555](http://localhost:5555).

## Sending Tasks

Tasks are sent to the Celery workers by executing a script from within the `app` container.

1.  **Access the `app` container:**
    ```bash
    docker-compose exec app bash
    ```

2.  **Run a Python script to send tasks:**
    From the shell inside the container, you can run a script like `send_tasks.py` or execute Python code directly.

    **Example: Sending a single simulation task**
    The primary task for running simulations is `wqb.tasks.simulate_task`.

    ```python
    # Inside a Python script or interpreter in the 'app' container
    from wqb.tasks import simulate_task

    # Define the alpha or multi-alpha data
    alpha_data = {
        'type': 'REGULAR',
        'settings': {
            'instrumentType': 'EQUITY',
            'region': 'USA',
            'universe': 'TOP3000',
            'delay': 1,
            'decay': 13,
            'neutralization': 'INDUSTRY',
            'truncation': 0.13,
            'pasteurization': 'ON',
            'unitHandling': 'VERIFY',
            'nanHandling': 'OFF',
            'language': 'FASTEXPR',
            'visualization': False
        },
        'regular': 'open / close',
    }

    # Send the task to the Celery queue
    task = simulate_task.delay(alpha_data)
    print(f"Sent task with ID: {task.id}")
    ```

    **Example: Sending multiple tasks concurrently**
    You can use the `wqb.tasks.simulate_tasks` task to process a list of simulation targets concurrently.

    ```python
    from wqb.tasks import simulate_tasks

    # A list of simulation targets
    sim_targets = [
        {'type': 'REGULAR', 'settings': {...}, 'regular': 'alpha_1'},
        {'type': 'REGULAR', 'settings': {...}, 'regular': 'alpha_2'},
    ]

    # Send the list of targets to the concurrent simulation task
    task = simulate_tasks.delay(sim_targets)
    print(f"Sent concurrent task with ID: {task.id}")
    ```

## Stopping the Services

To stop and remove all containers, networks, and volumes:
```bash
docker-compose down
```

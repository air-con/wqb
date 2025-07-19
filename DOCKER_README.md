# WQB Docker Deployment Guide

This guide provides comprehensive instructions for deploying and managing the WQB Celery worker using Docker and Docker Compose.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Sending Tasks](#sending-tasks)
- [Monitoring](#monitoring)
- [Stopping the Services](#stopping-the-services)

## Prerequisites

- **Docker Engine:** [Install Docker](https://docs.docker.com/engine/install/)
- **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)

## Configuration

The entire application is configured via environment variables loaded from a `.env` file.

1.  **Create `.env` File:**
    Copy the example file to create your local configuration:
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env` File:**
    Open the `.env` file and fill in the following variables. **All variables listed in `.env.example` are required for the application to boot correctly.**

    ### Required Variables

    - **`CELERY_BROKER_URL`**: The full connection URL for your message broker.
    - **`LARK_APP_ID`**: Your Lark/Feishu application's App ID.
    - **`LARK_APP_SECRET`**: Your Lark/Feishu application's App Secret.
    - **`LARK_APP_TOKEN`**: The token for the specific Bitable used as the Celery result backend.
    - **`LARK_TABLE_ID`**: The ID of the table within the Bitable.

    ### Optional Variables

    - **`CELERY_CONCURRENCY`**: The number of concurrent worker processes. Defaults to `3` if not set.
    - **`CELERY_QUEUE`**: The name of the message queue to consume from. Defaults to `celery` if not set.

## Deployment

With the `.env` file fully configured, you can build and start the Celery worker with a single command:

```bash
docker-compose up --build -d
```
- `--build`: Rebuilds the Docker image to include any recent code changes.
- `-d`: Runs the container in detached mode (in the background).

This command starts a single service: a Celery **worker** container that immediately begins listening for tasks.

## Sending Tasks

Tasks are sent by running the `send_tasks.py` script from your **local machine**.

1.  **Set Broker URL in Shell:**
    The script needs to know where to send the tasks. Export the `CELERY_BROKER_URL` in your shell session.
    ```bash
    export CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//"
    ```

2.  **Run the Script:**
    Execute the script to send a sample simulation task.
    ```bash
    python send_tasks.py
    ```

## Monitoring

To view the real-time logs from the running worker container:
```bash
docker-compose logs -f
```

## Stopping the Services

To stop and remove the container:
```bash
docker-compose down
```
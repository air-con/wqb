# WQB Project - Docker Deployment Guide

This guide provides instructions on how to deploy the WQB project using Docker and Docker Compose.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
  - [1. Build and Run (Local Development)](#1-build-and-run-local-development)
  - [2. Run from Docker Hub (Production/Deployment)](#2-run-from-docker-hub-productiondeployment)
- [Verifying the Deployment](#verifying-the-deployment)
- [Sending Tasks](#sending-tasks)
- [Stopping the Services](#stopping-the-services)
- [Cloud Deployment Notes](#cloud-deployment-notes)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

*   **Docker Engine:** [Install Docker](https://docs.docker.com/engine/install/)
*   **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/) (Docker Desktop for Windows/macOS includes Docker Compose)

## Configuration

The project relies on several environment variables for its operation, including connection details for RabbitMQ (Celery broker), MongoDB, and an external API. These variables should be configured in a `.env` file.

1.  **Create a `.env` file:**
    In the root directory of your project (where `docker-compose.yml` is located), create a new file named `.env`.

2.  **Add environment variables:**
    Populate the `.env` file with the following variables, replacing the placeholder values with your actual credentials and URLs:

    ```dotenv
    # Celery Broker URL (e.g., RabbitMQ, Redis)
    CELERY_BROKER_URL="amqps://user:password@host:port/vhost"

    # MongoDB Connection URI
    MONGO_URI="mongodb://user:password@host:port/database?authSource=admin"

    # External API Configuration
    API_DOMAIN="api.example.com" # e.g., your_api_domain.com
    API_KEY="your_api_key_here"

    # Celery Worker Concurrency (optional, default is 8)
    CELERY_CONCURRENCY=8
    ```
    **Important:** Ensure your `CELERY_BROKER_URL` and `MONGO_URI` are correctly formatted and accessible from your Docker containers.

## Deployment Steps

There are two main ways to run the project with Docker Compose: building images locally (for development) or pulling pre-built images from Docker Hub (for production/deployment).

### 1. Build and Run (Local Development)

This method builds the Docker images from your local codebase. Use this if you are developing the project and need to test local changes.

1.  **Ensure your `docker-compose.yml` uses `build` directives:**
    (This is the default setup if you haven't changed it to `image` directives yet.)

    ```yaml
    # docker-compose.yml (example snippet)
    services:
      worker:
        build:
          context: .
          dockerfile: Dockerfile
        # ... other configurations
      app:
        build:
          context: .
          dockerfile: Dockerfile
        # ... other configurations
    ```

2.  **Build and start the services:**
    Navigate to the project root directory in your terminal and run:

    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces Docker Compose to rebuild images before starting containers.
    *   `-d`: Runs the containers in detached mode (in the background).

### 2. Run from Docker Hub (Production/Deployment)

This method pulls pre-built Docker images from Docker Hub. Use this for production deployments where images are already published.

1.  **Modify your `docker-compose.yml` to use `image` directives:**
    Replace the `build` directives with `image` directives pointing to your Docker Hub repository. Also, remove the `volumes` mounts for `/app` as the code is already in the image.

    ```yaml
    # docker-compose.yml (example snippet)
    services:
      worker:
        image: usernamepassword/wqb # Replace with your actual Docker Hub image name
        # volumes: # Remove or comment out this line
        #   - .:/app
        # ... other configurations
      app:
        image: usernamepassword/wqb # Replace with your actual Docker Hub image name
        # volumes: # Remove or comment out this line
        #   - .:/app
        # ... other configurations
      flower:
        image: mher/flower:0.9.7 # Flower image
        # ... other configurations
    ```
    **Note:** Replace `usernamepassword/wqb` with your actual Docker Hub image name (e.g., `your_dockerhub_username/your_repo_name`).

2.  **Pull and start the services:**
    Navigate to the project root directory in your terminal and run:

    ```bash
    docker-compose up -d
    ```
    *   Docker Compose will automatically pull the specified images from Docker Hub if they are not available locally.

## Verifying the Deployment

After starting the services, you can verify their status and check logs:

1.  **Check container status:**
    ```bash
    docker-compose ps
    ```
    This command lists all services defined in your `docker-compose.yml` and their current status.

2.  **View service logs:**
    To see the logs for a specific service (e.g., `worker`):
    ```bash
    docker-compose logs worker
    ```
    To view logs for all services:
    ```bash
    docker-compose logs
    ```
    To follow logs in real-time:
    ```bash
    docker-compose logs -f
    ```

3.  **Access Flower UI:**
    If your `flower` service is running and its port (default 5555) is exposed, you can access the Celery monitoring dashboard in your web browser:
    ```
    http://localhost:5555
    ```
    If deploying to a remote VPS, replace `localhost` with your VPS's IP address or domain name. Ensure your VPS firewall allows traffic on port 5555.

## Sending Tasks

Tasks are sent to the Celery broker using the `send_tasks.py` script. This script acts as a client to your Celery setup.

1.  **Ensure `CELERY_BROKER_URL` is set:**
    The `send_tasks.py` script requires the `CELERY_BROKER_URL` environment variable to be set in your shell where you run the script. This should be the same broker URL that your Celery worker is connected to.

    ```bash
    export CELERY_BROKER_URL="amqps://user:password@host:port/vhost" # Use your actual broker URL
    ```

2.  **Run the `send_tasks.py` script:**
    Navigate to the project root directory and execute the script:

    ```bash
    python send_tasks.py
    ```

    The script will output messages indicating that tasks are being sent, along with their IDs.

    ```python
    # send_tasks.py (excerpt)
    from celery import Celery
    import os

    # --- Configuration for the Celery client --- #
    # IMPORTANT: You MUST set the CELERY_BROKER_URL environment variable
    # in your shell before running this script.
    # Example: export CELERY_BROKER_URL="amqps://krmckymc:drgEi9XHXNwSSH9r02mLGtl9z5qKHMHQ@fuji.lmq.cloudamqp.com/krmckymc"

    # Create a minimal Celery app instance for sending tasks
    # The broker URL will be read from the CELERY_BROKER_URL environment variable
    app = Celery('wqb')

    fields = ['assets', 'assets_curr', 'bookvalue_ps', 'capex', 'cash', 'cash_st', 'cashflow', 'cashflow_dividends', 'cashflow_fin', 'cashflow_invst', 'cashflow_op', 'cogs', 'current_ratio', 'debt', 'debt_lt', 'debt_st', 'depre_amort', 'ebit', 'ebitda', 'employee', 'enterprise_value', 'eps', 'equity', 'fnd6_acdo', 'fnd6_acodo', 'fnd6_acox', 'fnd6_acqgdwl', 'fnd6_acqintan', 'fnd6_adesinda_curcd', 'fnd6_aldo', 'fnd6_am', 'fnd6_aodo', 'fnd6_aox', 'fnd6_aqc', 'fnd6_aqi', 'fnd6_aqs', 'fnd6_beta', 'fnd6_capxs', 'fnd6_capxv', 'fnd6_caxts', 'fnd6_ceql', 'fnd6_ch', 'fnd6_ci', 'fnd6_cibegni', 'fnd6_cicurr', 'fnd6_cidergl', 'fnd6_cik', 'fnd6_cimii', 'fnd6_ciother', 'fnd6_cipen', 'fnd6_cisecgl', 'fnd6_citotal', 'fnd6_city', 'fnd6_cld2', 'fnd6_cld3', 'fnd6_cld4', 'fnd6_cld5', 'fnd6_cogss', 'fnd6_cptmfmq_actq', 'fnd6_cptmfmq_atq', 'fnd6_cptmfmq_ceqq', 'fnd6_cptmfmq_dlttq', 'fnd6_cptmfmq_dpq', 'fnd6_cptmfmq_lctq', 'fnd6_cptmfmq_oibdpq', 'fnd6_cptmfmq_opepsq', 'fnd6_cptmfmq_saleq', 'fnd6_cptnewqeventv110_actq', 'fnd6_cptnewqeventv110_apq', 'fnd6_cptnewqeventv110_atq', 'fnd6_cptnewqeventv110_ceqq', 'fnd6_cptnewqeventv110_dlttq', 'fnd6_cptnewqeventv110_dpq', 'fnd6_cptnewqeventv110_epsf12', 'fnd6_cptnewqeventv110_epsfxq', 'fnd6_cptnewqeventv110_epsx12', 'fnd6_cptnewqeventv110_lctq', 'fnd6_cptnewqeventv110_ltq', 'fnd6_cptnewqeventv110_nopiq', 'fnd6_cptnewqeventv110_oeps12', 'fnd6_cptnewqeventv110_oiadpq', 'fnd6_cptnewqeventv110_oibdpq', 'fnd6_cptnewqeventv110_opepsq', 'fnd6_cptnewqv1300_actq', 'fnd6_cptnewqv1300_apq', 'fnd6_cptnewqv1300_atq', 'fnd6_cptnewqv1300_ceqq', 'fnd6_cptnewqv1300_dlttq', 'fnd6_cptnewqv1300_dpq', 'fnd6_cptnewqv1300_epsf12', 'fnd6_cptnewqv1300_epsfxq', 'fnd6_cptnewqv1300_epsx12', 'fnd6_cptnewqv1300_lctq', 'fnd6_cptnewqv1300_ltq', 'fnd6_cptnewqv1300_nopiq', 'fnd6_cptnewqv1300_oeps12', 'fnd6_cptnewqv1300_oiadpq', 'fnd6_cptnewqv1300_oibdpq', 'fnd6_cptnewqv1300_opepsq', 'fnd6_cptnewqv1300_rectq', 'fnd6_cptnewqv1300_req', 'fnd6_cptnewqv1300_saleq', 'fnd6_cptnew... # truncated

# --- Send tasks by their string name --- #

# Task name for single alpha simulation (defined in wqb/tasks.py)
single_alpha_task_name = 'wqb.tasks.simulate_single_alpha_task'
for field in fields:
    print(f"Sending {single_alpha_task_name}...")
    task = app.send_task(single_alpha_task_name, args=[{
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
    'regular': f'liabilities/{field}',
}])
    print(f"Task sent with ID: {task.id}")

print("Done sending tasks.")
    ```

### Sending Multiple Tasks (Example)

To send multiple tasks in a loop, you can adapt the `send_tasks.py` script. Here's an example of how you might send 5 tasks:

```python
# send_multiple_tasks.py (example)
from celery import Celery
import os

app = Celery('wqb')

# Ensure CELERY_BROKER_URL is set in your environment
# export CELERY_BROKER_URL="amqps://user:password@host:port/vhost"

single_alpha_task_name = 'wqb.tasks.simulate_single_alpha_task'

# Example data for a single alpha task
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
    'regular': 'liabilities/some_field',
}

for i in range(5):
    print(f"Sending task {i+1}...")
    task = app.send_task(single_alpha_task_name, args=[alpha_data])
    print(f"Task {i+1} sent with ID: {task.id}")

print("Done sending multiple tasks.")
```

To run this example, save it as `send_multiple_tasks.py` (or similar) and execute it in your terminal after setting the `CELERY_BROKER_URL`:

```bash
export CELERY_BROKER_URL="amqps://user:password@host:port/vhost"
python send_multiple_tasks.py
```

## Stopping the Services

To stop and remove all running containers, networks, and volumes created by Docker Compose:

```bash
docker-compose down
```

## Cloud Deployment Notes

When deploying to cloud platforms (e.g., `run.claw.cloud`, AWS ECS, Google Cloud Run, Azure Container Instances), the principles are similar:

*   **Environment Variables:** You will configure environment variables directly within the cloud platform's deployment interface or via their CLI/API, rather than using a `.env` file.
*   **Container Images:** You will specify the Docker Hub image name (e.g., `usernamepassword/wqb`) for each service.
*   **Startup Commands:** For each service (e.g., `worker`, `app`), you will explicitly define the container's startup command and arguments in the platform's configuration.
    *   For `worker`: `celery -A wqb.tasks worker --loglevel=info --concurrency=${CELERY_CONCURRENCY:-8}`
    *   For `app`: `tail -f /dev/null` (or your specific application command)
    *   For `flower`: The `mher/flower` image usually has a default command, but if needed, it's `celery flower --broker=${CELERY_BROKER_URL}`.
*   **Port Mapping:** Ensure any necessary ports (like Flower's 5555) are correctly exposed and mapped by the cloud platform's networking configuration.
*   **Resource Allocation:** Configure CPU and memory resources as needed for each service.

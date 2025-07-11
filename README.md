# wqb

A better machine lib.

## HIGHLIGHTS

- **WorldQuant BRAIN Integration:** Seamlessly interact with the WorldQuant BRAIN platform.
- **PyPI Package:** Easily install and manage with pip.
- **Advanced Logging:** Centralized configuration with daily log rotation and console output.
- **Persistent Session:** Extends `requests.Session` with automatic, expiration-proof authentication.
- **Asynchronous Operations:** Built-in support for concurrent simulation, checking, and submission tasks.

## Docker & Celery Usage

This project is designed for scalable, asynchronous processing using Docker, Celery, and a message broker like RabbitMQ.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Setup

1.  **Configure Environment Variables:**
    Create a `.env` file by copying the example:
    ```sh
    cp .env.example .env
    ```
    Open `.env` and fill in your details:
    - `API_KEY`: Your WorldQuant BRAIN API key.
    - `CELERY_BROKER_URL`: The connection URL for your RabbitMQ instance.
    - `LARK_APP_ID`, `LARK_APP_SECRET`, `LARK_APP_TOKEN`, `LARK_TABLE_ID`: (Optional) Credentials for the Lark Bitable result backend.

2.  **Build and Start Services:**
    ```sh
    docker-compose up -d --build
    ```

### How to Use

1.  **Access the Application Container:**
    Get an interactive shell inside the `app` container:
    ```sh
    docker-compose exec app bash
    ```

2.  **Send a Simulation Task:**
    From the shell, you can execute a Python script to send tasks.

    **Example: Processing a single simulation**
    ```python
    from wqb.tasks import simulate_task

    single_alpha = {'type': 'REGULAR', 'settings': {...}, 'regular': 'open / close'}

    # Send a single alpha to the Celery queue.
    task = simulate_task.delay(single_alpha)
    print(f"Sent task with ID: {task.id}")
    ```

    **Example: Processing multiple simulations concurrently**
    ```python
    from wqb.tasks import simulate_tasks

    # A list of alphas to be processed concurrently
    sim_targets = [
        {'type': 'REGULAR', 'settings': {...}, 'regular': 'alpha_1'},
        {'type': 'REGULAR', 'settings': {...}, 'regular': 'alpha_2'},
    ]

    task = simulate_tasks.delay(sim_targets)
    print(f"Sent concurrent task with ID: {task.id}")
    ```

### Monitoring

-   **Worker Logs:** `docker-compose logs -f worker`
-   **Flower Dashboard:** [http://localhost:5555](http://localhost:5555)

## Local Usage (without Docker)

### Prerequisites

- Python >= 3.11
- An active internet connection

### Installation

```sh
python -m pip install wqb
```

### Usage

**PLEASE ALWAYS REMEMBER:**
- **Automatic Authentication:** Manual authentication is never needed. The session handles it automatically.
- **Arguments:** Positional arguments are required; keyword arguments are optional.
- **Return Types:** Methods return either a `requests.Response` or an `Iterable[requests.Response]`.

### Create a `wqb.WQBSession` object

The session now uses environment variables (`API_DOMAIN`, `API_KEY`) for authentication, which are automatically picked up by the client.

```python
from wqb import WQBSession

# The session is automatically authenticated using environment variables.
# No need to pass credentials here.
wqbs = WQBSession()

# You can now directly make API calls.
resp = wqbs.search_operators()
print(resp.ok) # True
```

### API Examples

(The rest of the usage examples for `search_operators`, `locate_dataset`, `simulate`, etc., remain the same but should be called on the `wqbs` object created as shown above.)

---

![wqb logo](https://github.com/rocky-d/wqb/blob/master/img/wqb_1024x1024.png)

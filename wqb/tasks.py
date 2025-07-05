from celery import Celery
from . import wqb_session

# Create a Celery app instance
app = Celery('wqb')

# Load the configuration from the celeryconfig.py file
app.config_from_object('celeryconfig')


@app.task
def simulate_alpha_task(alphas):
    """
    A Celery task to run a simulation for a list of alphas sequentially.
    """
    wqbs = wqb_session.WQBSession()
    multi_alphas = wqb_session.to_multi_alphas(alphas, 10)

    # Define a main async function to run simulations sequentially
    async def run_simulations_sequentially():
        for multi_alpha in multi_alphas:
            # The 'await' keyword ensures that each simulation finishes
            # before the next one starts, respecting API limits.
            print(f"Simulating multi_alpha: {multi_alpha}")
            await wqbs.simulate(multi_alpha)

    # Run the main async function once.
    import asyncio

    asyncio.run(run_simulations_sequentially())

    return f"Processed {len(alphas)} alphas sequentially."


@app.task
def simulate_single_alpha_task(alpha):
    """
    A Celery task to run a simulation for a single alpha.
    """
    wqbs = wqb_session.WQBSession()

    async def run_single_simulation():
        print(f"Simulating single alpha: {alpha}")
        await wqbs.simulate(alpha)

    import asyncio

    asyncio.run(run_single_simulation())

    return f"Processed single alpha."
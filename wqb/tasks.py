from celery import Celery
from . import wqb_session
from .backend import save_failed_simulation

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

    async def run_simulations_sequentially():
        for multi_alpha in multi_alphas:
            print(f"Simulating multi_alpha: {multi_alpha}")
            response = await wqbs.simulate(multi_alpha)
            if response is None or not response.ok:
                print(f"Failed to simulate multi_alpha: {multi_alpha}")
                save_failed_simulation(multi_alpha)

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
        response = await wqbs.simulate(alpha)
        if response is None or not response.ok:
            print(f"Failed to simulate single alpha: {alpha}")
            save_failed_simulation(alpha)

    import asyncio
    asyncio.run(run_single_simulation())

    return f"Processed single alpha."
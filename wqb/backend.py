import os
from pymongo import MongoClient

__all__ = ['save_failed_simulation']

# Initialize the MongoDB client from environment variables
client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
db = client[os.environ.get('MONGO_DATABASE', 'wqb_failures')]
collection = db[os.environ.get('MONGO_COLLECTION', 'simulations')]

def save_failed_simulation(alpha_data):
    """
    Saves the data of a failed simulation to the MongoDB backend.

    If the input is a list (multi_alpha), it saves each alpha individually.
    """
    if isinstance(alpha_data, list):
        # This was a multi_alpha, so insert each one as a separate document
        collection.insert_many(alpha_data)
        print(f"Saved {len(alpha_data)} failed alphas to MongoDB.")
    else:
        # This was a single alpha
        collection.insert_one(alpha_data)
        print("Saved 1 failed alpha to MongoDB.")

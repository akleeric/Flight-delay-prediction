from pymongo import MongoClient
from config.settings import settings
import pandas as pd

def load_historical_flights():
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.DB_HISTORY]
    collection = db["aviationstack_historical_landed_flights"]

    docs = list(collection.find({}))
    df = pd.json_normalize(docs, sep="_")
    client.close()
    return df

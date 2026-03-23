import pandas as pd
from datetime import timedelta
from pymongo import MongoClient
from config.settings import settings

def find_closest_weather(city: str, target_dt):
    """
    Retourne la description météo la plus proche dans les ±6h autour de target_dt.
    """
    if city is None or target_dt is None:
        return None, None

    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.DB_PRODUCTION]
        weather_col = db["weather_data"]

        start = target_dt - timedelta(hours=6)
        end = target_dt + timedelta(hours=6)

        docs_weather = list(weather_col.find({
            "name": city,
            "collected_at": {"$gte": start, "$lte": end}
        }).sort("collected_at", 1))

        if not docs_weather:
            return None, None

        def time_diff(doc):
            collected = pd.to_datetime(doc["collected_at"], utc=True)
            return abs(collected - target_dt)

        closest = min(docs_weather, key=time_diff)

        description = closest["weather"][0]["description"]
        date_used = closest["collected_at"]

        return description, date_used

    except Exception:
        return None, None

    finally:
        try:
            client.close()
        except:
            pass

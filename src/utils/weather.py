import pandas as pd
from pymongo import MongoClient
from config.settings import settings

def find_closest_weather(city: str, target_dt):
    """
    Retourne le document météo le plus proche dans le temps pour une ville donnée.
    Pas de fenêtre ±6h : on prend simplement la météo la plus proche.
    """
    if city is None or target_dt is None:
        return None, None

    try:
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.DB_HISTORY]  # flight_delay_history_db
        weather_col = db["weather_data"]  # clean_weather_data copié ici

        # Récupérer toutes les entrées météo de la ville
        docs_weather = list(weather_col.find({"name": city}))

        if not docs_weather:
            return None, None

        # Trouver la météo la plus proche dans le temps
        def time_diff(doc):
            collected = pd.to_datetime(doc["collected_at"], utc=True)
            return abs(collected - target_dt)

        closest = min(docs_weather, key=time_diff)

        return closest, closest["collected_at"]

    except Exception:
        return None, None

    finally:
        try:
            client.close()
        except:
            pass

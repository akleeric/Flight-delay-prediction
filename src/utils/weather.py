import pandas as pd
from pymongo import MongoClient
from config.settings import settings

# Cache memoire : toute la meteo est chargee une seule fois, groupee par ville.
# Evite d'ouvrir une connexion MongoDB par vol (auparavant ~2000 connexions).
_WEATHER_BY_CITY = None


def _load_weather_by_city():
    global _WEATHER_BY_CITY
    if _WEATHER_BY_CITY is None:
        client = MongoClient(settings.MONGO_URI)
        try:
            db = client[settings.DB_HISTORY]
            docs = list(db["weather_data"].find({}))
        finally:
            client.close()
        cache = {}
        for d in docs:
            cache.setdefault(d.get("name"), []).append(d)
        _WEATHER_BY_CITY = cache
    return _WEATHER_BY_CITY


def find_closest_weather(city: str, target_dt):
    """
    Retourne le document meteo le plus proche dans le temps pour une ville donnee.
    La meteo est chargee une seule fois en memoire (cache) puis matchee localement.
    """
    if city is None or target_dt is None:
        return None, None

    try:
        docs_weather = _load_weather_by_city().get(city, [])
        if not docs_weather:
            return None, None

        def time_diff(doc):
            collected = pd.to_datetime(doc["collected_at"], utc=True)
            return abs(collected - target_dt)

        closest = min(docs_weather, key=time_diff)
        return closest, closest["collected_at"]

    except Exception:
        return None, None

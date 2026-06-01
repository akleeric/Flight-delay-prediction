import requests
from datetime import datetime, timezone
from pymongo import MongoClient
from config.settings import settings
from src.utils.storage import save_raw
from src.utils.iata import IATA_TO_CITY
from src.utils.storage import save_raw, save_processed
from src.utils.transformers import build_features_for_flights


DEPARTURE_AIRPORTS = ["CDG", "ORY", "AMS", "LHR", "JFK"]
AIRLABS_AIRPORTS = ["CDG", "AMS", "LHR", "JFK", "ATL"]


class PredictionCollector:
    """
    Collecteur temps réel :
    - récupère max 10 vols actifs/scheduled du jour
    - récupère les météos des villes concernées
    - sauvegarde 2 JSON : flights_raw.json et weather_raw.json
    """

    def __init__(self):
        self.aviationstack_key = settings.AVIATIONSTACK_API_KEY
        self.weather_key = settings.OPENWEATHER_API_KEY
        self.mongo_uri = settings.MONGO_URI

    # ---------------------------------------------------------
    # 1. Récupérer max 10 vols actifs/scheduled du jour
    # ---------------------------------------------------------
    def get_live_flights(self):
        flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        MAX_FLIGHTS = 10

        for dep in DEPARTURE_AIRPORTS:
            for status in ["active", "scheduled"]:

                if len(flights) >= MAX_FLIGHTS:
                    break

                response = requests.get(
                    "http://api.aviationstack.com/v1/flights",
                    params={
                        "access_key": self.aviationstack_key,
                        "dep_iata": dep,
                        "flight_status": status,
                        "limit": 50
                    },
                    timeout=15
                )

                raw_flights = response.json().get("data", [])

                for f in raw_flights:
                    if len(flights) >= MAX_FLIGHTS:
                        break

                    if f.get("flight_date") != today_str:
                        continue

                    if f.get("flight_status") not in ["active", "scheduled"]:
                        continue

                    flights.append(f)

        save_raw("flights_raw", flights)
        return flights

    # ---------------------------------------------------------
    # 2. Récupérer vols actifs depuis AirLabs
    # ---------------------------------------------------------
    def get_live_flights_airlabs(self):
        flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        MAX_FLIGHTS = 10
        airlabs_key = settings.AIRLABS_API_KEY
        if not airlabs_key:
            print("Cle AirLabs absente — ignoré")
            return []
        for dep in AIRLABS_AIRPORTS:
            if len(flights) >= MAX_FLIGHTS:
                break
            try:
                response = requests.get(
                    "https://airlabs.co/api/v9/flights",
                    params={
                        "api_key": airlabs_key,
                        "dep_iata": dep,
                    },
                    timeout=15
                )
                raw = response.json().get("response", [])
                for f in raw:
                    if len(flights) >= MAX_FLIGHTS:
                        break
                    if not f.get("dep_iata") or not f.get("arr_iata"):
                        continue
                    # Normalisation au format Aviationstack
                    normalized = {
                        "flight_date": today_str,
                        "flight_status": "active",
                        "departure": {
                            "iata": f.get("dep_iata"),
                            "scheduled": f.get("dep_time", ""),
                            "estimated": f.get("dep_estimated", ""),
                            "actual": f.get("dep_actual", ""),
                            "delay": f.get("delayed"),
                        },
                        "arrival": {
                            "iata": f.get("arr_iata"),
                            "scheduled": f.get("arr_time", ""),
                            "estimated": f.get("arr_estimated", ""),
                            "actual": f.get("arr_actual"),
                        },
                        "airline": {
                            "iata": f.get("airline_iata", ""),
                            "name": f.get("airline_iata", ""),
                        },
                        "flight": {
                            "iata": f.get("flight_iata", ""),
                            "number": f.get("flight_number", ""),
                        }
                    }
                    flights.append(normalized)
            except Exception as e:
                print(f"Erreur AirLabs {dep}: {e}")
                continue
        return flights

    # ---------------------------------------------------------
    # 2. Récupérer météo propre pour une ville
    # ---------------------------------------------------------
    def fetch_weather(self, city):
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={self.weather_key}&units=metric"
        )

        data = requests.get(url, timeout=10).json()

        now = datetime.now(timezone.utc)
        timestamp = now.strftime("%Y%m%d%H")

        data["_id"] = f"{city}_{timestamp}"
        data["city"] = city
        data["collected_at"] = now.isoformat()  # FIX JSON

        # Sauvegarde Mongo
        client = MongoClient(self.mongo_uri)
        db = client[settings.DB_HISTORY]
        db["weather_data"].update_one({"_id": data["_id"]}, {"$set": data}, upsert=True)
        client.close()

        return data

    # ---------------------------------------------------------
    # 3. Récupérer météo pour toutes les villes concernées
    # ---------------------------------------------------------
    def collect_weather_for_flights(self, flights):
        cities = set()

        for f in flights:
            dep_iata = f.get("departure", {}).get("iata")
            arr_iata = f.get("arrival", {}).get("iata")

            if dep_iata in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[dep_iata])
            if arr_iata in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[arr_iata])

        weather_list = [self.fetch_weather(city) for city in cities]

        save_raw("weather_raw", weather_list)
        return weather_list
    # ---------------------------------------------------------
    # 4. Construire le dataset features pour la prédiction
    # ---------------------------------------------------------
    def build_processed_features(self, flights, weather_list):
        """
        Construit les features à partir des vols + météo
        et les sauvegarde dans data/processed.
        """
        features = build_features_for_flights(flights, weather_list)

        # Un seul JSON avec la liste de dicts
        # ex: data/processed/prediction_features.json
        save_processed("prediction_features", features)

        return features

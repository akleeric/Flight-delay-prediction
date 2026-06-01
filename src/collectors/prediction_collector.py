import requests
from datetime import datetime, timezone
from pymongo import MongoClient
import os
import sys

# Ajouter la racine du projet au PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from config.settings import settings
from src.utils.storage import save_raw, save_processed
from src.utils.iata import IATA_TO_CITY
from src.utils.transformers import build_features_for_flights


# Aviationstack : 5 aéroports
DEPARTURE_AIRPORTS_AS = ["CDG", "ORY", "AMS", "LHR", "JFK"]

# AirLabs : 5 grands aéroports mondiaux
DEPARTURE_AIRPORTS_AL = ["ATL", "PEK", "DXB", "HND", "LAX"]

MAX_FLIGHTS = 10


class PredictionCollector:
    """
    Collecteur temps réel :
    - récupère max 10 vols actifs/scheduled du jour depuis Aviationstack
    - récupère max 10 vols actifs/scheduled du jour depuis AirLabs
    - déduplique les vols (même trajet réel)
    - récupère les météos des villes concernées
    - sauvegarde 3 JSON :
        flights_raw.json (Aviationstack)
        airlabs_flights_raw.json (AirLabs)
        weather_raw.json (météos)
    """

    def __init__(self):
        self.aviationstack_key = settings.AVIATIONSTACK_API_KEY
        self.airlabs_key = settings.AIRLABS_API_KEY
        self.weather_key = settings.OPENWEATHER_API_KEY
        self.mongo_uri = settings.MONGO_URI

        # Set global pour éviter les doublons
        self.seen_flights = set()

    # ---------------------------------------------------------
    # 1. Vols Aviationstack
    # ---------------------------------------------------------
    def get_live_flights(self):
        flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for dep in DEPARTURE_AIRPORTS_AS:
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

                    dep_iata = f.get("departure", {}).get("iata")
                    arr_iata = f.get("arrival", {}).get("iata")
                    sched = f.get("departure", {}).get("scheduled")

                    if not dep_iata or not arr_iata or not sched:
                        continue

                    key = (dep_iata, arr_iata, sched)

                    # 🔥 Déduplication immédiate
                    if key in self.seen_flights:
                        continue

                    self.seen_flights.add(key)
                    flights.append(f)

        save_raw("flights_raw", flights)
        return flights

    # ---------------------------------------------------------
    # 2. Vols AirLabs
    # ---------------------------------------------------------
    def get_live_flights_airlabs(self):
        flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for dep in DEPARTURE_AIRPORTS_AL:
            if len(flights) >= MAX_FLIGHTS:
                break

            response = requests.get(
                "https://airlabs.co/api/v9/schedules",
                params={
                    "dep_iata": dep,
                    "api_key": self.airlabs_key
                },
                timeout=15
            )

            raw = response.json().get("response", [])

            for f in raw:
                if len(flights) >= MAX_FLIGHTS:
                    break

                dep_time = f.get("dep_time")
                if not dep_time or not dep_time.startswith(today_str):
                    continue

                if f.get("status") not in ["active", "scheduled"]:
                    continue

                dep_iata = f.get("dep_iata")
                arr_iata = f.get("arr_iata")
                sched = f.get("dep_time_utc")

                if not dep_iata or not arr_iata or not sched:
                    continue

                key = (dep_iata, arr_iata, sched)

                # 🔥 Déduplication immédiate
                if key in self.seen_flights:
                    continue

                self.seen_flights.add(key)
                flights.append(f)

        save_raw("airlabs_flights_raw", flights)
        return flights

    # ---------------------------------------------------------
    # 3. Récupérer météo propre pour une ville
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
        data["collected_at"] = now.isoformat()

        client = MongoClient(self.mongo_uri)
        db = client[settings.DB_HISTORY]
        db["weather_data"].update_one({"_id": data["_id"]}, {"$set": data}, upsert=True)
        client.close()

        return data

    # ---------------------------------------------------------
    # 4. Récupérer météo pour toutes les villes (AS + AL)
    # ---------------------------------------------------------
    def collect_weather_for_flights(self, flights_as, flights_al):
        cities = set()

        # Aviationstack
        for f in flights_as:
            dep = f.get("departure", {}).get("iata")
            arr = f.get("arrival", {}).get("iata")

            if dep in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[dep])
            if arr in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[arr])

        # AirLabs
        for f in flights_al:
            dep = f.get("dep_iata")
            arr = f.get("arr_iata")

            if dep in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[dep])
            if arr in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[arr])

        weather_list = [self.fetch_weather(city) for city in cities]

        save_raw("weather_raw", weather_list)
        return weather_list

    # ---------------------------------------------------------
    # 5. Construire les features (AS + AL)
    # ---------------------------------------------------------
    def build_processed_features(self, flights_as, flights_al, weather_list):
        flights = flights_as + flights_al
        features = build_features_for_flights(flights, weather_list)
        save_processed("prediction_features", features)
        return features


# ---------------------------------------------------------
# MAIN DE TEST
# ---------------------------------------------------------
if __name__ == "__main__":
    collector = PredictionCollector()

    print("Collecte Aviationstack...")
    flights_as = collector.get_live_flights()
    print(f"{len(flights_as)} vols AS")

    print("✈️ Collecte AirLabs...")
    flights_al = collector.get_live_flights_airlabs()
    print(f"{len(flights_al)} vols AL")

    print("Collecte météo...")
    weather = collector.collect_weather_for_flights(flights_as, flights_al)
    print(f"{len(weather)} villes météo")

    print("Construction features...")
    features = collector.build_processed_features(flights_as, flights_al, weather)
    print(f"{len(features)} features générées")

    print("Test PredictionCollector terminé.")

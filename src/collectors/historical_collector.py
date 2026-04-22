import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
import logging
import time

# --------------------------------------------------------------------
# Import de la matrice IATA -> Ville (source unique)
# --------------------------------------------------------------------
from src.utils.iata import IATA_TO_CITY

# --------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/historical_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


class HistoricalFlightCollector:
    """
    Collecteur historique basé sur le temps réel :
    - collecte uniquement les vols du jour
    - ne garde que ceux qui ont arrival.actual != None
    - limite à 50 vols pour test
    - stocke dans une base séparée : flight_delay_history_db
    """

    def __init__(self, airports=None):
        self.aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY')
        self.weather_key = os.getenv('OPENWEATHER_API_KEY')

        mongo_uri = os.getenv('MONGODB_URI')
        self.mongo_client = MongoClient(mongo_uri)

        self.db = self.mongo_client['flight_delay_history_db']

        if airports is None:
            airports = ['CDG', 'ORY', 'AMS', 'LHR', 'MAD', 'FRA', 'MUC', 'BCN', 'FCO', 'CPH']
        self.airports = airports

        logger.info("Collecteur historique initialisé (base séparée)")

    def collect_aviationstack_historical_like(self):
        logger.info("Collecte AviationStack (historique simulé)...")
        all_flights = []

        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for airport in self.airports:
            if len(all_flights) >= 50:
                break

            try:
                response = requests.get(
                    "http://api.aviationstack.com/v1/flights",
                    params={
                        'access_key': self.aviationstack_key,
                        'dep_iata': airport,
                        'limit': 100
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    flights = response.json().get('data', [])

                    for f in flights:
                        if len(all_flights) >= 100:
                            break

                        if f.get('flight_date') != today_str:
                            continue

                        if f.get('flight_status') != "landed":
                            continue

                        arrival = f.get('arrival', {})
                        if arrival.get('actual') is None or arrival.get('actual') == "":
                            continue

                        all_flights.append(f)

                    logger.info(f"{airport}: {len(all_flights)} vols finalisés cumulés")

                else:
                    logger.warning(f"{airport}: HTTP {response.status_code}")

                time.sleep(5)

            except Exception as e:
                logger.error(f"{airport}: {e}")

        collection = self.db['aviationstack_historical_landed_flights']
        saved = 0

        for flight in all_flights:
            flight['collected_at'] = datetime.now(timezone.utc)

            flight_iata = flight.get('flight', {}).get('iata', 'N/A')
            flight_date = flight.get('flight_date', 'N/A')
            flight['_id'] = f"{flight_iata}_{flight_date}"

            try:
                collection.update_one({'_id': flight['_id']}, {'$set': flight}, upsert=True)
                saved += 1
            except Exception as e:
                logger.error(f"Erreur MongoDB pour {flight.get('_id')}: {e}")

        logger.info(f"Historique: {saved} vols finalisés sauvegardés")
        return saved

    def collect_weather(self, cities=['Paris', 'Amsterdam', 'London', 'Madrid', 'Frankfurt', 'Munich', 'Barcelona', 'Rome', 'Copenhagen']):
        logger.info("Collecte Météo départ (liste statique)...")

        weather_db = self.mongo_client['flight_delay_history_db']
        collection = weather_db['weather_data']

        saved = 0
        for city in cities:
            try:
                response = requests.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={
                        'q': city,
                        'appid': self.weather_key,
                        'units': 'metric'
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    data['collected_at'] = datetime.now(timezone.utc)
                    data['_id'] = f"{city}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
                    data['role'] = 'departure'
                    collection.update_one({'_id': data['_id']}, {'$set': data}, upsert=True)
                    saved += 1
                    logger.info(f"[DEPARTURE] {city}: {data['main']['temp']}°C")
                else:
                    logger.warning(f"[DEPARTURE] {city}: HTTP {response.status_code}")
                time.sleep(1)

            except Exception as e:
                logger.error(f"[DEPARTURE] {city}: {e}")

        logger.info(f"Météo départ: {saved} villes sauvegardées")
        return saved

    def collect_arrival_weather_from_historical_flights(self):
        logger.info("Collecte Météo d'arrivée à partir des vols historisés...")

        history_db = self.mongo_client['flight_delay_history_db']
        flights_collection = history_db['aviationstack_historical_landed_flights']

        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        flights_cursor = flights_collection.find(
            {"flight_date": today_str},
            {"arrival.iata": 1}
        )

        arrival_iatas = set()
        for f in flights_cursor:
            arrival = f.get("arrival", {})
            arr_iata = arrival.get("iata")
            if arr_iata:
                arrival_iatas.add(arr_iata)

        logger.info(f"IATA d'arrivée trouvés pour aujourd'hui: {arrival_iatas}")

        cities = set()
        for iata in arrival_iatas:
            city = IATA_TO_CITY.get(iata)
            if city:
                cities.add(city)
            else:
                logger.warning(
                    f"⚠️ IATA inconnu dans iata.py : {iata} — "
                    f"ajoute-le dans IATA_TO_CITY pour éviter de perdre des vols."
                )


        if not cities:
            logger.info("Aucune ville d'arrivée à collecter pour aujourd'hui.")
            return 0

        weather_db = self.mongo_client['flight_delay_history_db']
        collection = weather_db['weather_data']

        saved = 0
        for city in cities:
            try:
                response = requests.get(
                    "http://api.openweathermap.org/data/2.5/weather",
                    params={
                        'q': city,
                        'appid': self.weather_key,
                        'units': 'metric'
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    data['collected_at'] = datetime.now(timezone.utc)
                    data['_id'] = f"{city}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
                    data['role'] = 'arrival'
                    collection.update_one({'_id': data['_id']}, {'$set': data}, upsert=True)
                    saved += 1
                    logger.info(f"[ARRIVAL] {city}: {data['main']['temp']}°C")
                else:
                    logger.warning(f"[ARRIVAL] {city}: HTTP {response.status_code}")
                time.sleep(1)

            except Exception as e:
                logger.error(f"[ARRIVAL] {city}: {e}")

        logger.info(f"Météo d'arrivée: {saved} villes sauvegardées")
        return saved

    def run(self):
        logger.info("=" * 70)
        logger.info("DÉBUT COLLECTE HISTORIQUE")
        logger.info("=" * 70)

        count = self.collect_aviationstack_historical_like()
        weather_dep_count = self.collect_weather()
        weather_arr_count = self.collect_arrival_weather_from_historical_flights()

        logger.info("=" * 70)
        logger.info(
            f"Collecte terminée : {count} vols finalisés ajoutés, "
            f"Météo départ={weather_dep_count}, Météo arrivée={weather_arr_count}"
        )
        logger.info("=" * 70)

    def close(self):
        self.mongo_client.close()
        logger.info("Connexions fermées")


if __name__ == "__main__":
    collector = HistoricalFlightCollector()
    try:
        collector.run()
    finally:
        collector.close()

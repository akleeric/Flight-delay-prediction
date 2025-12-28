import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
import logging
import time

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
    - limite à 10 vols pour test
    - stocke dans une base séparée : flight_delay_history_db
    """

    def __init__(self, airports=None):
        self.aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY')

        # -------------------------------
        # BASE DE DONNÉES HISTORIQUE
        # -------------------------------
        mongo_uri = os.getenv('MONGODB_URI')
        self.mongo_client = MongoClient(mongo_uri)

        # ⚠️ NOUVELLE BASE DÉDIÉE
        self.db = self.mongo_client['flight_delay_history_db']

        if airports is None:
            airports = ['CDG', 'ORY', 'AMS', 'LHR', 'JFK']
        self.airports = airports

        logger.info("Collecteur historique initialisé (base séparée)")

    def collect_aviationstack_historical_like(self):
        logger.info("Collecte AviationStack (historique simulé)...")
        all_flights = []

        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for airport in self.airports:
            if len(all_flights) >= 10:
                break  # Limite de test

            try:
                response = requests.get(
                    "http://api.aviationstack.com/v1/flights",
                    params={
                        'access_key': self.aviationstack_key,
                        'dep_iata': airport,
                        'limit': 50
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    flights = response.json().get('data', [])

                    # Filtrer : vols du jour + arrival.actual != None
                    for f in flights:
                        if len(all_flights) >= 10:
                            break

                        if f.get('flight_date') != today_str:
                            continue

                        arrival = f.get('arrival') or {}
                        if arrival.get('actual') is None:
                            continue

                        all_flights.append(f)

                    logger.info(f"{airport}: {len(all_flights)} vols finalisés cumulés")

                else:
                    logger.warning(f"{airport}: HTTP {response.status_code}")

                time.sleep(2)

            except Exception as e:
                logger.error(f"{airport}: {e}")

        # -------------------------------
        # SAUVEGARDE DANS LA BASE HISTORIQUE
        # -------------------------------
        collection = self.db['aviationstack_historical_flights']
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

        logger.info(f"Historique: {saved} vols finalisés sauvegardés (TEST)")
        return saved

    def run(self):
        logger.info("=" * 70)
        logger.info("DÉBUT COLLECTE HISTORIQUE (TEST 10 vols)")
        logger.info("=" * 70)

        count = self.collect_aviationstack_historical_like()

        logger.info("=" * 70)
        logger.info(f"Collecte terminée : {count} vols finalisés ajoutés")
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

import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/production_collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

class ProductionFlightCollector:
    """Collecteur de production - AviationStack + Air France-KLM + Météo"""
    def __init__(self):
        # APIs
        self.aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY')
        self.afklm_key = os.getenv('AIRFRANCEKLM_API_KEY')
        self.weather_key = os.getenv('OPENWEATHER_API_KEY')

        # MongoDB
        mongo_uri = os.getenv('MONGODB_URI')
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client['flight_delay_db']
        logger.info("Collecteur de production initialisé")

    def collect_aviationstack(self, airports=['CDG', 'ORY', 'AMS', 'LHR', 'JFK']):
        """Collecter vols AviationStack"""
        logger.info("Collecte AviationStack...")
        all_flights = []

        for airport in airports:
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
                    data = response.json()
                    flights = data.get('data', [])
                    all_flights.extend(flights)
                    logger.info(f"{airport}: {len(flights)} vols")
                time.sleep(2)  # Rate limit
            except Exception as e:
                logger.error(f" {airport}: {e}")

        # Sauvegarder
        collection = self.db['aviationstack_flights']
        saved = 0
        for flight in all_flights:
            flight['collected_at'] = datetime.now(timezone.utc)
            flight_iata = flight.get('flight', {}).get('iata', 'N/A')
            flight_date = flight.get('flight_date', 'N/A')
            flight['_id'] = f"{flight_iata}_{flight_date}"
            try:
                collection.update_one({'_id': flight['_id']}, {'$set': flight}, upsert=True)
                saved += 1
            except:
                pass

        logger.info(f"AviationStack: {saved} vols sauvegardés")
        return len(all_flights)

    def collect_afklm(self):
        """Collecter vols Air France-KLM"""
        logger.info("Collecte Air France-KLM...")

        try:
            # Date future (l'API retourne les vols programmés)
            tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=0)

            response = requests.get(
                "https://api.airfranceklm.com/opendata/flightstatus",
                headers={
                    'API-Key': self.afklm_key,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                params={
                    'startRange': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'endRange': end.strftime('%Y-%m-%dT%H:%M:%SZ')
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                flights = data.get('flightStatuses', [])

                # Sauvegarder
                collection = self.db['afklm_flights']
                saved = 0
                for flight in flights:
                    flight['collected_at'] = datetime.now(timezone.utc)
                    flight_id = flight.get('id', f"AFKLM_{flight.get('flightNumber', 'N/A')}")
                    flight['_id'] = flight_id
                    try:
                        collection.update_one({'_id': flight['_id']}, {'$set': flight}, upsert=True)
                        saved += 1
                    except:
                        pass

                logger.info(f"Air France-KLM: {saved} vols sauvegardés")
                return len(flights)
            else:
                logger.warning(f"Air France-KLM: Code {response.status_code}")
                return 0
        except Exception as e:
            logger.error(f"Air France-KLM: {e}")
            return 0

    def collect_weather(self, cities=['Paris', 'Amsterdam', 'London', 'New York']):
        """Collecter données météo"""
        logger.info("Collecte Météo...")
        collection = self.db['weather_data']
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
                    collection.update_one({'_id': data['_id']}, {'$set': data}, upsert=True)
                    saved += 1
                    logger.info(f"{city}: {data['main']['temp']}°C")
                time.sleep(1)

            except Exception as e:
                logger.error(f"{city}: {e}")
        logger.info(f"Météo: {saved} villes sauvegardées")
        return saved

    def get_statistics(self):
        """Statistiques globales"""
        stats = {
            'aviationstack': self.db['aviationstack_flights'].count_documents({}),
            'afklm': self.db['afklm_flights'].count_documents({}),
            'weather': self.db['weather_data'].count_documents({})
        }
        return stats

    def run(self):
        """Exécuter le cycle complet de collecte"""
        logger.info("="*70)
        logger.info("DÉBUT COLLECTE PRODUCTION")
        logger.info("="*70)
        start_time = time.time()

        # Collectes
        aviationstack_count = self.collect_aviationstack()
        afklm_count = self.collect_afklm()
        weather_count = self.collect_weather()

        # Stats
        stats = self.get_statistics()
        duration = time.time() - start_time
        logger.info("="*70)
        logger.info(f" COLLECTE TERMINÉE en {duration:.2f}s")
        logger.info(f"Collectés: AviationStack={aviationstack_count}, AF/KLM={afklm_count}, Météo={weather_count}")
        logger.info(f"Total DB: AviationStack={stats['aviationstack']}, AF/KLM={stats['afklm']}, Météo={stats['weather']}")
        logger.info("="*70)
        return stats
    def close(self):
        self.mongo_client.close()
        logger.info(" Connexions fermées")

if __name__ == "__main__":
    collector = ProductionFlightCollector()
    try:
        collector.run()
    except KeyboardInterrupt:
        logger.info("Arrêt manuel")
    except Exception as e:
        logger.error(f"Erreur: {e}")
    finally:
        collector.close()

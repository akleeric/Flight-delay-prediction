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


# ====================================================================
#  CLASS PRINCIPALE
# ====================================================================

class HistoricalFlightCollector:

    def __init__(self, airports=None):
        """
        Initialisation du collecteur historique.
        """
        self.aviationstack_key = os.getenv('AVIATIONSTACK_API_KEY')
        self.weather_key = os.getenv('OPENWEATHER_API_KEY')
        self.airlabs_key = os.getenv("AIRLABS_API_KEY")

        mongo_uri = os.getenv('MONGODB_URI')
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client['flight_delay_history_db']

        # Aéroports Aviationstack (compte avec abonnement)
        if airports is None:
            airports = [
                "CDG", "ORY", "NCE", "LYS", "MRS",   # France (5)
                "LHR", "LGW", "AMS", "FRA", "MUC",
                "MAD", "BCN", "FCO", "CPH", "ZRH",
                "VIE", "BRU", "OSL", "ARN", "DUS"
            ]
        self.airports = airports

        # Aéroports AirLabs (compte gratuit)
        self.airlabs_airports = ["ATL", "PEK", "DXB", "HND", "LAX"]

        logger.info("Collecteur historique initialisé.")

    # ====================================================================
    #  UTILITAIRES FACTORISÉS
    # ====================================================================

    def _fetch_weather(self, city, role):
        """
        Appel OpenWeather factorisé.
        """
        try:
            r = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "appid": self.weather_key, "units": "metric"},
                timeout=20
            )

            if r.status_code != 200:
                logger.warning(f"[{role.upper()}] {city}: HTTP {r.status_code}")
                return 0

            data = r.json()
            data["collected_at"] = datetime.now(timezone.utc)
            data["_id"] = f"{city}_{datetime.now(timezone.utc).strftime('%Y%m%d%H')}_{role}"
            data["role"] = role

            self.db["weather_data"].update_one({"_id": data["_id"]}, {"$set": data}, upsert=True)

            logger.info(f"[{role.upper()}] {city}: {data['main']['temp']}°C")
            return 1

        except Exception as e:
            logger.error(f"[{role.upper()}] {city}: {e}")
            return 0

    def _extract_cities_from_flights(self, collection_name, field_path):
        """
        Extraction factorisée des villes à partir d'une collection de vols.
        field_path = "arrival.iata" ou "dep_iata"
        """
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        collection = self.db[collection_name]

        # Construction du filtre Mongo
        mongo_filter = {"flight_date": today_str} if "aviationstack" in collection_name else {"dep_time": {"$regex": f"^{today_str}"}}

        cursor = collection.find(mongo_filter, {field_path: 1})

        iatas = set()
        for f in cursor:
            # Navigation dynamique dans le JSON
            value = f
            for key in field_path.split("."):
                value = value.get(key, {})
            if isinstance(value, str):
                iatas.add(value)

        # Mapping IATA -> villes
        cities = set()
        for iata in iatas:
            city = IATA_TO_CITY.get(iata)
            if city:
                cities.add(city)
            else:
                logger.warning(f"[IATA] Inconnu : {iata}")

        return cities

    # ====================================================================
    #  BLOC AVIATIONSTACK
    # ====================================================================

    def collect_aviationstack_historical_like(self):
        """
        Collecte des vols landed depuis Aviationstack.
        """
        logger.info("Collecte AviationStack (historique simulé)...")
        all_flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for airport in self.airports:
            if len(all_flights) >= 50:
                break

            try:
                r = requests.get(
                    "http://api.aviationstack.com/v1/flights",
                    params={'access_key': self.aviationstack_key, 'dep_iata': airport, 'limit': 100},
                    timeout=30
                )

                if r.status_code != 200:
                    logger.warning(f"{airport}: HTTP {r.status_code}")
                    continue

                flights = r.json().get('data', [])

                for f in flights:
                    if len(all_flights) >= 100:
                        break

                    if f.get('flight_date') != today_str:
                        continue
                    if f.get('flight_status') != "landed":
                        continue
                    if not f.get('arrival', {}).get('actual'):
                        continue

                    all_flights.append(f)

                logger.info(f"{airport}: {len(all_flights)} vols cumulés")

                time.sleep(5)

            except Exception as e:
                logger.error(f"{airport}: {e}")

        # Sauvegarde Mongo
        collection = self.db['aviationstack_historical_landed_flights']
        saved = 0

        for f in all_flights:
            f['collected_at'] = datetime.now(timezone.utc)
            flight_iata = f.get('flight', {}).get('iata', 'N/A')
            flight_date = f.get('flight_date', 'N/A')
            f['_id'] = f"{flight_iata}_{flight_date}"

            try:
                collection.update_one({'_id': f['_id']}, {'$set': f}, upsert=True)
                saved += 1
            except Exception as e:
                logger.error(f"Erreur MongoDB pour {f.get('_id')}: {e}")

        logger.info(f"Aviationstack: {saved} vols sauvegardés")
        return saved

    def collect_weather(self):
        """
        Collecte dynamique de la météo de DÉPART pour les vols Aviationstack historisés.
        (Nom historique conservé)
        """
        logger.info("Collecte Météo départ (Aviationstack)...")

        # Extraction des villes depuis departure.iata
        cities = self._extract_cities_from_flights(
            "aviationstack_historical_landed_flights",
            "departure.iata"
        )

        saved = sum(self._fetch_weather(city, "departure") for city in cities)

        logger.info(f"[AVIATIONSTACK] Météo départ sauvegardée: {saved}")
        return saved
    
    def collect_arrival_weather_from_historical_flights(self):
        """
        Collecte dynamique de la météo d'ARRIVÉE pour les vols Aviationstack historisés.
        """
        logger.info("Collecte Météo arrivée (Aviationstack)...")

        cities = self._extract_cities_from_flights(
            "aviationstack_historical_landed_flights",
            "arrival.iata"
        )

        saved = sum(self._fetch_weather(city, "arrival") for city in cities)

        logger.info(f"[AVIATIONSTACK] Météo arrivée sauvegardée: {saved}")
        return saved



    # ====================================================================
    #  BLOC AIRLABS
    # ====================================================================

    def collect_airlabs_historical_landed_flights(self):
        """
        Collecte des vols landed AirLabs (compte gratuit).
        """
        logger.info("Collecte AirLabs (vols landed)...")

        base_url = "https://airlabs.co/api/v9/schedules"
        all_flights = []
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        for dep in self.airlabs_airports:
            if len(all_flights) >= 10:
                break

            params = {"dep_iata": dep, "status": "landed", "api_key": self.airlabs_key}

            try:
                r = requests.get(base_url, params=params, timeout=20)
                if r.status_code != 200:
                    logger.warning(f"[AIRLABS] {dep}: HTTP {r.status_code}")
                    continue

                flights = r.json().get("response", [])
                count_for_airport = 0

                for f in flights:
                    if len(all_flights) >= 10 or count_for_airport >= 2:
                        break

                    if not f.get("dep_time", "").startswith(today_str):
                        continue
                    if f.get("status") != "landed":
                        continue
                    if f.get("cs_flight_iata"):
                        continue
                    if not f.get("dep_actual") or not f.get("arr_actual"):
                        continue

                    all_flights.append(f)
                    count_for_airport += 1

                logger.info(f"[AIRLABS] {dep}: {count_for_airport} vols retenus")
                time.sleep(2)

            except Exception as e:
                logger.error(f"[AIRLABS] {dep}: {e}")

        # Sauvegarde Mongo
        collection = self.db["airlabs_historical_landed_flights"]
        saved = 0

        for f in all_flights:
            f["collected_at"] = datetime.now(timezone.utc)
            flight_iata = f.get("flight_iata", "N/A")
            dep_date = f.get("dep_time", "N/A").split(" ")[0]
            f["_id"] = f"{flight_iata}_{dep_date}"

            try:
                collection.update_one({"_id": f["_id"]}, {"$set": f}, upsert=True)
                saved += 1
            except Exception as e:
                logger.error(f"[AIRLABS] MongoDB: {e}")

        logger.info(f"[AIRLABS] {saved} vols sauvegardés")
        return saved

    def collect_departure_weather_from_airlabs_flights(self):
        cities = self._extract_cities_from_flights(
            "airlabs_historical_landed_flights",
            "dep_iata"
        )
        saved = sum(self._fetch_weather(city, "departure_airlabs") for city in cities)
        logger.info(f"AirLabs météo départ: {saved}")
        return saved

    def collect_arrival_weather_from_airlabs_flights(self):
        cities = self._extract_cities_from_flights(
            "airlabs_historical_landed_flights",
            "arr_iata"
        )
        saved = sum(self._fetch_weather(city, "arrival_airlabs") for city in cities)
        logger.info(f"AirLabs météo arrivée: {saved}")
        return saved

    # ====================================================================
    #  BLOC COMMUN — RUN
    # ====================================================================

    def run(self):
        # ==============================================================
        # AVIATIONSTACK
        # ==============================================================
        logger.info("=" * 70)
        logger.info("DÉBUT COLLECTE HISTORIQUE AVIATIONSTACK")
        logger.info("=" * 70)

        flights_count = self.collect_aviationstack_historical_like()
        weather_dep_count = self.collect_weather()  # météo départ
        weather_arr_count = self.collect_arrival_weather_from_historical_flights()  # météo arrivée

        logger.info("=" * 70)
        logger.info(
            f"[AVIATIONSTACK] Collecte terminée : "
            f"vols={flights_count}, "
            f"météo_depart={weather_dep_count}, "
            f"météo_arrivée={weather_arr_count}"
        )
        logger.info("=" * 70)

        # ==============================================================
        # AIRLABS
        # ==============================================================
        logger.info("=" * 70)
        logger.info("DÉBUT COLLECTE HISTORIQUE AIRLABS")
        logger.info("=" * 70)

        flights_count = self.collect_airlabs_historical_landed_flights()
        weather_dep_count = self.collect_departure_weather_from_airlabs_flights()
        weather_arr_count = self.collect_arrival_weather_from_airlabs_flights()

        logger.info("=" * 70)
        logger.info(
            f"[AIRLABS] Collecte terminée : "
            f"vols={flights_count}, "
            f"météo_depart={weather_dep_count}, "
            f"météo_arrivée={weather_arr_count}"
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

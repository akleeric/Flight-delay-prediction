import requests
import os
from datetime import datetime, timedelta, timezone
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
        logging.FileHandler('logs/backfill_april_aviationstack.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
AVIATIONSTACK_KEY = os.getenv("AVIATIONSTACK_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

AIRPORTS = ['CDG', 'ORY', 'AMS', 'LHR', 'JFK']
MAX_PER_DAY_PER_AIRPORT = 2

client = MongoClient(MONGO_URI)
db = client["flight_delay_history_db"]
collection = db["aviationstack_historical_landed_flights"]


def fetch_flights_for_day(airport, date_str):
    """
    Récupère les vols AviationStack pour un aéroport et une date donnée.
    Filtre : landed + arrival.actual non vide.
    Retourne max 2 vols valides.
    """

    logger.info(f"📡 API AviationStack | {airport} | {date_str}")

    try:
        response = requests.get(
            "http://api.aviationstack.com/v1/flights",
            params={
                "access_key": AVIATIONSTACK_KEY,
                "dep_iata": airport,
                "flight_date": date_str,
                "limit": 100
            },
            timeout=15
        )

        if response.status_code != 200:
            logger.warning(f"{airport} {date_str} → HTTP {response.status_code}")
            return []

        flights = response.json().get("data", [])
        valid = []

        for f in flights:
            if len(valid) >= MAX_PER_DAY_PER_AIRPORT:
                break

            if f.get("flight_status") != "landed":
                continue

            arrival = f.get("arrival", {})
            if arrival.get("actual") in (None, ""):
                continue

            valid.append(f)

        logger.info(f"{airport} {date_str} → {len(valid)} vols valides")
        return valid

    except Exception as e:
        logger.error(f"Erreur API {airport} {date_str}: {e}")
        return []


def save_flights(flights):
    """
    Sauvegarde les vols dans MongoDB avec skip si _id existe déjà.
    """
    saved = 0

    for f in flights:
        flight_iata = f.get("flight", {}).get("iata", "N/A")
        flight_date = f.get("flight_date", "N/A")
        _id = f"{flight_iata}_{flight_date}"

        if collection.find_one({"_id": _id}):
            continue  # skip

        f["_id"] = _id
        f["collected_at"] = datetime.now(timezone.utc)

        try:
            collection.insert_one(f)
            saved += 1
        except Exception as e:
            logger.error(f"Erreur MongoDB pour {_id}: {e}")

    return saved


def backfill_april_2026():
    logger.info("🚀 DÉBUT BACKFILL AVRIL 2026")

    start_date = datetime(2026, 4, 1)
    end_date = datetime(2026, 4, 30)

    current = start_date
    total_saved = 0

    while current <= end_date:
        date_str = current.strftime("%Y-%m-%d")
        logger.info(f"\n📅 JOUR : {date_str}")

        for airport in AIRPORTS:
            flights = fetch_flights_for_day(airport, date_str)
            saved = save_flights(flights)
            total_saved += saved

            time.sleep(2)  # éviter de brûler ton quota

        current += timedelta(days=1)

    logger.info(f"🎉 BACKFILL TERMINÉ — {total_saved} vols ajoutés")
    return total_saved


if __name__ == "__main__":
    backfill_april_2026()
    client.close()

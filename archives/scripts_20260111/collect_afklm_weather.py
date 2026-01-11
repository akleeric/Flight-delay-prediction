#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collection.airfrance_collector import AirFranceCollector
from src.data_collection.weather_collector import WeatherCollector
from src.data_processing import get_mongodb_client
from datetime import datetime

print(f"\n{'='*60}")
print(f"COLLECTE AF-KLM + MÉTÉO - {datetime.now().strftime('%H:%M')}")
print("="*60)

# Mapping IATA -> Ville
IATA_TO_CITY = {
    'CDG': 'Paris', 'ORY': 'Paris',
    'AMS': 'Amsterdam',
    'LHR': 'London',
    'JFK': 'New York',
    'FRA': 'Frankfurt',
    'BCN': 'Barcelona',
    'MAD': 'Madrid',
    'FCO': 'Rome',
    'MXP': 'Milan'
}

# Collecte AF-KLM
afklm = AirFranceCollector()
flights = afklm.collect_flights(date_offset=0)
print(f"✅ AF-KLM: {len(flights)} vols")

# Extraire villes uniques depuis les aéroports
cities = set()
for f in flights:
    route = f.get('route', [])
    for iata in route:
        if iata in IATA_TO_CITY:
            cities.add(IATA_TO_CITY[iata])

cities = list(cities)[:10]
print(f"📍 Villes météo: {', '.join(cities)}")

# Météo
weather = WeatherCollector()
weather_data = weather.collect_weather_bulk(cities)
print(f"✅ Météo: {len(weather_data)} observations")

# Sauvegarde
client = get_mongodb_client()
db = client.db

if flights:
    db.afklm_flights.insert_many(flights)
    print(f"💾 {len(flights)} vols AF-KLM sauvegardés")
    
if weather_data:
    db.weather_data.insert_many(weather_data)
    print(f"💾 {len(weather_data)} observations météo sauvegardées")

print(f"\n📊 TOTAUX EN BASE:")
print(f"AviationStack: {db.aviationstack_flights.count_documents({})} (rate limit)")
print(f"AF-KLM: {db.afklm_flights.count_documents({})}")
print(f"Météo: {db.weather_data.count_documents({})}")

client.close()
afklm.close()
weather.close()

print("="*60)

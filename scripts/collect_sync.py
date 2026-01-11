#!/usr/bin/env python3
"""
Collecte SYNCHRONISEE - Adaptative
- Si AviationStack dispo → 3 sources
- Si AviationStack rate limit → 2 sources (AF-KLM + Météo)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collection import AviationStackCollector, WeatherCollector, AirFranceCollector
from src.data_processing import get_mongodb_client
from src.utils.exceptions import APIException
from datetime import datetime
import time

print("\n" + "="*60)
print("COLLECTE SYNCHRONISEE - MODE ADAPTATIF")
print("="*60)

IATA_TO_CITY = {
    'CDG': 'Paris', 'ORY': 'Paris', 'AMS': 'Amsterdam',
    'LHR': 'London', 'JFK': 'New York', 'FRA': 'Frankfurt',
    'BCN': 'Barcelona', 'MAD': 'Madrid', 'FCO': 'Rome', 'MXP': 'Milan'
}

# Initialisation
weather_collector = WeatherCollector()
afklm_collector = AirFranceCollector()
mongo = get_mongodb_client()

airports = ['CDG', 'ORY', 'AMS', 'LHR', 'JFK']
total_vols_as = 0
total_vols_afklm = 0
total_meteo = 0
aviationstack_available = True

print(f"\n{'='*60}")
print(f"COLLECTE - {datetime.now().strftime('%H:%M:%S')}")
print("="*60)

# === 1. AIR FRANCE-KLM ===
print(f"\n[1/3]  AIR FRANCE-KLM")
try:
    flights_afklm = afklm_collector.collect_flights(date_offset=0)

    if flights_afklm:
        # CORRECTION : Sauvegarder directement dans la bonne collection
        mongo.db.afklm_flights.insert_many(flights_afklm)
        total_vols_afklm = len(flights_afklm)
        print(f"  AF-KLM: {total_vols_afklm} vols collectés et sauvegardés")
    else:
        print(f"   AF-KLM: 0 vols")

except Exception as e:
    flights_afklm = []
    print(f" AF-KLM erreur: {e}")

# === 2. AVIATIONSTACK ===
print(f"\n[2/3]  AVIATIONSTACK")

# Test rapide sur 1 aéroport pour détecter rate limit
try:
    flight_collector = AviationStackCollector()
    test_flights = flight_collector.collect_flights(dep_iata=airports[0], limit=5)

    if test_flights:
        # AviationStack disponible
        for flight in test_flights:
            try:
                mongo.insert_flight_data(flight)
                total_vols_as += 1
            except Exception:
                pass

        print(f"   {airports[0]}: {len(test_flights)} vols")

        # Continuer avec les autres aéroports
        for airport in airports[1:]:
            try:
                flights = flight_collector.collect_flights(dep_iata=airport, limit=10)
                if flights:
                    for flight in flights:
                        try:
                            mongo.insert_flight_data(flight)
                            total_vols_as += 1
                        except Exception:
                            pass
                    print(f"   {airport}: {len(flights)} vols")
                time.sleep(1)
            except Exception as e:
                print(f"   {airport}: {e}")

        aviationstack_available = True

except APIException as e:
    if "rate limit" in str(e).lower() or "exceeded" in str(e).lower():
        print(f"   Rate limit détecté - AviationStack désactivé pour cette collecte")
        aviationstack_available = False
    else:
        print(f"   Erreur: {e}")
        aviationstack_available = False

except Exception as e:
    print(f"  Erreur: {e}")
    aviationstack_available = False

# === 3. METEO ===
print(f"\n[3/3]  METEO")

cities = set()
if flights_afklm:
    for f in flights_afklm:
        for iata in f.get('route', []):
            if iata in IATA_TO_CITY:
                cities.add(IATA_TO_CITY[iata])

if len(cities) < 3:
    cities.update(['Paris', 'Amsterdam', 'London', 'New York'])

cities = list(cities)[:10]

try:
    weather_data = weather_collector.collect_weather_bulk(cities)

    if weather_data:
        mongo.db.weather_data.insert_many(weather_data)
        total_meteo = len(weather_data)
        print(f"  Météo: {total_meteo} observations ({', '.join(cities[:4])})")

except Exception as e:
    print(f"  Météo erreur: {e}")

# === RÉSUME ===
print("\n" + "="*60)
print(" COLLECTE TERMINEE")
print("="*60)
print(f" Vols collectés:")
if aviationstack_available:
    print(f"    - AviationStack: {total_vols_as}")
print(f"    - AF-KLM: {total_vols_afklm}")
print(f" Météo: {total_meteo} observations")

print("\n TOTAUX EN BASE:")
print(f"AviationStack: {mongo.db.aviationstack_flights.count_documents({})}" +
      ("" if aviationstack_available else " (rate limit)"))
print(f"AF-KLM: {mongo.db.afklm_flights.count_documents({})}")
print(f"Météo: {mongo.db.weather_data.count_documents({})}")
print("="*60)

# Nettoyage
weather_collector.close()
afklm_collector.close()
mongo.close()

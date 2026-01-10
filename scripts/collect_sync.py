#!/usr/bin/env python3
"""Collecte synchronisée - Vol + Météo au même moment"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_collection import AviationStackCollector, WeatherCollector
from src.data_processing import get_mongodb_client
from datetime import datetime
import time

print("\n" + "="*60)
print("COLLECTE SYNCHRONISEE - VOLS + METEO")
print("="*60)

flight_collector = AviationStackCollector()
weather_collector = WeatherCollector()
mongo = get_mongodb_client()

airports = [
    {'iata': 'CDG', 'city': 'Paris'},
    {'iata': 'ORY', 'city': 'Paris'},
    {'iata': 'AMS', 'city': 'Amsterdam'},
    {'iata': 'LHR', 'city': 'London'},
    {'iata': 'JFK', 'city': 'New York'}
]

cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 1

total_vols = 0
total_meteo = 0

for cycle in range(1, cycles + 1):
    print(f"\n{'='*60}")
    print(f"CYCLE {cycle}/{cycles} - {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)

    for airport in airports:
        print(f"\n {airport['iata']} ({airport['city']})")

        # 1. METEO D'ABORD (snapshot du moment)
        try:
            weather_raw = weather_collector.collect_weather_by_city(city=airport['city'])

            weather_data = {
                'airport_iata': airport['iata'],
                'city': airport['city'],
                'temperature': weather_raw.get('main', {}).get('temp'),
                'feels_like': weather_raw.get('main', {}).get('feels_like'),
                'humidity': weather_raw.get('main', {}).get('humidity'),
                'pressure': weather_raw.get('main', {}).get('pressure'),
                'wind_speed': weather_raw.get('wind', {}).get('speed'),
                'wind_direction': weather_raw.get('wind', {}).get('deg'),
                'visibility': weather_raw.get('visibility'),
                'cloud_coverage': weather_raw.get('clouds', {}).get('all'),
                'weather_condition': weather_raw.get('weather', [{}])[0].get('main'),
                'weather_description': weather_raw.get('weather', [{}])[0].get('description'),
                'observation_time': datetime.now(),
                'raw_data': weather_raw
            }

            mongo.insert_weather_data(weather_data)
            total_meteo += 1

            print(f"   Météo: {weather_data['temperature']:.1f}°C, {weather_data['weather_condition']}")

        except Exception as e:
            print(f"  Météo: {e}")

        time.sleep(0.5)

        # 2. VOLS JUSTE APRÈS (même fenêtre temporelle)
        try:
            flights = flight_collector.collect_flights(dep_iata=airport['iata'], limit=10)

            saved = 0
            delayed = 0

            for flight in flights:
                try:
                    mongo.insert_flight_data(flight)
                    saved += 1

                    delay = flight.get('departure', {}).get('delay', 0)
                    if delay and delay > 15:
                        delayed += 1
                except:
                    pass

            total_vols += saved
            print(f"   Vols: {saved} collectés ({delayed} retards)")

        except Exception as e:
            print(f"   Vols: {e}")

        time.sleep(1)

    if cycle < cycles:
        print(f"\n Pause 30 secondes avant cycle suivant...")
        time.sleep(30)

print("\n" + "="*60)
print("COLLECTE TERMINEE")
print("="*60)
print(f" Vols collectés: {total_vols}")
print(f" Météo collectée: {total_meteo}")
print("="*60 + "\n")

flight_collector.close()
weather_collector.close()
mongo.close()

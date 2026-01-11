#!/usr/bin/env python3
"""Collecte continue données météo OpenWeatherMap"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime
from src.data_collection import WeatherCollector
from src.data_processing import get_mongodb_client
from src.utils import get_logger

logger = get_logger('weather_collector')


def collect_weather_cycle(collector, mongo):
    """Un cycle de collecte météo"""
    logger.info("="*60)
    logger.info(f"DÉBUT COLLECTE MÉTÉO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

    # NE PAS recréer collector et mongo ici

    airports = [
        {'iata': 'CDG', 'city': 'Paris'},
        {'iata': 'ORY', 'city': 'Paris'},
        {'iata': 'AMS', 'city': 'Amsterdam'},
        {'iata': 'LHR', 'city': 'London'},
        {'iata': 'JFK', 'city': 'New York'}
    ]

    all_weather = []

    for airport in airports:
        try:
            raw_data = collector.collect_weather_by_city(city=airport['city'])

            if raw_data:
                weather_data = {
                    'airport_iata': airport['iata'],
                    'city': airport['city'],
                    'temperature': raw_data.get('main', {}).get('temp'),
                    'feels_like': raw_data.get('main', {}).get('feels_like'),
                    'humidity': raw_data.get('main', {}).get('humidity'),
                    'pressure': raw_data.get('main', {}).get('pressure'),
                    'wind_speed': raw_data.get('wind', {}).get('speed'),
                    'wind_direction': raw_data.get('wind', {}).get('deg'),
                    'visibility': raw_data.get('visibility'),
                    'cloud_coverage': raw_data.get('clouds', {}).get('all'),
                    'weather_condition': raw_data.get('weather', [{}])[0].get('main'),
                    'weather_description': raw_data.get('weather', [{}])[0].get('description'),
                    'observation_time': raw_data.get('collected_at'),
                    'raw_data': raw_data
                }

                all_weather.append(weather_data)

                logger.info(f"{airport['iata']} ({airport['city']}): "
                          f"{weather_data.get('temperature', 'N/A')}°C, "
                          f"{weather_data.get('weather_condition', 'N/A')}")

            time.sleep(1)

        except Exception as e:
            logger.error(f"Erreur {airport['iata']}: {e}")

    # Sauvegarder
    if all_weather:
        for weather in all_weather:
            mongo.insert_weather_data(weather)
        saved = len(all_weather)
        logger.info(f"Sauvegardé: {saved} observations météo")

    # Stats
    stats = mongo.get_statistics()
    logger.info(f"Total météo en base: {stats.get('weather', 0)}")

    # NE PAS fermer ici !

    logger.info("="*60)

    return len(all_weather)



def main():
    import sys

    max_cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    logger.info("DÉMARRAGE COLLECTE MÉTÉO CONTINUE")
    if max_cycles > 0:
        logger.info(f"Mode limité : {max_cycles} cycles")
    else:
        logger.info("Mode continu : infini")
    logger.info("Fréquence: toutes les 30 minutes")
    logger.info("Ctrl+C pour arrêter")

    # Créer UNE SEULE FOIS
    collector = WeatherCollector()
    mongo = get_mongodb_client()

    cycle_count = 0
    total_collected = 0

    try:
        while True:
            cycle_count += 1
            logger.info(f"\nCYCLE MÉTÉO {cycle_count}")

            collected = collect_weather_cycle(collector, mongo)  # Passer collector et mongo
            total_collected += collected

            logger.info(f"\nTotal collecté: {total_collected} observations en {cycle_count} cycles")

            if max_cycles > 0 and cycle_count >= max_cycles:
                logger.info(f"\n {max_cycles} cycles terminés")
                break

            pause_time = 30 if max_cycles > 0 else 1800
            pause_msg = "30 secondes" if max_cycles > 0 else "30 minutes"
            logger.info(f"Pause {pause_msg}...")
            time.sleep(pause_time)

    except KeyboardInterrupt:
        logger.info("\n\nArrêt par utilisateur")
        logger.info(f"Total: {total_collected} observations en {cycle_count} cycles")
    finally:
        # Fermer UNE SEULE FOIS à la fin
        collector.close()
        mongo.close()


if __name__ == "__main__":
    main()

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


def collect_weather_cycle():
    """Un cycle de collecte météo"""
    logger.info("="*60)
    logger.info(f"DÉBUT COLLECTE MÉTÉO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    collector = WeatherCollector()
    mongo = get_mongodb_client()
    
    # Aéroports à surveiller
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
                # Extraire et formater les données météo
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
    
    collector.close()
    mongo.close()
    
    logger.info("="*60)
    
    return len(all_weather)


def main():
    logger.info("DÉMARRAGE COLLECTE MÉTÉO CONTINUE")
    logger.info("Fréquence: toutes les 30 minutes")
    logger.info("Ctrl+C pour arrêter")

    cycle_count = 0
    total_collected = 0

    try:
        while True:
            cycle_count += 1
            logger.info(f"\nCYCLE MÉTÉO {cycle_count}")

            collected = collect_weather_cycle()
            total_collected += collected

            logger.info(f"\nTotal collecté: {total_collected} observations en {cycle_count} cycles")
            logger.info("Pause 30 minutes...")
            time.sleep(1800)

    except KeyboardInterrupt:
        logger.info("\n\nArrêt par utilisateur")
        logger.info(f"Total: {total_collected} observations en {cycle_count} cycles")


if __name__ == "__main__":
    main()

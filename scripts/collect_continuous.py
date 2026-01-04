#!/usr/bin/env python3
"""Collecte continue de vols AviationStack"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import datetime
from src.data_collection import AviationStackCollector
from src.data_processing import get_mongodb_client
from src.utils import get_logger

logger = get_logger('continuous_collector')

def collect_cycle():
    """Un cycle de collecte"""
    logger.info("="*60)
    logger.info(f"DÉBUT COLLECTE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)
    
    collector = AviationStackCollector()
    mongo = get_mongodb_client()
    
    # Collecter depuis les aéroports principaux
    all_flights = []
    airports = ['CDG', 'ORY', 'AMS', 'LHR', 'JFK']
    
    for airport in airports:
        flights = collector.collect_flights(dep_iata=airport, limit=50)
        all_flights.extend(flights)
        logger.info(f"{airport}: {len(flights)} vols")
        time.sleep(2)  # Pause entre aéroports
    
    # Sauvegarder
    if all_flights:
        saved = mongo.insert_aviationstack_flights_bulk(all_flights)
        logger.info(f"Sauvegardé: {saved} vols")
    
    # Stats
    stats = mongo.get_statistics()
    logger.info(f"Total en base: {stats['aviationstack']} vols")
    
    collector.close()
    mongo.close()
    
    logger.info(f"Stats collector: {collector.get_stats()}")
    logger.info("="*60)
    
    return len(all_flights)

def main():
    logger.info("DÉMARRAGE COLLECTE CONTINUE")
    logger.info("Ctrl+C pour arrêter")
    
    cycle_count = 0
    total_collected = 0
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"\nCYCLE {cycle_count}")
            
            collected = collect_cycle()
            total_collected += collected
            
            logger.info(f"\nTotal collecté: {total_collected} vols en {cycle_count} cycles")
            logger.info("Pause 5 minutes...")
            time.sleep(3600)  # 5 minutes
            
    except KeyboardInterrupt:
        logger.info("\n\nArrêt par utilisateur")
        logger.info(f"Total: {total_collected} vols en {cycle_count} cycles")

if __name__ == "__main__":
    main()

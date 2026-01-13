#!/usr/bin/env python3
"""Exploration rapide des données collectées"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processing import get_mongodb_client
from datetime import datetime
import pandas as pd

def explore():
    print("="*60)
    print("EXPLORATION DES DONNEES")
    print("="*60)

    mongo = get_mongodb_client()

    # Stats globales
    stats = mongo.get_statistics()
    print(f"\nSTATS GLOBALES:")
    print(f"  Vols AviationStack: {stats['aviationstack']}")
    print(f"  Vols AF-KLM: {stats['afklm']}")
    print(f"  Données météo: {stats['weather']}")

    # Récupérer les vols
    flights = mongo.get_aviationstack_flights(limit=1000)

    if flights:
        print(f"\nANALYSE DES VOLS (sample: {len(flights)}):")

        # Statuts
        statuses = {}
        airlines = {}
        airports_dep = {}

        for f in flights:
            # Status
            status = f.get('flight_status', 'unknown')
            statuses[status] = statuses.get(status, 0) + 1

            # Airline
            airline = f.get('airline', {}).get('name', 'Unknown')
            airlines[airline] = airlines.get(airline, 0) + 1

            # Departure airport
            dep = f.get('departure', {}).get('iata', 'Unknown')
            airports_dep[dep] = airports_dep.get(dep, 0) + 1

        print("\nTop 5 Status:")
        for status, count in sorted(statuses.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {status}: {count}")

        print("\nTop 5 Compagnies:")
        for airline, count in sorted(airlines.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {airline}: {count}")

        print("\nTop 5 Aéroports (départ):")
        for airport, count in sorted(airports_dep.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {airport}: {count}")

        # Vols récents
        print("\nDERNIERS VOLS COLLECTES:")
        for f in flights[:5]:
            flight_info = f.get('flight', {})
            dep = f.get('departure', {})
            arr = f.get('arrival', {})
            print(f"  {flight_info.get('iata', 'N/A')}: {dep.get('iata')} → {arr.get('iata')} ({f.get('flight_status')})")

    mongo.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    explore()

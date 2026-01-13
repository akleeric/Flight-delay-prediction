#!/usr/bin/env python3
"""Préparation des données pour ML - AVEC AF-KLM"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processing import get_mongodb_client
from datetime import datetime
import pandas as pd

def extract_aviationstack_features(mongo):
    """Extrait features depuis AviationStack"""
    print("\n[1/2] Extraction AviationStack...")
    flights = mongo.get_aviationstack_flights(limit=5000)

    data = []
    for flight in flights:
        try:
            flight_info = flight.get('flight', {})
            departure = flight.get('departure', {})
            arrival = flight.get('arrival', {})
            airline = flight.get('airline', {})

            dep_time_str = departure.get('scheduled')
            if not dep_time_str:
                continue

            try:
                dep_time = datetime.fromisoformat(dep_time_str.replace('Z', '+00:00'))
            except:
                continue

            delay = departure.get('delay', 0)

            row = {
                'source': 'aviationstack',
                'flight_iata': flight_info.get('iata'),
                'airline_iata': airline.get('iata'),
                'airline_name': airline.get('name'),
                'departure_airport': departure.get('iata'),
                'arrival_airport': arrival.get('iata'),
                'scheduled_hour': dep_time.hour,
                'day_of_week': dep_time.weekday(),
                'month': dep_time.month,
                'is_weekend': 1 if dep_time.weekday() >= 5 else 0,
                'status': flight.get('flight_status', 'unknown'),
                'delay_minutes': delay if delay else 0,
                'is_delayed': 1 if delay and delay > 15 else 0
            }
            data.append(row)
        except Exception:
            continue

    print(f"  {len(data)} vols AviationStack")
    return data

def extract_afklm_features(mongo):
    """Extrait features depuis AF-KLM"""
    print("\n[2/2]  Extraction AF-KLM...")

    # Accès direct à la collection
    flights = list(mongo.db.afklm_flights.find())

    data = []
    for flight in flights:
        try:
            route = flight.get('route', [])
            if len(route) < 2:
                continue

            airline = flight.get('airline', {})
            flight_date = flight.get('flightScheduleDate', '')

            if not flight_date:
                continue

            # Parser date
            try:
                dep_time = datetime.fromisoformat(flight_date)
            except:
                continue

            # Extraction delay depuis legs
            delay = 0
            legs = flight.get('flightLegs', [])
            if legs:
                first_leg = legs[0]
                sched = first_leg.get('scheduledDepartureUTCDateTime', '')
                actual = first_leg.get('actualDepartureUTCDateTime', '')

                if sched and actual:
                    try:
                        sched_dt = datetime.fromisoformat(sched.replace('Z', '+00:00'))
                        actual_dt = datetime.fromisoformat(actual.replace('Z', '+00:00'))
                        delay = int((actual_dt - sched_dt).total_seconds() / 60)
                    except:
                        pass

            row = {
                'source': 'airfrance_klm',
                'flight_iata': f"{airline.get('code', '')}{flight.get('flightNumber', '')}",
                'airline_iata': airline.get('code', ''),
                'airline_name': airline.get('name', ''),
                'departure_airport': route[0],
                'arrival_airport': route[-1],
                'scheduled_hour': dep_time.hour,
                'day_of_week': dep_time.weekday(),
                'month': dep_time.month,
                'is_weekend': 1 if dep_time.weekday() >= 5 else 0,
                'status': flight.get('flightStatusPublic', 'unknown'),
                'delay_minutes': delay,
                'is_delayed': 1 if delay > 15 else 0
            }
            data.append(row)
        except Exception:
            continue

    print(f"    {len(data)} vols AF-KLM")
    return data

def extract_features():
    """Extrait features depuis TOUTES les sources"""
    print("="*60)
    print("EXTRACTION FEATURES ML - 2 SOURCES")
    print("="*60)

    mongo = get_mongodb_client()

    # Extraction des 2 sources
    as_data = extract_aviationstack_features(mongo)
    afklm_data = extract_afklm_features(mongo)

    # Unification
    print("\n[3/3]  Unification...")
    all_data = as_data + afklm_data
    df = pd.DataFrame(all_data)

    print(f"    {len(df)} vols totaux")
    print(f"      - AviationStack: {len(df[df['source']=='aviationstack'])}")
    print(f"      - AF-KLM: {len(df[df['source']=='airfrance_klm'])}")

    # Stats
    print(f"\n📊 STATISTIQUES:")
    print(f"   Aperçu:")
    print(df.head())

    print(f"\n   Distribution retards (is_delayed):")
    print(df['is_delayed'].value_counts())
    print(f"   Taux de retard: {df['is_delayed'].mean()*100:.1f}%")

    print(f"\n   Stats delay (minutes):")
    print(df['delay_minutes'].describe())

    print(f"\n   Top 10 aéroports (départ):")
    print(df['departure_airport'].value_counts().head(10))

    print(f"\n   Top 10 compagnies:")
    print(df['airline_name'].value_counts().head(10))

    # Sauvegarde
    output_path = Path('data/processed/flights_features.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print(f"\n Dataset sauvegardé: {output_path}")
    print("="*60)

    mongo.close()
    return df

if __name__ == "__main__":
    df = extract_features()

#!/usr/bin/env python3
"""Préparation des données pour ML"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_processing import get_mongodb_client
from datetime import datetime
import pandas as pd
import json

def extract_features():
    """Extrait les features des vols MongoDB"""
    print("="*60)
    print("EXTRACTION DES FEATURES POUR ML")
    print("="*60)
    
    mongo = get_mongodb_client()
    
    # Récupérer tous les vols
    flights = mongo.get_aviationstack_flights(limit=5000)
    print(f"\n✓ {len(flights)} vols récupérés")
    
    # Préparer les données
    data = []
    
    for flight in flights:
        try:
            # Infos de base
            flight_info = flight.get('flight', {})
            departure = flight.get('departure', {})
            arrival = flight.get('arrival', {})
            airline = flight.get('airline', {})
            
            # Date de départ
            dep_time_str = departure.get('scheduled')
            if not dep_time_str:
                continue
            
            # Parser la date
            try:
                dep_time = datetime.fromisoformat(dep_time_str.replace('Z', '+00:00'))
            except:
                continue
            
            # Features temporelles
            hour = dep_time.hour
            day_of_week = dep_time.weekday()  # 0=Lundi, 6=Dimanche
            month = dep_time.month
            is_weekend = 1 if day_of_week >= 5 else 0
            
            # Delay (target variable)
            delay = departure.get('delay')
            is_delayed = 1 if delay and delay > 15 else 0
            
            # Status
            status = flight.get('flight_status', 'unknown')
            
            row = {
                'flight_iata': flight_info.get('iata'),
                'airline_iata': airline.get('iata'),
                'airline_name': airline.get('name'),
                'departure_airport': departure.get('iata'),
                'arrival_airport': arrival.get('iata'),
                'scheduled_hour': hour,
                'day_of_week': day_of_week,
                'month': month,
                'is_weekend': is_weekend,
                'status': status,
                'delay_minutes': delay if delay else 0,
                'is_delayed': is_delayed
            }
            
            data.append(row)
            
        except Exception as e:
            continue
    
    # Créer DataFrame
    df = pd.DataFrame(data)
    
    print(f"\n✓ Dataset créé: {len(df)} vols")
    print(f"\nAperçu des features:")
    print(df.head())
    
    print(f"\nDistribution de la target (is_delayed):")
    print(df['is_delayed'].value_counts())
    
    print(f"\nStats delay:")
    print(df['delay_minutes'].describe())
    
    # Sauvegarder
    output_path = Path('data/processed/flights_features.csv')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✓ Dataset sauvegardé: {output_path}")
    
    # Stats par aéroport
    print(f"\nVols par aéroport (départ):")
    print(df['departure_airport'].value_counts().head(10))
    
    print(f"\nVols par compagnie:")
    print(df['airline_name'].value_counts().head(10))
    
    mongo.close()
    print("\n" + "="*60)
    
    return df

if __name__ == "__main__":
    df = extract_features()

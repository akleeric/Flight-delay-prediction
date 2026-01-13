#!/usr/bin/env python3
"""Feature engineering avancé - 24 features conformes UML"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'data_processing'))
from feature_calculator import FeatureCalculator


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance entre deux points GPS"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371
    return round(c * r, 2)


def get_season(month):
    """Retourne la saison"""
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:
        return 'fall'


def get_time_of_day(hour):
    """Retourne la période de la journée"""
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    elif 18 <= hour < 22:
        return 'evening'
    else:
        return 'night'


AIRPORT_COORDS = {
    'CDG': (49.0097, 2.5479),
    'ORY': (48.7233, 2.3794),
    'LHR': (51.4700, -0.4543),
    'JFK': (40.6413, -73.7781),
    'AMS': (52.3105, 4.7683)
}

HOLIDAYS = [
    '2025-01-01', '2025-04-21', '2025-05-01', '2025-05-08',
    '2025-05-29', '2025-06-09', '2025-07-14', '2025-08-15',
    '2025-11-01', '2025-11-11', '2025-12-25',
    '2026-01-01', '2026-04-06', '2026-05-01', '2026-05-08',
    '2026-05-14', '2026-05-25', '2026-07-14', '2026-08-15',
    '2026-11-01', '2026-11-11', '2026-12-25'
]


def build_enhanced_features(mongodb_collection_name='aviationstack_flights',
                           output_csv='data/processed/flights_features_enhanced.csv'):
    """Construit le dataset avec les 24 features conformes UML"""
    print("="*70)
    print("FEATURE ENGINEERING AVANCÉ - 24 FEATURES UML")
    print("="*70)

    from src.data_processing import get_mongodb_client

    mongo = get_mongodb_client()
    print(f"\n[1/6] Chargement données MongoDB ({mongodb_collection_name})...")

    flights = list(mongo.db[mongodb_collection_name].find({}))
    print(f"  ✓ {len(flights)} vols chargés")

    if len(flights) == 0:
        print(" Aucun vol trouvé dans MongoDB!")
        mongo.close()
        return

    print("\n[2/6] Conversion en DataFrame...")
    df = pd.DataFrame(flights)

    df['flight_iata'] = df['flight'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df['airline_iata'] = df['airline'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df['airline_name'] = df['airline'].apply(lambda x: x.get('name') if isinstance(x, dict) else None)
    df['departure_airport'] = df['departure'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df['arrival_airport'] = df['arrival'].apply(lambda x: x.get('iata') if isinstance(x, dict) else None)
    df['scheduled_departure'] = df['departure'].apply(lambda x: x.get('scheduled') if isinstance(x, dict) else None)
    df['actual_departure'] = df['departure'].apply(lambda x: x.get('actual') if isinstance(x, dict) else None)
    df['delay_minutes'] = df['departure'].apply(lambda x: x.get('delay', 0) if isinstance(x, dict) else 0)

    df['scheduled_departure'] = pd.to_datetime(df['scheduled_departure'])
    df['actual_departure'] = pd.to_datetime(df['actual_departure'])

    df = df.dropna(subset=['flight_iata', 'scheduled_departure', 'departure_airport', 'arrival_airport'])
    df = df.drop_duplicates(subset=['flight_iata', 'scheduled_departure'])

    print(f"  ✓ {len(df)} vols après nettoyage")

    print("\n[3/6] Calcul features temporelles...")
    df['scheduled_hour'] = df['scheduled_departure'].dt.hour
    df['day_of_week'] = df['scheduled_departure'].dt.dayofweek
    df['month'] = df['scheduled_departure'].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)

    df['date_str'] = df['scheduled_departure'].dt.strftime('%Y-%m-%d')
    df['is_holiday'] = df['date_str'].isin(HOLIDAYS).astype(int)

    df['season'] = df['month'].apply(get_season)
    df['time_of_day'] = df['scheduled_hour'].apply(get_time_of_day)

    print(f"  ✓ 7 features temporelles créées")

    print("\n[4/6] Calcul features opérationnelles...")

    def calculate_distance(row):
        dep = row['departure_airport']
        arr = row['arrival_airport']

        if dep in AIRPORT_COORDS and arr in AIRPORT_COORDS:
            dep_coords = AIRPORT_COORDS[dep]
            arr_coords = AIRPORT_COORDS[arr]
            return haversine_distance(dep_coords[0], dep_coords[1], 
                                     arr_coords[0], arr_coords[1])
        return np.nan

    df['flight_distance_km'] = df.apply(calculate_distance, axis=1)
    df['scheduled_duration_min'] = (df['flight_distance_km'] / 800 * 60).round(0)

    le_airline = LabelEncoder()
    le_dep = LabelEncoder()
    le_arr = LabelEncoder()

    df['airline_encoded'] = le_airline.fit_transform(df['airline_iata'])
    df['dep_encoded'] = le_dep.fit_transform(df['departure_airport'])
    df['arr_encoded'] = le_arr.fit_transform(df['arrival_airport'])

    print(f"  ✓ 3 features opérationnelles créées")

    print("\n[5/6] Intégration features météorologiques...")
    print("  - Collecte météo continue nécessaire pour données complètes")
    print("  - Utilisation de valeurs par défaut si météo absente")

    weather_data = {}
    for airport in df['departure_airport'].unique():
        weather = mongo.db.weather_data.find_one(
            {'airport_iata': airport},
            sort=[('observation_time', -1)]
        )
        if weather:
            weather_data[airport] = weather

    def get_weather_features(row, prefix='dep'):
        airport = row['departure_airport'] if prefix == 'dep' else row['arrival_airport']
        weather = weather_data.get(airport, {})

        bad_conditions = ['Rain', 'Snow', 'Thunderstorm', 'Fog']

        return {
            f'{prefix}_temperature': weather.get('temperature', 15.0),
            f'{prefix}_wind_speed': weather.get('wind_speed', 10.0),
            f'{prefix}_visibility': weather.get('visibility', 10000),
            f'{prefix}_precipitation': weather.get('precipitation', 0.0),
            f'{prefix}_weather_bad': 1 if weather.get('weather_condition') in bad_conditions else 0
        }

    for prefix in ['dep', 'arr']:
        weather_features = df.apply(lambda row: get_weather_features(row, prefix), axis=1, result_type='expand')
        df = pd.concat([df, weather_features], axis=1)

    print(f"  ✓ 10 features météorologiques créées ({len(weather_data)} aéroports avec météo)")

    print("\n[6/6] Calcul features agrégées...")
    print("  - Calcul intensif (requêtes MongoDB historiques)...")

    calculator = FeatureCalculator()

    aggregated_features = []

    for idx, row in df.iterrows():
        try:
            flight_data = {
                'airline_iata': row['airline_iata'],
                'departure_airport': row['departure_airport'],
                'arrival_airport': row['arrival_airport'],
                'scheduled_departure': row['scheduled_departure'],
                'aircraft_registration': None
            }

            features = calculator.calculate_all_features(flight_data)
            aggregated_features.append(features)

            if (idx + 1) % 100 == 0:
                print(f"    Progression: {idx+1}/{len(df)} vols")

        except Exception as e:
            aggregated_features.append({
                'airline_avg_delay': 0.0,
                'route_avg_delay': 0.0,
                'airport_congestion': 0.5,
                'prev_flight_delay': 0
            })

    calculator.close()

    agg_df = pd.DataFrame(aggregated_features)
    df = pd.concat([df, agg_df], axis=1)

    print(f"  4 features agrégées créées")

    df['is_delayed'] = (df['delay_minutes'] > 15).astype(int)

    feature_columns = [
        'scheduled_hour', 'day_of_week', 'month', 'is_weekend', 'is_holiday', 'season', 'time_of_day',
        'dep_temperature', 'dep_wind_speed', 'dep_visibility', 'dep_precipitation', 'dep_weather_bad',
        'arr_temperature', 'arr_wind_speed', 'arr_visibility', 'arr_precipitation', 'arr_weather_bad',
        'flight_distance_km', 'scheduled_duration_min',
        'airline_encoded', 'dep_encoded', 'arr_encoded',
        'airline_avg_delay', 'route_avg_delay', 'airport_congestion', 'prev_flight_delay',
        'flight_iata', 'airline_iata', 'airline_name', 'departure_airport', 'arrival_airport',
        'delay_minutes', 'is_delayed'
    ]

    df_final = df[feature_columns].copy()

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df_final.to_csv(output_path, index=False)

    print("\n" + "="*70)
    print("RÉSUME")
    print("="*70)
    print(f"Total vols: {len(df_final)}")
    print(f"Features: 24 (+ métadonnées)")
    print(f"Distribution cible:")
    print(f"  - À l'heure: {(df_final['is_delayed'] == 0).sum()} ({(df_final['is_delayed'] == 0).sum()/len(df_final)*100:.1f}%)")
    print(f"  - En retard: {(df_final['is_delayed'] == 1).sum()} ({(df_final['is_delayed'] == 1).sum()/len(df_final)*100:.1f}%)")
    print(f"\n✓ Dataset sauvegardé: {output_path}")
    print("="*70)

    mongo.close()

    return df_final


if __name__ == "__main__":
    build_enhanced_features()

"""Calculateur de features agrégées pour ML avancé"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.data_processing import get_mongodb_client


class FeatureCalculator:
    """Calcule les features agrégées à partir de l'historique"""

    def __init__(self):
        self.mongo = get_mongodb_client()

    def calculate_airline_avg_delay(self, airline_iata: str, 
                                   reference_date: datetime,
                                   window_days: int = 30) -> float:
        """
        Retard moyen de la compagnie sur les N derniers jours

        Args:
            airline_iata: Code IATA compagnie (ex: "AF")
            reference_date: Date de référence
            window_days: Fenêtre temporelle en jours

        Returns:
            Retard moyen en minutes
        """
        start_date = reference_date - timedelta(days=window_days)

        pipeline = [
            {
                '$match': {
                    'airline.iata': airline_iata,
                    'departure.scheduled': {
                        '$gte': start_date,
                        '$lt': reference_date
                    },
                    'departure.delay': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avg_delay': {'$avg': '$departure.delay'}
                }
            }
        ]

        result = list(self.mongo.db.aviationstack_flights.aggregate(pipeline))

        if result and result[0]['avg_delay'] is not None:
            return round(float(result[0]['avg_delay']), 2)
        return 0.0

    def calculate_route_avg_delay(self, departure_iata: str, 
                                 arrival_iata: str,
                                 reference_date: datetime,
                                 window_days: int = 30) -> float:
        """
        Retard moyen de la route sur les N derniers jours

        Args:
            departure_iata: Aéroport de départ (ex: "CDG")
            arrival_iata: Aéroport d'arrivée (ex: "JFK")
            reference_date: Date de référence
            window_days: Fenêtre temporelle en jours

        Returns:
            Retard moyen en minutes
        """
        start_date = reference_date - timedelta(days=window_days)

        pipeline = [
            {
                '$match': {
                    'departure.iata': departure_iata,
                    'arrival.iata': arrival_iata,
                    'departure.scheduled': {
                        '$gte': start_date,
                        '$lt': reference_date
                    },
                    'departure.delay': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avg_delay': {'$avg': '$departure.delay'}
                }
            }
        ]

        result = list(self.mongo.db.aviationstack_flights.aggregate(pipeline))

        if result and result[0]['avg_delay'] is not None:
            return round(float(result[0]['avg_delay']), 2)
        return 0.0

    def calculate_airport_congestion(self, airport_iata: str,
                                    reference_datetime: datetime,
                                    window_hours: int = 2) -> float:
        """
        Score de congestion aéroport (nombre vols / capacité théorique)

        Args:
            airport_iata: Code IATA aéroport (ex: "CDG")
            reference_datetime: Date et heure de référence
            window_hours: Fenêtre temporelle en heures

        Returns:
            Score congestion (0.0 = vide, 1.0+ = saturé)
        """
        start_time = reference_datetime - timedelta(hours=window_hours/2)
        end_time = reference_datetime + timedelta(hours=window_hours/2)

        # Compter vols au départ + arrivée
        departures = self.mongo.db.aviationstack_flights.count_documents({
            'departure.iata': airport_iata,
            'departure.scheduled': {'$gte': start_time, '$lt': end_time}
        })

        arrivals = self.mongo.db.aviationstack_flights.count_documents({
            'arrival.iata': airport_iata,
            'arrival.scheduled': {'$gte': start_time, '$lt': end_time}
        })

        total_flights = departures + arrivals

        # Capacités théoriques par heure (estimation)
        AIRPORT_CAPACITIES = {
            'CDG': 120,  # Charles de Gaulle
            'ORY': 60,   # Orly
            'LHR': 90,   # Heathrow
            'JFK': 100,  # JFK
            'AMS': 100,  # Schiphol
        }

        capacity = AIRPORT_CAPACITIES.get(airport_iata, 80) * window_hours

        congestion = total_flights / capacity if capacity > 0 else 0.0
        return round(min(congestion, 1.5), 2)  # Cap à 1.5

    def get_previous_flight_delay(self, aircraft_registration: Optional[str],
                                  airline_iata: str,
                                  reference_datetime: datetime) -> int:
        """
        Retard du vol précédent du même avion

        Args:
            aircraft_registration: Immatriculation avion (peut être None)
            airline_iata: Compagnie (fallback si pas de registration)
            reference_datetime: Date et heure de référence

        Returns:
            Retard en minutes (0 si pas d'info)
        """
        # Si on a l'immatriculation, chercher le vol précédent
        if aircraft_registration:
            previous_flight = self.mongo.db.aviationstack_flights.find_one(
                {
                    'aircraft.registration': aircraft_registration,
                    'departure.actual': {'$lt': reference_datetime}
                },
                sort=[('departure.actual', -1)]
            )

            if previous_flight and previous_flight.get('departure', {}).get('delay'):
                return int(previous_flight['departure']['delay'])

        # Fallback : retard moyen de la compagnie sur dernière heure
        one_hour_ago = reference_datetime - timedelta(hours=1)

        pipeline = [
            {
                '$match': {
                    'airline.iata': airline_iata,
                    'departure.actual': {'$gte': one_hour_ago, '$lt': reference_datetime},
                    'departure.delay': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avg_delay': {'$avg': '$departure.delay'}
                }
            }
        ]

        result = list(self.mongo.db.aviationstack_flights.aggregate(pipeline))

        if result and result[0]['avg_delay'] is not None:
            return int(result[0]['avg_delay'])

        return 0

    def calculate_all_features(self, flight_data: Dict) -> Dict:
        """
        Calcule toutes les features agrégées pour un vol

        Args:
            flight_data: Dict avec clés airline_iata, departure_airport, 
                        arrival_airport, scheduled_departure, aircraft_registration

        Returns:
            Dict avec les 4 features agrégées
        """
        scheduled_dt = flight_data['scheduled_departure']
        if isinstance(scheduled_dt, str):
            scheduled_dt = datetime.fromisoformat(scheduled_dt.replace('Z', '+00:00'))

        features = {
            'airline_avg_delay': self.calculate_airline_avg_delay(
                flight_data['airline_iata'],
                scheduled_dt
            ),
            'route_avg_delay': self.calculate_route_avg_delay(
                flight_data['departure_airport'],
                flight_data['arrival_airport'],
                scheduled_dt
            ),
            'airport_congestion': self.calculate_airport_congestion(
                flight_data['departure_airport'],
                scheduled_dt
            ),
            'prev_flight_delay': self.get_previous_flight_delay(
                flight_data.get('aircraft_registration'),
                flight_data['airline_iata'],
                scheduled_dt
            )
        }

        return features

    def close(self):
        """Fermer connexion MongoDB"""
        self.mongo.close()


# Exemple d'utilisation
if __name__ == "__main__":
    print("="*60)
    print("TEST FEATURE CALCULATOR")
    print("="*60)

    calculator = FeatureCalculator()

    # Test sur un vol exemple
    test_flight = {
        'airline_iata': 'AF',
        'departure_airport': 'CDG',
        'arrival_airport': 'JFK',
        'scheduled_departure': datetime.now(),
        'aircraft_registration': None  # Pas d'immat dans le dataset actuel
    }

    print("\nCalcul features agrégées pour vol test:")
    print(f"Route: {test_flight['departure_airport']} → {test_flight['arrival_airport']}")
    print(f"Compagnie: {test_flight['airline_iata']}")

    features = calculator.calculate_all_features(test_flight)

    print("\nRésultats:")
    for feature, value in features.items():
        print(f"  {feature}: {value}")

    calculator.close()
    print("\n✓ Test terminé")

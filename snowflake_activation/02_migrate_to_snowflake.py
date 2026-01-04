#!/usr/bin/env python3
"""
Migration MongoDB → Snowflake
Script complet de migration des données
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pymongo import MongoClient
    import snowflake.connector
    from snowflake.connector.errors import DatabaseError
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Erreur import: {e}")
    print("\nInstallez les dépendances:")
    print("pip install pymongo snowflake-connector-python python-dotenv")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration_snowflake.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


class MongoDBExtractor:
    """Extracteur de données MongoDB"""
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGODB_URI')
        self.db_name = os.getenv('MONGODB_DB_NAME', 'flight_delay_db')
        self.client = None
        self.db = None
        
    def connect(self):
        """Connexion à MongoDB"""
        try:
            logger.info("Connexion à MongoDB...")
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client[self.db_name]
            self.client.server_info()
            logger.info(f"✓ Connecté à MongoDB: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur connexion MongoDB: {e}")
            return False
    
    def extract_flights(self) -> List[Dict]:
        """Extraire tous les vols de MongoDB"""
        try:
            logger.info("Extraction des vols...")
            
            collections = ['aviationstack_flights', 'afklm_flights', 'flights_realtime']
            all_flights = []
            
            for coll_name in collections:
                if coll_name in self.db.list_collection_names():
                    collection = self.db[coll_name]
                    flights = list(collection.find({}))
                    all_flights.extend(flights)
                    logger.info(f"  ✓ {coll_name}: {len(flights)} vols")
            
            logger.info(f"Total extrait: {len(all_flights)} vols")
            return all_flights
            
        except Exception as e:
            logger.error(f"❌ Erreur extraction vols: {e}")
            return []
    
    def extract_weather(self) -> List[Dict]:
        """Extraire données météo de MongoDB"""
        try:
            logger.info("Extraction météo...")
            
            if 'weather_data' in self.db.list_collection_names():
                collection = self.db['weather_data']
                weather_data = list(collection.find({}))
                logger.info(f"  ✓ weather_data: {len(weather_data)} observations")
                return weather_data
            else:
                logger.warning("  ⚠ Collection weather_data non trouvée")
                return []
                
        except Exception as e:
            logger.error(f"❌ Erreur extraction météo: {e}")
            return []
    
    def close(self):
        """Fermer connexion"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB déconnecté")


class SnowflakeLoader:
    """Chargeur de données Snowflake"""
    
    def __init__(self):
        self.account = os.getenv('SNOWFLAKE_ACCOUNT')
        self.user = os.getenv('SNOWFLAKE_USER')
        self.password = os.getenv('SNOWFLAKE_PASSWORD')
        self.warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'FLIGHT_WH')
        self.database = os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_DELAYS_DB')
        self.schema = os.getenv('SNOWFLAKE_SCHEMA', 'RAW_DATA')
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Connexion à Snowflake"""
        try:
            logger.info("Connexion à Snowflake...")
            
            self.conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema
            )
            
            self.cursor = self.conn.cursor()
            
            self.cursor.execute("SELECT CURRENT_VERSION()")
            version = self.cursor.fetchone()[0]
            logger.info(f"✓ Connecté à Snowflake: {self.database}")
            logger.info(f"  Version: {version}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion Snowflake: {e}")
            return False
    
    def ensure_reference_data(self):
        """S'assurer que les données de référence existent"""
        logger.info("Vérification données de référence...")
        
        airports_data = [
            ('CDG', 'LFPG', 'Charles de Gaulle', 'Paris', 'France', 'FR', 49.0097, 2.5479),
            ('ORY', 'LFPO', 'Orly', 'Paris', 'France', 'FR', 48.7233, 2.3794),
            ('JFK', 'KJFK', 'JFK International', 'New York', 'USA', 'US', 40.6413, -73.7781),
            ('LHR', 'EGLL', 'Heathrow', 'London', 'UK', 'GB', 51.4700, -0.4543),
            ('AMS', 'EHAM', 'Schiphol', 'Amsterdam', 'Netherlands', 'NL', 52.3086, 4.7639),
        ]
        
        airlines_data = [
            ('AF', 'AFR', 'Air France', 'France', 'FR'),
            ('KL', 'KLM', 'KLM', 'Netherlands', 'NL'),
            ('BA', 'BAW', 'British Airways', 'UK', 'GB'),
            ('LH', 'DLH', 'Lufthansa', 'Germany', 'DE'),
        ]
        
        try:
            for airport in airports_data:
                self.cursor.execute("""
                    MERGE INTO AIRPORTS t USING (
                        SELECT %s AS iata, %s AS icao, %s AS name, %s AS city, 
                               %s AS country, %s AS code, %s AS lat, %s AS lon
                    ) s ON t.iata_code = s.iata
                    WHEN NOT MATCHED THEN
                        INSERT (iata_code, icao_code, name, city, country, country_code, latitude, longitude)
                        VALUES (s.iata, s.icao, s.name, s.city, s.country, s.code, s.lat, s.lon)
                """, airport)
            
            for airline in airlines_data:
                self.cursor.execute("""
                    MERGE INTO AIRLINES t USING (
                        SELECT %s AS iata, %s AS icao, %s AS name, %s AS country, %s AS code
                    ) s ON t.iata_code = s.iata
                    WHEN NOT MATCHED THEN
                        INSERT (iata_code, icao_code, name, country, country_code)
                        VALUES (s.iata, s.icao, s.name, s.country, s.code)
                """, airline)
            
            self.conn.commit()
            logger.info("✓ Données de référence vérifiées")
            
        except Exception as e:
            logger.error(f"❌ Erreur données de référence: {e}")
    
    def transform_and_load_flights(self, mongo_flights: List[Dict]) -> Tuple[int, int]:
        """Transformer et charger les vols dans Snowflake"""
        logger.info(f"Chargement de {len(mongo_flights)} vols...")
        
        inserted = 0
        failed = 0
        
        for flight_doc in mongo_flights:
            try:
                flight_data = self._transform_flight(flight_doc)
                
                if flight_data:
                    self._insert_flight(flight_data)
                    inserted += 1
                    
                    if inserted % 100 == 0:
                        logger.info(f"  Progression: {inserted}/{len(mongo_flights)}")
                        self.conn.commit()
                
            except Exception as e:
                failed += 1
                logger.warning(f"  ⚠ Erreur vol: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"✓ Vols chargés: {inserted} insérés, {failed} échoués")
        
        return inserted, failed
    
    def _transform_flight(self, doc: Dict) -> Optional[Dict]:
        """Transformer un document MongoDB en données Snowflake"""
        try:
            flight_info = doc.get('flight', {})
            airline_info = doc.get('airline', {})
            departure_info = doc.get('departure', {})
            arrival_info = doc.get('arrival', {})
            
            transformed = {
                'flight_iata': flight_info.get('iata', ''),
                'flight_icao': flight_info.get('icao'),
                'flight_number': flight_info.get('number', ''),
                'airline_code': airline_info.get('iata', ''),
                'departure_code': departure_info.get('iata', ''),
                'arrival_code': arrival_info.get('iata', ''),
                'scheduled_departure': departure_info.get('scheduled'),
                'scheduled_arrival': arrival_info.get('scheduled'),
                'actual_departure': departure_info.get('actual'),
                'actual_arrival': arrival_info.get('actual'),
                'estimated_departure': departure_info.get('estimated'),
                'estimated_arrival': arrival_info.get('estimated'),
                'departure_delay': departure_info.get('delay'),
                'arrival_delay': arrival_info.get('delay'),
                'departure_terminal': departure_info.get('terminal'),
                'departure_gate': departure_info.get('gate'),
                'arrival_terminal': arrival_info.get('terminal'),
                'arrival_gate': arrival_info.get('gate'),
                'baggage_belt': arrival_info.get('baggage'),
                'flight_status': doc.get('status', 'unknown'),
                'flight_date': None,
                'data_source': doc.get('data_source', 'mongodb')
            }
            
            if transformed['scheduled_departure']:
                if isinstance(transformed['scheduled_departure'], str):
                    transformed['flight_date'] = transformed['scheduled_departure'][:10]
                else:
                    transformed['flight_date'] = transformed['scheduled_departure'].strftime('%Y-%m-%d')
            
            if transformed['departure_delay'] is not None:
                transformed['is_delayed'] = transformed['departure_delay'] > 15
            else:
                transformed['is_delayed'] = False
            
            return transformed
            
        except Exception as e:
            logger.warning(f"Erreur transformation: {e}")
            return None
    
    def _insert_flight(self, flight_data: Dict):
        """Insérer un vol dans Snowflake"""
        
        insert_sql = """
        MERGE INTO FLIGHTS t USING (
            SELECT 
                %(flight_iata)s AS flight_iata,
                %(flight_date)s AS flight_date,
                %(flight_icao)s AS flight_icao,
                %(flight_number)s AS flight_number,
                (SELECT airline_id FROM AIRLINES WHERE iata_code = %(airline_code)s) AS airline_id,
                (SELECT airport_id FROM AIRPORTS WHERE iata_code = %(departure_code)s) AS departure_airport_id,
                (SELECT airport_id FROM AIRPORTS WHERE iata_code = %(arrival_code)s) AS arrival_airport_id,
                %(scheduled_departure)s AS scheduled_departure,
                %(scheduled_arrival)s AS scheduled_arrival,
                %(actual_departure)s AS actual_departure,
                %(actual_arrival)s AS actual_arrival,
                %(estimated_departure)s AS estimated_departure,
                %(estimated_arrival)s AS estimated_arrival,
                %(departure_delay)s AS departure_delay,
                %(arrival_delay)s AS arrival_delay,
                %(departure_terminal)s AS departure_terminal,
                %(departure_gate)s AS departure_gate,
                %(arrival_terminal)s AS arrival_terminal,
                %(arrival_gate)s AS arrival_gate,
                %(baggage_belt)s AS baggage_belt,
                %(flight_status)s AS flight_status,
                %(is_delayed)s AS is_delayed,
                %(data_source)s AS data_source
        ) s ON t.flight_iata = s.flight_iata AND t.flight_date = s.flight_date
        WHEN NOT MATCHED THEN
            INSERT (
                flight_iata, flight_icao, flight_number,
                airline_id, departure_airport_id, arrival_airport_id,
                scheduled_departure, scheduled_arrival,
                actual_departure, actual_arrival,
                estimated_departure, estimated_arrival,
                departure_delay, arrival_delay,
                departure_terminal, departure_gate,
                arrival_terminal, arrival_gate, baggage_belt,
                flight_status, is_delayed, flight_date, data_source
            )
            VALUES (
                s.flight_iata, s.flight_icao, s.flight_number,
                s.airline_id, s.departure_airport_id, s.arrival_airport_id,
                s.scheduled_departure, s.scheduled_arrival,
                s.actual_departure, s.actual_arrival,
                s.estimated_departure, s.estimated_arrival,
                s.departure_delay, s.arrival_delay,
                s.departure_terminal, s.departure_gate,
                s.arrival_terminal, s.arrival_gate, s.baggage_belt,
                s.flight_status, s.is_delayed, s.flight_date, s.data_source
            )
        """
        
        self.cursor.execute(insert_sql, flight_data)
    
    def transform_and_load_weather(self, mongo_weather: List[Dict]) -> Tuple[int, int]:
        """Transformer et charger données météo dans Snowflake"""
        logger.info(f"Chargement de {len(mongo_weather)} observations météo...")
        
        inserted = 0
        failed = 0
        
        for weather_doc in mongo_weather:
            try:
                weather_data = self._transform_weather(weather_doc)
                
                if weather_data:
                    self._insert_weather(weather_data)
                    inserted += 1
                    
                    if inserted % 100 == 0:
                        logger.info(f"  Progression: {inserted}/{len(mongo_weather)}")
                        self.conn.commit()
                
            except Exception as e:
                failed += 1
                continue
        
        self.conn.commit()
        logger.info(f"✓ Météo chargée: {inserted} insérées, {failed} échouées")
        
        return inserted, failed
    
    def _transform_weather(self, doc: Dict) -> Optional[Dict]:
        """Transformer données météo"""
        try:
            return {
                'airport_code': doc.get('airport_code'),
                'observation_time': doc.get('observation_time'),
                'temperature': doc.get('temperature'),
                'feels_like': doc.get('feels_like'),
                'humidity': doc.get('humidity'),
                'pressure': doc.get('pressure'),
                'wind_speed': doc.get('wind_speed'),
                'wind_direction': doc.get('wind_direction'),
                'visibility': doc.get('visibility'),
                'cloud_coverage': doc.get('cloud_coverage'),
                'weather_condition': doc.get('weather_condition'),
                'weather_description': doc.get('weather_description'),
                'precipitation': doc.get('precipitation'),
                'snow': doc.get('snow')
            }
        except Exception as e:
            return None
    
    def _insert_weather(self, weather_data: Dict):
        """Insérer données météo"""
        
        insert_sql = """
        MERGE INTO WEATHER_DATA t USING (
            SELECT 
                (SELECT airport_id FROM AIRPORTS WHERE iata_code = %(airport_code)s) AS airport_id,
                %(observation_time)s AS observation_time,
                %(temperature)s AS temperature,
                %(feels_like)s AS feels_like,
                %(humidity)s AS humidity,
                %(pressure)s AS pressure,
                %(wind_speed)s AS wind_speed,
                %(wind_direction)s AS wind_direction,
                %(visibility)s AS visibility,
                %(cloud_coverage)s AS cloud_coverage,
                %(weather_condition)s AS weather_condition,
                %(weather_description)s AS weather_description,
                %(precipitation)s AS precipitation,
                %(snow)s AS snow
        ) s ON t.airport_id = s.airport_id AND t.observation_time = s.observation_time
        WHEN NOT MATCHED THEN
            INSERT (
                airport_id, observation_time, temperature, feels_like, humidity, pressure,
                wind_speed, wind_direction, visibility, cloud_coverage,
                weather_condition, weather_description, precipitation, snow
            )
            VALUES (
                s.airport_id, s.observation_time, s.temperature, s.feels_like, s.humidity, s.pressure,
                s.wind_speed, s.wind_direction, s.visibility, s.cloud_coverage,
                s.weather_condition, s.weather_description, s.precipitation, s.snow
            )
        """
        
        self.cursor.execute(insert_sql, weather_data)
    
    def log_migration(self, etl_type: str, records_processed: int, 
                     records_inserted: int, records_failed: int, 
                     start_time: datetime, status: str):
        """Logger la migration dans MONITORING.ETL_LOGS"""
        try:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            self.cursor.execute("USE SCHEMA MONITORING")
            
            log_sql = """
            INSERT INTO ETL_LOGS (
                etl_type, start_time, end_time, status,
                records_processed, records_inserted, records_failed,
                execution_time_sec
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            self.cursor.execute(log_sql, (
                etl_type, start_time, end_time, status,
                records_processed, records_inserted, records_failed,
                execution_time
            ))
            
            self.conn.commit()
            self.cursor.execute(f"USE SCHEMA {self.schema}")
            
        except Exception as e:
            logger.error(f"❌ Erreur log migration: {e}")
    
    def get_statistics(self):
        """Afficher statistiques Snowflake"""
        logger.info("\n" + "="*60)
        logger.info("STATISTIQUES SNOWFLAKE")
        logger.info("="*60)
        
        try:
            self.cursor.execute("SELECT COUNT(*) FROM FLIGHTS")
            flights_count = self.cursor.fetchone()[0]
            logger.info(f"Vols totaux : {flights_count}")
            
            self.cursor.execute("SELECT COUNT(*) FROM WEATHER_DATA")
            weather_count = self.cursor.fetchone()[0]
            logger.info(f"Observations météo : {weather_count}")
            
            self.cursor.execute("SELECT COUNT(*) FROM AIRPORTS")
            airports_count = self.cursor.fetchone()[0]
            logger.info(f"Aéroports : {airports_count}")
            
            self.cursor.execute("SELECT COUNT(*) FROM AIRLINES")
            airlines_count = self.cursor.fetchone()[0]
            logger.info(f"Compagnies : {airlines_count}")
            
            logger.info("="*60 + "\n")
            
        except Exception as e:
            logger.error(f"❌ Erreur statistiques: {e}")
    
    def close(self):
        """Fermer connexion"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("✓ Snowflake déconnecté")


def main():
    """Fonction principale de migration"""
    
    print("\n" + "="*60)
    print("MIGRATION MONGODB → SNOWFLAKE")
    print("="*60 + "\n")
    
    start_time = datetime.now()
    
    mongo = MongoDBExtractor()
    if not mongo.connect():
        print("❌ Impossible de se connecter à MongoDB")
        return
    
    flights = mongo.extract_flights()
    weather = mongo.extract_weather()
    mongo.close()
    
    if not flights:
        print("⚠ Aucun vol à migrer")
        return
    
    snowflake = SnowflakeLoader()
    if not snowflake.connect():
        print("❌ Impossible de se connecter à Snowflake")
        return
    
    snowflake.ensure_reference_data()
    
    flights_inserted, flights_failed = snowflake.transform_and_load_flights(flights)
    
    snowflake.log_migration(
        'flights_migration', 
        len(flights), 
        flights_inserted, 
        flights_failed,
        start_time,
        'success' if flights_failed == 0 else 'partial'
    )
    
    if weather:
        weather_inserted, weather_failed = snowflake.transform_and_load_weather(weather)
        snowflake.log_migration(
            'weather_migration',
            len(weather),
            weather_inserted,
            weather_failed,
            start_time,
            'success' if weather_failed == 0 else 'partial'
        )
    
    snowflake.get_statistics()
    snowflake.close()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("MIGRATION TERMINÉE !")
    print("="*60)
    print(f"Durée totale: {duration:.2f} secondes")
    print(f"Vols: {flights_inserted} insérés, {flights_failed} échoués")
    if weather:
        print(f"Météo: {weather_inserted} insérées, {weather_failed} échouées")
    print("="*60 + "\n")
    
    logger.info("✓ Migration complétée avec succès")


if __name__ == "__main__":
    main()

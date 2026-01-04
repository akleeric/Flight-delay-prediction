#!/usr/bin/env python3
"""
Synchronisation continue MongoDB → Snowflake (OPTIONNEL)
Script pour synchroniser automatiquement MongoDB → Snowflake
Peut être exécuté en cron quotidien/hebdomadaire
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pymongo import MongoClient
    import snowflake.connector
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Erreur import: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_snowflake.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()


class IncrementalSync:
    """Synchronisation incrémentale MongoDB → Snowflake"""
    
    def __init__(self):
        self.mongo_client = None
        self.mongo_db = None
        self.snow_conn = None
        self.snow_cursor = None
        self.last_sync_time = None
        
    def connect_mongodb(self):
        """Connexion MongoDB"""
        try:
            logger.info("Connexion à MongoDB...")
            mongo_uri = os.getenv('MONGODB_URI')
            db_name = os.getenv('MONGODB_DB_NAME', 'flight_delay_db')
            
            self.mongo_client = MongoClient(mongo_uri)
            self.mongo_db = self.mongo_client[db_name]
            self.mongo_client.server_info()
            
            logger.info(f"✓ MongoDB connecté: {db_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur MongoDB: {e}")
            return False
    
    def connect_snowflake(self):
        """Connexion Snowflake"""
        try:
            logger.info("Connexion à Snowflake...")
            
            self.snow_conn = snowflake.connector.connect(
                account=os.getenv('SNOWFLAKE_ACCOUNT'),
                user=os.getenv('SNOWFLAKE_USER'),
                password=os.getenv('SNOWFLAKE_PASSWORD'),
                warehouse=os.getenv('SNOWFLAKE_WAREHOUSE', 'FLIGHT_WH'),
                database=os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_DELAYS_DB'),
                schema=os.getenv('SNOWFLAKE_SCHEMA', 'RAW_DATA')
            )
            
            self.snow_cursor = self.snow_conn.cursor()
            logger.info("✓ Snowflake connecté")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur Snowflake: {e}")
            return False
    
    def get_last_sync_time(self):
        """Récupérer la date de dernière synchronisation"""
        try:
            self.snow_cursor.execute("""
                SELECT MAX(end_time) 
                FROM MONITORING.ETL_LOGS 
                WHERE etl_type IN ('flights_migration', 'incremental_sync')
                AND status = 'success'
            """)
            
            result = self.snow_cursor.fetchone()
            
            if result and result[0]:
                self.last_sync_time = result[0]
                logger.info(f"Dernière sync: {self.last_sync_time}")
            else:
                self.last_sync_time = datetime.now() - timedelta(days=1)
                logger.info("Première sync - Prendre dernières 24h")
            
            return self.last_sync_time
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération last_sync: {e}")
            self.last_sync_time = datetime.now() - timedelta(days=1)
            return self.last_sync_time
    
    def get_new_flights(self) -> List[Dict]:
        """Récupérer vols depuis dernière sync"""
        try:
            logger.info(f"Récupération vols depuis {self.last_sync_time}...")
            
            all_new_flights = []
            collections = ['aviationstack_flights', 'afklm_flights']
            
            for coll_name in collections:
                if coll_name in self.mongo_db.list_collection_names():
                    collection = self.mongo_db[coll_name]
                    
                    query = {
                        '$or': [
                            {'created_at': {'$gte': self.last_sync_time}},
                            {'last_updated': {'$gte': self.last_sync_time}}
                        ]
                    }
                    
                    flights = list(collection.find(query))
                    all_new_flights.extend(flights)
                    
                    logger.info(f"  {coll_name}: {len(flights)} nouveaux vols")
            
            logger.info(f"Total nouveaux vols: {len(all_new_flights)}")
            return all_new_flights
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération vols: {e}")
            return []
    
    def sync_flights(self, flights: List[Dict]) -> Tuple[int, int]:
        """Synchroniser vols vers Snowflake"""
        if not flights:
            logger.info("Aucun nouveau vol à synchroniser")
            return 0, 0
        
        logger.info(f"Synchronisation de {len(flights)} vols...")
        
        inserted = 0
        failed = 0
        
        for flight_doc in flights:
            try:
                flight_data = self._transform_flight(flight_doc)
                
                if flight_data:
                    self._upsert_flight(flight_data)
                    inserted += 1
                    
                    if inserted % 50 == 0:
                        logger.info(f"  Progression: {inserted}/{len(flights)}")
                        self.snow_conn.commit()
                
            except Exception as e:
                failed += 1
                continue
        
        self.snow_conn.commit()
        logger.info(f"✓ Sync terminée: {inserted} vols, {failed} échoués")
        
        return inserted, failed
    
    def _transform_flight(self, doc: Dict) -> Dict:
        """Transformer vol MongoDB → Snowflake"""
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
    
    def _upsert_flight(self, flight_data: Dict):
        """Insérer ou mettre à jour un vol"""
        
        upsert_sql = """
        MERGE INTO FLIGHTS t
        USING (
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
        ) s
        ON t.flight_iata = s.flight_iata AND t.flight_date = s.flight_date
        WHEN MATCHED THEN
            UPDATE SET
                actual_departure = s.actual_departure,
                actual_arrival = s.actual_arrival,
                departure_delay = s.departure_delay,
                arrival_delay = s.arrival_delay,
                flight_status = s.flight_status,
                is_delayed = s.is_delayed,
                updated_at = CURRENT_TIMESTAMP()
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
        
        self.snow_cursor.execute(upsert_sql, flight_data)
    
    def log_sync(self, records_processed: int, records_inserted: int, 
                 records_failed: int, start_time: datetime):
        """Logger la synchronisation"""
        try:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            self.snow_cursor.execute("USE SCHEMA MONITORING")
            
            log_sql = """
            INSERT INTO ETL_LOGS (
                etl_type, start_time, end_time, status,
                records_processed, records_inserted, records_failed,
                execution_time_sec
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            status = 'success' if records_failed == 0 else 'partial'
            
            self.snow_cursor.execute(log_sql, (
                'incremental_sync', start_time, end_time, status,
                records_processed, records_inserted, records_failed,
                execution_time
            ))
            
            self.snow_conn.commit()
            self.snow_cursor.execute("USE SCHEMA RAW_DATA")
            
        except Exception as e:
            logger.error(f"❌ Erreur log sync: {e}")
    
    def close(self):
        """Fermer connexions"""
        if self.mongo_client:
            self.mongo_client.close()
        if self.snow_cursor:
            self.snow_cursor.close()
        if self.snow_conn:
            self.snow_conn.close()


def main():
    """Fonction principale"""
    
    print("\n" + "="*60)
    print("SYNCHRONISATION INCRÉMENTALE MONGODB → SNOWFLAKE")
    print("="*60 + "\n")
    
    start_time = datetime.now()
    
    sync = IncrementalSync()
    
    if not sync.connect_mongodb():
        return
    
    if not sync.connect_snowflake():
        return
    
    sync.get_last_sync_time()
    new_flights = sync.get_new_flights()
    
    if new_flights:
        inserted, failed = sync.sync_flights(new_flights)
        sync.log_sync(len(new_flights), inserted, failed, start_time)
    else:
        logger.info("✓ Aucune nouvelle donnée à synchroniser")
    
    sync.close()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print(f"SYNC TERMINÉE en {duration:.2f}s")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

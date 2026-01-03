"""MongoDB Client - Compatible avec vos collections existantes"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from config.settings import settings
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseException, DatabaseConnectionError

class MongoDBClient:
    """Client MongoDB adapté à votre structure"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.uri = settings.MONGODB_URI
        self.db_name = settings.MONGODB_DB_NAME
        
        if not self.uri:
            raise DatabaseException("MONGODB_URI not configured")
        
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        try:
            self.logger.info("Connecting to MongoDB...")
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.logger.info(f"Connected to MongoDB: {self.db_name}")
        except PyMongoError as e:
            raise DatabaseConnectionError(f"Failed to connect: {e}")
    
    def insert_aviationstack_flight(self, flight: dict) -> bool:
        """Insère un vol AviationStack (format existant)"""
        try:
            collection = self.db[settings.MONGODB_AVIATIONSTACK_COLLECTION]
            if 'collected_at' not in flight:
                flight['collected_at'] = datetime.utcnow()
            flight_iata = flight.get('flight', {}).get('iata', 'N/A')
            flight_date = flight.get('flight_date', 'N/A')
            flight['_id'] = f"{flight_iata}_{flight_date}"
            collection.update_one({'_id': flight['_id']}, {'$set': flight}, upsert=True)
            return True
        except PyMongoError as e:
            self.logger.error(f"Insert failed: {e}")
            return False
    
    def insert_aviationstack_flights_bulk(self, flights: List[dict]) -> int:
        """Insère plusieurs vols AviationStack"""
        saved = 0
        for flight in flights:
            if self.insert_aviationstack_flight(flight):
                saved += 1
        self.logger.info(f"Bulk inserted {saved} flights")
        return saved
    
    def insert_afklm_flight(self, flight: dict) -> bool:
        """Insère un vol AF-KLM (format existant)"""
        try:
            collection = self.db[settings.MONGODB_AFKLM_COLLECTION]
            if 'collected_at' not in flight:
                flight['collected_at'] = datetime.utcnow()
            flight_id = flight.get('id', f"AFKLM_{flight.get('flightNumber', 'N/A')}")
            flight['_id'] = flight_id
            collection.update_one({'_id': flight['_id']}, {'$set': flight}, upsert=True)
            return True
        except PyMongoError as e:
            self.logger.error(f"Insert failed: {e}")
            return False
    
    def insert_weather_data(self, weather: dict) -> bool:
        """Insère données météo (format existant)"""
        try:
            collection = self.db[settings.MONGODB_WEATHER_COLLECTION]
            if 'collected_at' not in weather:
                weather['collected_at'] = datetime.utcnow()
            city = weather.get('name', 'Unknown')
            timestamp = weather['collected_at'].strftime('%Y%m%d%H')
            weather['_id'] = f"{city}_{timestamp}"
            collection.update_one({'_id': weather['_id']}, {'$set': weather}, upsert=True)
            return True
        except PyMongoError as e:
            self.logger.error(f"Insert failed: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """Stats globales (comme votre check_data.py)"""
        try:
            return {
                'aviationstack': self.db[settings.MONGODB_AVIATIONSTACK_COLLECTION].count_documents({}),
                'afklm': self.db[settings.MONGODB_AFKLM_COLLECTION].count_documents({}),
                'weather': self.db[settings.MONGODB_WEATHER_COLLECTION].count_documents({})
            }
        except PyMongoError as e:
            self.logger.error(f"Stats failed: {e}")
            return {}
    
    def get_aviationstack_flights(self, limit: int = 10) -> List[dict]:
        """Récupère les derniers vols AviationStack"""
        try:
            collection = self.db[settings.MONGODB_AVIATIONSTACK_COLLECTION]
            return list(collection.find().sort('collected_at', DESCENDING).limit(limit))
        except PyMongoError as e:
            self.logger.error(f"Query failed: {e}")
            return []
    
    def close(self):
        if self.client:
            self.client.close()
            self.logger.info("MongoDB closed")

_mongodb_client = None

def get_mongodb_client():
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = MongoDBClient()
    return _mongodb_client

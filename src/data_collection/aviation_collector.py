"""AviationStack Collector avec retry et rate limiting"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from config.settings import settings
from src.data_collection.base_collector import BaseCollector
from src.utils.exceptions import APIException

class AviationStackCollector(BaseCollector):
    def __init__(self):
        super().__init__(api_name="aviationstack", base_url=settings.AVIATIONSTACK_BASE_URL)
        self.api_key = settings.AVIATIONSTACK_API_KEY
        if not self.api_key:
            raise APIException("AVIATIONSTACK_API_KEY not configured")
    
    def _get_default_headers(self) -> Dict[str, str]:
        return {'Accept': 'application/json'}
    
    def collect_flights(self, dep_iata: str = None, limit: int = 100) -> List[dict]:
        """Collecte vols depuis AviationStack"""
        params = {'access_key': self.api_key, 'limit': min(limit, 100)}
        if dep_iata:
            params['dep_iata'] = dep_iata
        
        self.logger.info(f"Collecting flights (limit={limit}, dep={dep_iata})")
        
        try:
            response = self._make_request(endpoint='flights', method='GET', params=params)
            data = response.json()
            
            if 'data' not in data:
                self.logger.warning("No data in response")
                return []
            
            flights = data['data']
            self.logger.info(f"Collected {len(flights)} flights")
            return flights
            
        except APIException as e:
            self.logger.error(f"Collection failed: {e}")
            return []
    
    def collect_from_airports(self, airports: List[str] = None) -> List[dict]:
        """Collecte depuis plusieurs aéroports"""
        if not airports:
            airports = settings.DEFAULT_AIRPORTS
        
        all_flights = []
        for airport in airports:
            flights = self.collect_flights(dep_iata=airport, limit=50)
            all_flights.extend(flights)
            self.logger.info(f"{airport}: {len(flights)} flights")
        
        return all_flights

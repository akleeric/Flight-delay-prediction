"""Air France-KLM Collector"""
from typing import List
from datetime import datetime, timedelta
from config.settings import settings
from src.data_collection.base_collector import BaseCollector
from src.utils.exceptions import APIException

class AirFranceCollector(BaseCollector):
    def __init__(self):
        super().__init__(api_name="airfrance", base_url=settings.AIRFRANCEKLM_BASE_URL)
        self.api_key = settings.AIRFRANCEKLM_API_KEY
        if not self.api_key:
            raise APIException("AIRFRANCEKLM_API_KEY not configured")
    
    def _get_default_headers(self):
        return {
            'API-Key': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
    
    def collect_flights(self, date_offset: int = 1) -> List[dict]:
        target_date = datetime.utcnow() + timedelta(days=date_offset)
        start = target_date.replace(hour=0, minute=0, second=0)
        end = target_date.replace(hour=23, minute=59, second=59)
        
        params = {
            'startRange': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'endRange': end.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        try:
            response = self._make_request(endpoint='', method='GET', params=params)
            data = response.json()
            flights = data.get('flightStatuses', [])
            for flight in flights:
                flight['collected_at'] = datetime.utcnow()
            self.logger.info(f"Collected {len(flights)} AF-KLM flights")
            return flights
        except APIException as e:
            self.logger.error(f"Collection failed: {e}")
            return []

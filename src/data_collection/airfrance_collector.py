"""Air France-KLM Collector - CORRIGÉ"""
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
        """Headers corrigés selon documentation officielle"""
        return {
            'Api-Key': self.api_key,  # ✅ CORRIGÉ: Api-Key (pas API-Key)
            'accept-language': 'en-GB',
            'Accept': 'application/hal+json'
        }
    
    def collect_flights(self, date_offset: int = 0) -> List[dict]:
        """
        Collecte vols AF-KLM
        date_offset=0 pour aujourd'hui (par défaut)
        """
        target_date = datetime.utcnow() + timedelta(days=date_offset)
        start = target_date.replace(hour=0, minute=0, second=0)
        end = target_date.replace(hour=23, minute=59, second=59)
        
        params = {
            'startRange': start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'endRange': end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'movementType': 'D',  # Départs
            'pageSize': 100
        }
        
        try:
            response = self._make_request(endpoint='', method='GET', params=params)
            data = response.json()
            
            # ✅ CORRIGÉ: Cherche les bonnes clés
            flights = data.get('flights', []) or data.get('operationalFlights', [])
            
            for flight in flights:
                flight['collected_at'] = datetime.utcnow()
                flight['source'] = 'airfrance_klm'
            
            if flights:
                self.logger.info(f"✅ Collected {len(flights)} AF-KLM flights")
            else:
                self.logger.warning(f"⚠️ AF-KLM API responded but 0 flights (awaiting activation)")
            
            return flights
            
        except APIException as e:
            self.logger.error(f"❌ AF-KLM collection failed: {e}")
            return []

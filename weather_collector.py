"""Weather Collector"""
from typing import List, Optional
from datetime import datetime
from config.settings import settings
from src.data_collection.base_collector import BaseCollector
from src.utils.exceptions import APIException

class WeatherCollector(BaseCollector):
    def __init__(self):
        super().__init__(api_name="openweather", base_url=settings.OPENWEATHER_BASE_URL)
        self.api_key = settings.OPENWEATHER_API_KEY
        if not self.api_key:
            raise APIException("OPENWEATHER_API_KEY not configured")
    
    def _get_default_headers(self):
        return {'Accept': 'application/json'}
    
    def collect_weather_by_city(self, city: str) -> Optional[dict]:
        params = {'q': city, 'appid': self.api_key, 'units': 'metric'}
        try:
            response = self._make_request(endpoint='weather', method='GET', params=params)
            data = response.json()
            data['collected_at'] = datetime.utcnow()
            self.logger.info(f"{city}: {data.get('main', {}).get('temp')}°C")
            return data
        except APIException as e:
            self.logger.error(f"Failed for {city}: {e}")
            return None
    
    def collect_weather_bulk(self, cities: List[str] = None) -> List[dict]:
        if not cities:
            cities = settings.DEFAULT_CITIES
        weather_data = []
        for city in cities:
            weather = self.collect_weather_by_city(city)
            if weather:
                weather_data.append(weather)
        self.logger.info(f"Collected weather for {len(weather_data)} cities")
        return weather_data

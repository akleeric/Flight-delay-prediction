"""Base Collector avec retry logic et rate limiting"""
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from collections import deque

from config.settings import settings
from src.utils.logger import get_logger
from src.utils.exceptions import APIException, APIRateLimitError, APITimeoutError

class RateLimiter:
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
    
    def __call__(self):
        now = time.time()
        while self.calls and self.calls[0] < now - self.period:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            sleep_time = self.period - (now - self.calls[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
                return self()
        self.calls.append(now)

class BaseCollector(ABC):
    def __init__(self, api_name: str, base_url: str):
        self.api_name = api_name
        self.base_url = base_url
        self.logger = get_logger(f"{__name__}.{api_name}")
        self.rate_limiter = RateLimiter(
            settings.API_RATE_LIMIT_CALLS,
            settings.API_RATE_LIMIT_PERIOD
        )
        self.session = requests.Session()
        self.stats = {'total': 0, 'success': 0, 'failed': 0}
    
    @abstractmethod
    def _get_default_headers(self) -> Dict[str, str]:
        pass
    
    def _make_request(self, endpoint: str, method: str = 'GET', 
                     params: Dict = None, timeout: int = 30):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.rate_limiter()
        
        for attempt in range(settings.MAX_RETRIES):
            try:
                self.logger.debug(f"Request {attempt+1}/{settings.MAX_RETRIES}: {url}")
                response = self.session.request(
                    method=method, url=url, params=params, 
                    headers=self._get_default_headers(), timeout=timeout
                )
                
                if response.status_code == 429:
                    raise APIRateLimitError("Rate limit exceeded")
                elif response.status_code >= 500:
                    raise APIException(f"Server error {response.status_code}")
                elif not response.ok:
                    raise APIException(f"HTTP {response.status_code}")
                
                self.stats['total'] += 1
                self.stats['success'] += 1
                return response
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout (attempt {attempt+1})")
                if attempt < settings.MAX_RETRIES - 1:
                    time.sleep(settings.RETRY_DELAY * (settings.BACKOFF_FACTOR ** attempt))
            except APIException as e:
                self.logger.error(f"API error: {e}")
                if attempt < settings.MAX_RETRIES - 1:
                    time.sleep(settings.RETRY_DELAY * (settings.BACKOFF_FACTOR ** attempt))
        
        self.stats['failed'] += 1
        raise APIException("All retries failed")
    
    def get_stats(self):
        return self.stats
    
    def close(self):
        self.session.close()

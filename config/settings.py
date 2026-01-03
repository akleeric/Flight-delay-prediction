"""Configuration centralisée"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Settings:
    AVIATIONSTACK_API_KEY = os.getenv('AVIATIONSTACK_API_KEY', '')
    AVIATIONSTACK_BASE_URL = "http://api.aviationstack.com/v1"
    AIRFRANCEKLM_API_KEY = os.getenv('AIRFRANCEKLM_API_KEY', '')
    AIRFRANCEKLM_API_SECRET = os.getenv('AIRFRANCEKLM_API_SECRET', '')
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
    OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    MONGODB_DB_NAME = 'flight_delay_db'
    MONGODB_AVIATIONSTACK_COLLECTION = 'aviationstack_flights'
    MONGODB_AFKLM_COLLECTION = 'afklm_flights'
    MONGODB_WEATHER_COLLECTION = 'weather_data'
    MONGODB_LOGS_COLLECTION = 'api_logs'
    SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT', '')
    SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER', '')
    SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD', '')
    SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE', 'FLIGHT_WH')
    SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_DELAYS_DB')
    SNOWFLAKE_SCHEMA_RAW = os.getenv('SNOWFLAKE_SCHEMA', 'RAW_DATA')
    API_RATE_LIMIT_CALLS = 10
    API_RATE_LIMIT_PERIOD = 60
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    BACKOFF_FACTOR = 2.0
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_DIR = Path('logs')
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / 'data'
    DEFAULT_AIRPORTS = ['CDG', 'ORY', 'AMS', 'LHR', 'JFK']
    DEFAULT_CITIES = ['Paris', 'Amsterdam', 'London', 'New York']
    
    @classmethod
    def validate(cls):
        required = {'AVIATIONSTACK_API_KEY': cls.AVIATIONSTACK_API_KEY, 'MONGODB_URI': cls.MONGODB_URI}
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(f"Missing: {', '.join(missing)}")
        return True

settings = Settings()

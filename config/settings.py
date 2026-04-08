import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    MONGO_URI = os.getenv("MONGODB_URI")
    AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

    # Bases Mongo
    DB_HISTORY = "flight_delay_history_db"
    DB_PRODUCTION = "flight_delay_db"

    # URL
    API_URL = os.getenv("API_URL", "http://3.250.9.111:8000")


settings = Settings()

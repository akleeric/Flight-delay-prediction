import requests
from datetime import datetime, timezone
from config.settings import settings
from src.utils.storage import save_raw


class PredictionCollector:
    """
    Collecteur minimal pour récupérer un vol du jour au départ de CDG
    et la météo de Paris, afin de préparer une prédiction.
    """

    def __init__(self):
        self.aviationstack_key = settings.AVIATIONSTACK_API_KEY
        self.weather_key = settings.OPENWEATHER_API_KEY

    def get_one_flight_from_cdg(self):
        """Récupère un vol brut au départ de CDG et sauvegarde le JSON complet."""
        response = requests.get(
            "http://api.aviationstack.com/v1/flights",
            params={
                "access_key": self.aviationstack_key,
                "dep_iata": "CDG",
                "limit": 50
            },
            timeout=15
        )

        flights = response.json()

        # 🔥 Sauvegarde brute
        save_raw("flight_raw", flights)

        data = flights.get("data", [])

        if not data:
            return None

        # 👉 On prend simplement le premier vol (pas de filtre strict)
        return data[0]

    def get_weather_paris(self):
        """Récupère la météo brute de Paris et sauvegarde le JSON complet."""
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={
                "q": "Paris",
                "appid": self.weather_key,
                "units": "metric"
            },
            timeout=10
        )

        weather = response.json()

        # 🔥 Sauvegarde brute
        save_raw("weather_raw", weather)

        return weather

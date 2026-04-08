import requests
from config.settings import settings

def fetch_flight(flight_iata):
    url = (
        f"http://api.aviationstack.com/v1/flights"
        f"?access_key={settings.AVIATIONSTACK_API_KEY}"
        f"&flight_iata={flight_iata}"
    )
    return requests.get(url).json()

def fetch_weather(city):
    url = (
        f"http://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={settings.OPENWEATHER_API_KEY}&units=metric"
    )
    return requests.get(url).json()

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv('MONGODB_URI'))
db = client['flight_delay_db']

print("="*60)
print(" STATISTIQUES DE LA BASE DE DONNÉES")
print("="*60)

print(f"\n  Vols AviationStack: {db['aviationstack_flights'].count_documents({})}")
print(f" Vols Air France-KLM: {db['afklm_flights'].count_documents({})}")
print(f" Données météo: {db['weather_data'].count_documents({})}")

print("\n Derniers vols AviationStack:")
for flight in db['aviationstack_flights'].find().sort('collected_at', -1).limit(3):
    flight_info = flight.get('flight', {})
    print(f"  - {flight_info.get('iata', 'N/A')}: {flight.get('flight_status', 'N/A')}")

print("\n Derniers vols Air France-KLM:")
for flight in db['afklm_flights'].find().sort('collected_at', -1).limit(3):
    print(f"  - Vol {flight.get('flightNumber', 'N/A')}: {flight.get('flightScheduleDate', 'N/A')}")

print("\n Dernières données météo:")
for weather in db['weather_data'].find().sort('collected_at', -1).limit(3):
    print(f"  - {weather.get('name', 'N/A')}: {weather.get('main', {}).get('temp', 'N/A')}°C")

client.close()

print("\n" + "="*60)

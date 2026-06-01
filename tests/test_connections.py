#!/usr/bin/env python3
"""
Script de test des connexions APIs et Databases
"""

import os
from dotenv import load_dotenv
import requests
from pymongo import MongoClient
import psycopg2

# Charger variables d'environnement
load_dotenv()

print("="*60)
print("TEST DES CONNEXIONS - Services Cloud & APIs")
print("="*60)

# ============================================
# TEST 1 : AviationStack API
# ============================================
print("\n1. Test AviationStack API...")
try:
    api_key = os.getenv('AVIATIONSTACK_API_KEY')
    if not api_key:
        print("AVIATIONSTACK_API_KEY non trouvée dans .env")
    else:
        url = "http://api.aviationstack.com/v1/flights"
        params = {'access_key': api_key, 'limit': 1}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                flight = data['data'][0]
                print(f"OK - Vol récupéré: {flight.get('flight', {}).get('iata', 'N/A')}")
            else:
                print(f"Réponse vide (normal si pas de vols actuellement)")
        else:
            print(f"Erreur HTTP {response.status_code}")
except Exception as e:
    print(f"Erreur: {e}")

# ============================================
# TEST 2 : Lufthansa API
# ============================================
"""
print("\n2. Test Lufthansa API (OAuth)...")
try:
    client_id = os.getenv('LUFTHANSA_CLIENT_ID')
    client_secret = os.getenv('LUFTHANSA_SECRET')

    if not client_id or not client_secret:
        print(" Credentials Lufthansa non trouvées")
    else:
        # Obtenir token
        url = "https://api.lufthansa.com/v1/oauth/token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, data=data, timeout=10)

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('access_token')
            if token:
                print(f"OK - Token obtenu (expire dans {token_data.get('expires_in')}s)")
            else:
                print("Token non reçu")
        else:
            print(f"Erreur HTTP {response.status_code}")
except Exception as e:
    print(f" Erreur: {e}")
"""

# ============================================
# TEST 3 : Air France-KLM API
# ============================================
print("\n3. Test Air France-KLM API...")
try:
    url = "https://api.airfranceklm.com/opendata/flightstatus"
    # Paramètres exactement comme dans le curl qui fonctionne
    params = {
        'startRange': '2025-12-31T09:00:00Z',
        'endRange': '2025-12-31T23:59:59Z'
    }
    headers = {
        'API-Key': os.getenv('AIRFRANCEKLM_API_KEY'),
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    # Timeout augmenté à 30 secondes
    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code == 200:
        data = response.json()
        flights = data.get('flightStatuses', [])
        print(f" OK - {len(flights)} vols AF/KLM récupérés")
    else:
        print(f"  Code {response.status_code}")
        print(f"  Response: {response.text[:150]}")
except requests.exceptions.Timeout:
    print(f" Timeout - L'API met trop de temps à répondre")
    print(f" L'API fonctionne (curl OK) mais est lente")
except Exception as e:
    print(f"  Erreur: {e}")

# ============================================
# TEST 4 : OpenWeatherMap API
# ============================================
print("\n4. Test OpenWeatherMap API...")
try:
    api_key = os.getenv('OPENWEATHER_API_KEY')
    if not api_key:
        print("OPENWEATHER_API_KEY non trouvée")
    else:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {'q': 'Paris', 'appid': api_key, 'units': 'metric'}
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            temp = data.get('main', {}).get('temp', 'N/A')
            print(f" OK - Température Paris: {temp}°C")
        elif response.status_code == 401:
            print(" Clé invalide ou pas encore active (attendre 10min-2h)")
        else:
            print(f" Erreur HTTP {response.status_code}")
except Exception as e:
    print(f"  Erreur: {e}")

# ============================================
# TEST 5 : MongoDB Atlas
# ============================================
print("\n5. Test MongoDB Atlas...")
try:
    uri = os.getenv('MONGODB_URI')
    if not uri:
        print(" MONGODB_URI non trouvée")
    else:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Ping pour tester connexion
        client.admin.command('ping')
        print("OK - Connexion MongoDB réussie")

        # Tester création database/collection
        db = client['flight_delays_test']
        collection = db['test_collection']
        collection.insert_one({'test': 'data', 'timestamp': 'now'})
        print("OK - Test écriture réussi")

        client.close()
except Exception as e:
    print(f"Erreur: {e}")

# ============================================
# TEST 6 : Supabase (PostgreSQL)
# ============================================
print("\n6. Test Supabase PostgreSQL...")
try:
    db_url = os.getenv('SUPABASE_DB_URL')
    if not db_url:
        print("SUPABASE_DB_URL non trouvée")
    else:
        # Forcer IPv4 uniquement (contourner le problème IPv6)
        import socket
        original_getaddrinfo = socket.getaddrinfo

        def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        socket.getaddrinfo = ipv4_only

        try:
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f" OK - PostgreSQL version: {version[:30]}...")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f" Erreur avec IPv4 forcé: {e}")
        finally:
            socket.getaddrinfo = original_getaddrinfo
except Exception as e:
    print(f"Erreur: {e}")



# ============================================
# TEST 7 : Snowflake
# ============================================
print("\n7. Test Snowflake...")
try:
    import snowflake.connector

    account = os.getenv('SNOWFLAKE_ACCOUNT')
    user = os.getenv('SNOWFLAKE_USER')
    password = os.getenv('SNOWFLAKE_PASSWORD')

    if not all([account, user, password]):
        print(" Credentials Snowflake incomplets")
    else:
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        print(f" OK - Snowflake version: {version}")
        cursor.close()
        conn.close()
except Exception as e:
    print(f" Erreur: {e}")

print("\n" + "="*60)
print("TESTS TERMINÉS")
print("="*60)

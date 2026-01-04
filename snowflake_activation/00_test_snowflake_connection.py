#!/usr/bin/env python3
"""
Test de connexion Snowflake
Vérifie que tout est prêt pour la migration
"""

import os
import sys
from dotenv import load_dotenv

try:
    import snowflake.connector
    from snowflake.connector.errors import DatabaseError
except ImportError:
    print("Erreur: snowflake-connector-python non installé")
    print("\nInstallez avec:")
    print("pip install snowflake-connector-python")
    sys.exit(1)

load_dotenv()

def test_connection():
    print("\n" + "="*60)
    print("TEST CONNEXION SNOWFLAKE")
    print("="*60 + "\n")

    account = os.getenv('SNOWFLAKE_ACCOUNT')
    user = os.getenv('SNOWFLAKE_USER')
    password = os.getenv('SNOWFLAKE_PASSWORD')
    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', 'FLIGHT_WH')
    database = os.getenv('SNOWFLAKE_DATABASE', 'FLIGHT_DELAYS_DB')

    if not all([account, user, password]):
        print(" Credentials Snowflake manquantes dans .env")
        print("\nVérifiez dans .env :")
        print("SNOWFLAKE_ACCOUNT=...")
        print("SNOWFLAKE_USER=...")
        print("SNOWFLAKE_PASSWORD=...")
        return False

    print(f"Account: {account}")
    print(f"User: {user}")
    print(f"Warehouse: {warehouse}")
    print(f"Database: {database}\n")

    try:
        print("1. Test connexion...", end=" ")
        conn = snowflake.connector.connect(
            account=account,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        print("✓")

        print("2. Vérification version...", end=" ")
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]
        print(f"✓ (v{version})")

        print("3. Test warehouse...", end=" ")
        cursor.execute(f"USE WAREHOUSE {warehouse}")
        print("✓")

        print("4. Test database...", end=" ")
        cursor.execute(f"USE DATABASE {database}")
        print("✓")

        print("5. Vérification schemas...")
        cursor.execute("SHOW SCHEMAS")
        schemas = [row[1] for row in cursor.fetchall()]

        expected_schemas = ['RAW_DATA', 'PROCESSED_DATA', 'MONITORING']
        for schema in expected_schemas:
            if schema in schemas:
                print(f"    {schema}")
            else:
                print(f"    {schema} manquant (exécuter 01_snowflake_setup.sql)")

        print("6. Vérification tables RAW_DATA...")
        cursor.execute("USE SCHEMA RAW_DATA")
        cursor.execute("SHOW TABLES")
        tables = [row[1] for row in cursor.fetchall()]

        expected_tables = ['AIRPORTS', 'AIRLINES', 'AIRCRAFT', 'ROUTES', 'FLIGHTS', 'WEATHER_DATA']

        for table in expected_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"    {table} ({count} lignes)")
            else:
                print(f"    {table} manquante")

        cursor.close()
        conn.close()

        print("\n" + "="*60)
        print("✓ SNOWFLAKE PRÊT")
        print("="*60 + "\n")
        return True

    except DatabaseError as e:
        if 'trial account expired' in str(e).lower():
            print("\n PÉRIODE D'ESSAI SNOWFLAKE EXPIRÉE")
            print("\n Pour réactiver:")
            print("1. Créer nouveau compte: https://signup.snowflake.com/")
            print("2. Mettre à jour credentials dans .env")
        else:
            print(f"\n Erreur Snowflake: {e}")
        return False

    except Exception as e:
        print(f"\n  Erreur: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

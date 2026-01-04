"""Snowflake Client - Avec gestion période expirée"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import snowflake.connector
from snowflake.connector.errors import DatabaseError, ProgrammingError

from config.settings import settings
from src.utils.logger import get_logger
from src.utils.exceptions import DatabaseException, DatabaseConnectionError

class SnowflakeClient:
    """Client Snowflake - Graceful fallback si indisponible"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.account = settings.SNOWFLAKE_ACCOUNT
        self.user = settings.SNOWFLAKE_USER
        self.password = settings.SNOWFLAKE_PASSWORD
        self.warehouse = settings.SNOWFLAKE_WAREHOUSE
        self.database = settings.SNOWFLAKE_DATABASE
        self.schema = settings.SNOWFLAKE_SCHEMA_RAW

        self.conn = None
        self.is_available = False

        # Tentative de connexion (non bloquante)
        try:
            self._connect()
        except Exception as e:
            self.logger.warning(f"Snowflake not available: {e}")
            self.logger.info("Continuing with MongoDB only")

    def _connect(self):
        """Connexion à Snowflake"""
        if not all([self.account, self.user, self.password]):
            raise DatabaseException("Snowflake credentials missing in .env")

        try:
            self.logger.info("Attempting Snowflake connection...")
            self.conn = snowflake.connector.connect(
                account=self.account,
                user=self.user,
                password=self.password,
                warehouse=self.warehouse,
                database=self.database,
                schema=self.schema,
                login_timeout=10
            )
            self.is_available = True
            self.logger.info(f"Connected to Snowflake: {self.database}")

        except DatabaseError as e:
            error_msg = str(e).lower()
            if 'trial' in error_msg or 'expired' in error_msg or 'suspended' in error_msg:
                self.logger.warning("Snowflake trial period expired")
                self.logger.info("To renew: Create new account at https://signup.snowflake.com/")
            elif 'incorrect' in error_msg or 'authentication' in error_msg:
                self.logger.error("Snowflake authentication failed - check credentials")
            else:
                self.logger.error(f"Snowflake connection error: {e}")

            self.is_available = False
            raise DatabaseConnectionError(f"Snowflake unavailable: {e}")

    def insert_flight(self, flight_data: dict) -> bool:
        """Insère un vol dans Snowflake (si disponible)"""
        if not self.is_available:
            return False

        try:
            cursor = self.conn.cursor()

            # Créer la table si elle n'existe pas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS RAW_DATA.FLIGHTS (
                    flight_iata VARCHAR(10),
                    flight_date DATE,
                    airline_iata VARCHAR(5),
                    departure_airport VARCHAR(5),
                    arrival_airport VARCHAR(5),
                    flight_status VARCHAR(20),
                    collected_at TIMESTAMP,
                    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
                )
            """)

            # Insérer le vol
            query = """
                INSERT INTO RAW_DATA.FLIGHTS (
                    flight_iata, flight_date, airline_iata,
                    departure_airport, arrival_airport,
                    flight_status, collected_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                flight_data.get('flight', {}).get('iata'),
                flight_data.get('flight_date'),
                flight_data.get('airline', {}).get('iata'),
                flight_data.get('departure', {}).get('iata'),
                flight_data.get('arrival', {}).get('iata'),
                flight_data.get('flight_status'),
                datetime.utcnow()
            )

            cursor.execute(query, values)
            self.conn.commit()
            cursor.close()
            return True

        except Exception as e:
            self.logger.error(f"Snowflake insert failed: {e}")
            return False

    def count_flights(self) -> int:
        """Compte les vols dans Snowflake"""
        if not self.is_available:
            return 0

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM RAW_DATA.FLIGHTS")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else 0
        except:
            return 0

    def is_connected(self) -> bool:
        """Vérifie si Snowflake est disponible"""
        return self.is_available

    def close(self):
        """Ferme la connexion"""
        if self.conn:
            try:
                self.conn.close()
                self.logger.info("Snowflake connection closed")
            except:
                pass

_snowflake_client = None

def get_snowflake_client():
    """Retourne instance Snowflake (peut être None si indisponible)"""
    global _snowflake_client
    if _snowflake_client is None:
        try:
            _snowflake_client = SnowflakeClient()
        except:
            return None
    return _snowflake_client

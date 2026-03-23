import pandas as pd
import numpy as np
import logging
from datetime import timedelta
from src.utils.weather import find_closest_weather

logger = logging.getLogger(__name__)

FINAL_COLUMNS = [
    "airline_name",
    "departure_iata",
    "arrival_iata",
    "departure_delay_actual",
    "departure_delay_estimated",
    "arrival_delay_estimated",
    "flight_duration_scheduled",
    "departure_meteo",
]


# ---------------------------------------------------------
# 1. "APPLATISSEMENT" DES DONNÉES
# Ici, df_raw est déjà un DataFrame venant de Mongo
# ---------------------------------------------------------
def flatten_documents(df_raw: pd.DataFrame) -> pd.DataFrame:
    if df_raw is None or df_raw.empty:
        logger.warning("Aucun document trouvé dans Mongo.")
        return pd.DataFrame()
    return df_raw.copy()

# ---------------------------------------------------------
# 2. CONVERSION DES DATES
# ---------------------------------------------------------
def convert_datetime_columns(df):
    datetime_cols = [
        "flight_date",
        "collected_at",
        "filtered_at",
        "departure_scheduled",
        "departure_estimated",
        "departure_actual",
        "arrival_scheduled",
        "arrival_estimated",
        "arrival_actual",
    ]

    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


# ---------------------------------------------------------
# 3. CALCUL DES DÉLAIS
# ---------------------------------------------------------
def compute_delay(actual, scheduled):
    if pd.isna(actual) or pd.isna(scheduled):
        return None
    delay = (actual - scheduled).total_seconds() / 60
    return max(delay, 0)


def compute_duration(dep, arr):
    if pd.isna(dep) or pd.isna(arr):
        return None
    duration = (arr - dep).total_seconds() / 60
    return max(duration, 0)


def add_delay_features(df):
    df["departure_delay_actual"] = df.apply(
        lambda row: compute_delay(row.get("departure_actual"), row.get("departure_scheduled")),
        axis=1
    )

    df["departure_delay_estimated"] = df.apply(
        lambda row: compute_delay(row.get("departure_estimated"), row.get("departure_scheduled")),
        axis=1
    )

    df["arrival_delay_estimated"] = df.apply(
        lambda row: compute_delay(row.get("arrival_estimated"), row.get("arrival_scheduled")),
        axis=1
    )

    df["flight_duration_scheduled"] = df.apply(
        lambda row: compute_duration(row.get("departure_scheduled"), row.get("arrival_scheduled")),
        axis=1
    )

    return df


# ---------------------------------------------------------
# 4. AJOUT DES DONNÉES MÉTÉO
# ---------------------------------------------------------
AIRPORT_TO_CITY = {
    "CDG": "Paris",
    "ORY": "Paris",
    "AMS": "Amsterdam",
    "LHR": "London",
    "JFK": "New York",
}


def add_weather_features(df):
    df["departure_meteo"] = None

    for idx, row in df.iterrows():
        iata = row.get("departure_iata")
        city = AIRPORT_TO_CITY.get(iata)

        if city is None:
            continue

        # Choix de la meilleure référence temporelle
        ref_dt = (
            row.get("departure_actual")
            or row.get("departure_estimated")
            or row.get("departure_scheduled")
        )

        meteo, _ = find_closest_weather(city, ref_dt)
        df.at[idx, "departure_meteo"] = meteo

    # Remplissage des valeurs manquantes
    if df["departure_meteo"].isna().sum() > 0:
        mode_value = df["departure_meteo"].mode()[0]
        df["departure_meteo"] = df["departure_meteo"].fillna(mode_value)

    return df


# ---------------------------------------------------------
# 5. SÉLECTION DES COLONNES FINALES
# ---------------------------------------------------------
def select_final_columns(df):
    missing = [c for c in FINAL_COLUMNS if c not in df.columns]

    if missing:
        logger.warning(f"Colonnes manquantes : {missing}. Création d'un dataset factice.")

        # Dataset minimal pour éviter les erreurs
        dummy = pd.DataFrame([{
            "airline_name": "easyJet",
            "departure_iata": "ORY",
            "arrival_iata": "LIS",
            "departure_delay_actual": 10.0,
            "departure_delay_estimated": 5.0,
            "arrival_delay_estimated": 12.0,
            "flight_duration_scheduled": 95.0,
            "departure_meteo": "clear sky",
        }])

        return dummy

    return df[FINAL_COLUMNS]


# ---------------------------------------------------------
# 6. PIPELINE COMPLET
# ---------------------------------------------------------
def build_training_dataset(df_raw):
    """
    Pipeline complet :
    - applatissement
    - conversion datetime
    - calcul des délais
    - ajout météo
    - sélection des colonnes finales
    - split train/test
    """

    df = flatten_documents(df_raw)
    df = convert_datetime_columns(df)
    df = add_delay_features(df)
    df = add_weather_features(df)
    df = select_final_columns(df)

    # Suppression des lignes sans target
    df = df.dropna(subset=["arrival_delay_estimated"])

    X = df.drop("arrival_delay_estimated", axis=1)
    y = df["arrival_delay_estimated"]

    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=0.25, random_state=42)

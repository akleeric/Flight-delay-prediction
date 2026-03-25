import pandas as pd
import logging
from src.utils.weather import find_closest_weather

logger = logging.getLogger(__name__)

# Colonnes utilisées comme FEATURES (celles que l’API fournira)
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


def flatten_documents(docs):
    if isinstance(docs, pd.DataFrame):
        return docs.copy()
    if isinstance(docs, list) and all(isinstance(x, dict) for x in docs):
        return pd.json_normalize(docs, sep="_")
    raise TypeError("docs doit être DataFrame ou liste de dicts")


def convert_datetime_columns(df):
    datetime_cols = [
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


def compute_delay(actual, scheduled):
    if pd.isna(actual) or pd.isna(scheduled):
        return None
    return max((actual - scheduled).total_seconds() / 60, 0)


def compute_duration(dep, arr):
    if pd.isna(dep) or pd.isna(arr):
        return None
    return max((arr - dep).total_seconds() / 60, 0)


def add_delay_features(df):
    df["departure_delay_actual"] = df.apply(
        lambda r: compute_delay(r.get("departure_actual"), r.get("departure_scheduled")),
        axis=1
    )
    df["departure_delay_estimated"] = df.apply(
        lambda r: compute_delay(r.get("departure_estimated"), r.get("departure_scheduled")),
        axis=1
    )
    df["arrival_delay_actual"] = df.apply(
        lambda r: compute_delay(r.get("arrival_actual"), r.get("arrival_scheduled")),
        axis=1
    )
    df["arrival_delay_estimated"] = df.apply(
        lambda r: compute_delay(r.get("arrival_estimated"), r.get("arrival_scheduled")),
        axis=1
    )
    df["flight_duration_scheduled"] = df.apply(
        lambda r: compute_duration(r.get("departure_scheduled"), r.get("arrival_scheduled")),
        axis=1
    )
    return df


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
        city = AIRPORT_TO_CITY.get(row.get("departure_iata"))
        if city is None:
            continue
        ref_dt = (
            row.get("departure_actual")
            or row.get("departure_estimated")
            or row.get("departure_scheduled")
        )
        meteo, _ = find_closest_weather(city, ref_dt)
        df.at[idx, "departure_meteo"] = meteo

    df["departure_meteo"] = df["departure_meteo"].fillna(df["departure_meteo"].mode()[0])
    return df


def select_final_columns(df):
    return df[FINAL_COLUMNS]


def build_training_dataset(docs):
    df = flatten_documents(docs)
    df = convert_datetime_columns(df)
    df = add_delay_features(df)
    df = add_weather_features(df)

    # On garde la target pour le training
    df = df.dropna(subset=["arrival_delay_actual"])

    X = select_final_columns(df)
    y = df["arrival_delay_actual"]

    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=0.25, random_state=42)

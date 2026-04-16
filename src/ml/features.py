import pandas as pd
import logging
from src.utils.weather import find_closest_weather
from src.utils.iata import IATA_TO_CITY   # <-- une seule source IATA

logger = logging.getLogger(__name__)

# Colonnes finales utilisées pour le modèle ML
FINAL_COLUMNS = [
    "airline_name",
    "departure_iata",
    "arrival_iata",

    # Features temporelles
    "scheduled_hour",
    "day_of_week",
    "month",
    "is_weekend",

    # Retards & durée
    "departure_delay_actual",
    "departure_delay_estimated",
    "arrival_delay_estimated",
    "flight_duration_scheduled",

    # Météo départ
    "dep_temperature",
    "dep_wind_speed",
    "dep_visibility",
    "dep_precipitation",
    "dep_weather_bad",

    # Météo arrivée
    "arr_temperature",
    "arr_wind_speed",
    "arr_visibility",
    "arr_precipitation",
    "arr_weather_bad",
]


# ---------------------------------------------------------
# 1. Flatten
# ---------------------------------------------------------
def flatten_documents(docs):
    if isinstance(docs, pd.DataFrame):
        return docs.copy()
    if isinstance(docs, list) and all(isinstance(x, dict) for x in docs):
        return pd.json_normalize(docs, sep="_")
    raise TypeError("docs doit être DataFrame ou liste de dicts")


# ---------------------------------------------------------
# 2. Convertir les colonnes datetime
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 3. Calcul des retards et durées
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# 4. Features temporelles
# ---------------------------------------------------------
def add_time_features(df):
    df["scheduled_hour"] = df["departure_scheduled"].dt.hour
    df["day_of_week"] = df["departure_scheduled"].dt.weekday + 1
    df["month"] = df["departure_scheduled"].dt.month
    df["is_weekend"] = df["day_of_week"].isin([6, 7]).astype(int)
    return df


# ---------------------------------------------------------
# 5. Météo départ + arrivée
# ---------------------------------------------------------
def extract_weather_fields(weather):
    """
    Gère 3 formats :
    - dict OpenWeather standard
    - dict custom (Unknown_…)
    - string ("clear sky")
    Utilise weather.main au lieu de description.
    """

    # Cas 1 : aucune donnée
    if weather is None:
        return {
            "temperature": None,
            "wind_speed": None,
            "visibility": None,
            "precipitation": None,
            "weather_bad": None,
        }

    # Cas 2 : ancien format texte ("clear sky")
    if isinstance(weather, str):
        main = weather.lower()
        bad = int(any(k in main for k in ["rain", "snow", "thunderstorm", "fog"]))
        return {
            "temperature": None,
            "wind_speed": None,
            "visibility": None,
            "precipitation": None,
            "weather_bad": bad,
        }

    # Cas 3 : format custom avec raw_data
    if isinstance(weather, dict) and "raw_data" in weather:
        raw = weather["raw_data"]
        main = raw.get("weather", [{}])[0].get("main", "").lower()
        bad = int(any(k in main for k in ["rain", "snow", "thunderstorm", "fog"]))

        return {
            "temperature": raw.get("main", {}).get("temp"),
            "wind_speed": raw.get("wind", {}).get("speed"),
            "visibility": raw.get("visibility"),
            "precipitation": raw.get("rain", {}).get("1h", 0) if isinstance(raw.get("rain"), dict) else 0,
            "weather_bad": bad,
        }

    # Cas 4 : format OpenWeather standard
    if isinstance(weather, dict):
        main_section = weather.get("main", {})
        wind = weather.get("wind", {})
        visibility = weather.get("visibility")
        main = weather.get("weather", [{}])[0].get("main", "").lower()

        bad = int(any(k in main for k in ["rain", "snow", "thunderstorm", "fog"]))

        return {
            "temperature": main_section.get("temp"),
            "wind_speed": wind.get("speed"),
            "visibility": visibility,
            "precipitation": weather.get("rain", {}).get("1h", 0) if isinstance(weather.get("rain"), dict) else 0,
            "weather_bad": bad,
        }

    # Cas inconnu
    return {
        "temperature": None,
        "wind_speed": None,
        "visibility": None,
        "precipitation": None,
        "weather_bad": None,
    }



def add_weather_features(df):
    # Initialisation
    df["dep_temperature"] = None
    df["dep_wind_speed"] = None
    df["dep_visibility"] = None
    df["dep_precipitation"] = None
    df["dep_weather_bad"] = None

    df["arr_temperature"] = None
    df["arr_wind_speed"] = None
    df["arr_visibility"] = None
    df["arr_precipitation"] = None
    df["arr_weather_bad"] = None

    for idx, row in df.iterrows():

        # -----------------------------
        # Météo départ
        # -----------------------------
        dep_city = IATA_TO_CITY.get(row.get("departure_iata"))
        dep_dt = (
            row.get("departure_actual")
            or row.get("departure_estimated")
            or row.get("departure_scheduled")
        )

        dep_weather, _ = find_closest_weather(dep_city, dep_dt)
        dep_fields = extract_weather_fields(dep_weather)

        df.at[idx, "dep_temperature"] = dep_fields["temperature"]
        df.at[idx, "dep_wind_speed"] = dep_fields["wind_speed"]
        df.at[idx, "dep_visibility"] = dep_fields["visibility"]
        df.at[idx, "dep_precipitation"] = dep_fields["precipitation"]
        df.at[idx, "dep_weather_bad"] = dep_fields["weather_bad"]

        # -----------------------------
        # Météo arrivée
        # -----------------------------
        arr_city = IATA_TO_CITY.get(row.get("arrival_iata"))
        arr_dt = (
            row.get("arrival_actual")
            or row.get("arrival_estimated")
            or row.get("arrival_scheduled")
        )

        arr_weather, _ = find_closest_weather(arr_city, arr_dt)
        arr_fields = extract_weather_fields(arr_weather)

        df.at[idx, "arr_temperature"] = arr_fields["temperature"]
        df.at[idx, "arr_wind_speed"] = arr_fields["wind_speed"]
        df.at[idx, "arr_visibility"] = arr_fields["visibility"]
        df.at[idx, "arr_precipitation"] = arr_fields["precipitation"]
        df.at[idx, "arr_weather_bad"] = arr_fields["weather_bad"]

    return df


# ---------------------------------------------------------
# 6. Sélection des colonnes finales
# ---------------------------------------------------------
def select_final_columns(df):
    return df[FINAL_COLUMNS]


# ---------------------------------------------------------
# 7. Pipeline complet
# ---------------------------------------------------------
def build_training_dataset(docs):
    df = flatten_documents(docs)
    df = convert_datetime_columns(df)
    df = add_delay_features(df)
    df = add_time_features(df)
    df = add_weather_features(df)

    # On garde la target pour le training
    df = df.dropna(subset=["arrival_delay_actual"])

    X = select_final_columns(df)
    y = df["arrival_delay_actual"]

    from sklearn.model_selection import train_test_split
    return train_test_split(X, y, test_size=0.25, random_state=42)

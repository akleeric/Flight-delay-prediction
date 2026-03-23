#Ml pas à pas 2

# ============================================
# IMPORTS
# ============================================
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score

# ============================================
# ETAPE 0 : CONNEXION MONGO & RECUPERATION DES DONNEES
# ============================================
load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["flight_delay_history_db"]
collection = db["aviationstack_historical_landed_flights"]

query = {
    "flight_status": "landed",
    "arrival.actual": {"$nin": [None, ""]},
    "arrival.scheduled": {"$nin": [None, ""]},
    "departure.scheduled": {"$nin": [None, ""]},
    "departure.actual": {"$nin": [None, ""]},
}

docs = list(collection.find(query))
#print(f"Nombre de vols récupérés : {len(docs)}")

# ============================================
# ETAPE 1 : APPLATISSEMENT
# ============================================
df_flat = pd.json_normalize(docs, sep="_")

cols_to_keep = [
    "_id",
    "flight_date",
    "flight_status",
    "collected_at",
    "filtered_at",
    "live",

    "airline_name",
    "airline_iata",
    "airline_icao",

    "aircraft_registration",
    "aircraft_iata",
    "aircraft_icao",
    "aircraft_icao24",

    "departure_airport",
    "departure_timezone",
    "departure_iata",
    "departure_icao",
    "departure_terminal",
    "departure_gate",
    "departure_scheduled",
    "departure_estimated",
    "departure_actual",
    "departure_estimated_runway",
    "departure_actual_runway",

    "arrival_airport",
    "arrival_timezone",
    "arrival_iata",
    "arrival_icao",
    "arrival_terminal",
    "arrival_gate",
    "arrival_baggage",
    "arrival_scheduled",
    "arrival_estimated",
    "arrival_actual",
    "arrival_estimated_runway",
    "arrival_actual_runway",

    "flight_number",
    "flight_iata",
    "flight_icao",
    "flight_codeshared",
]

existing_cols = [c for c in cols_to_keep if c in df_flat.columns]
df_flat = df_flat[existing_cols]

datetime_cols = [
    "flight_date",
    "collected_at",
    "filtered_at",
    "departure_scheduled",
    "departure_estimated",
    "departure_actual",
    "departure_estimated_runway",
    "departure_actual_runway",
    "arrival_scheduled",
    "arrival_estimated",
    "arrival_actual",
    "arrival_estimated_runway",
    "arrival_actual_runway",
]

for col in datetime_cols:
    if col in df_flat.columns:
        df_flat[col] = pd.to_datetime(df_flat[col], errors="coerce")

# ============================================
# ETAPE 2 : ANALYSE & NETTOYAGE DES COLONNES
# ============================================
null_counts = df_flat.isnull().sum()
null_percent = (null_counts / len(df_flat)) * 100

null_summary = (
    pd.DataFrame({
        "null_count": null_counts,
        "null_percent": null_percent.round(2)
    })
    .query("null_percent > 0")
    .sort_values(by="null_percent", ascending=False)
)

#print("Résumé des colonnes avec valeurs nulles :")
#print(null_summary.head(20))

cols_to_drop = null_summary[null_summary["null_percent"] > 30.0].index.tolist()
df_flat_filtered = df_flat.drop(columns=cols_to_drop)

cols_runway = [col for col in df_flat_filtered.columns if "runway" in col.lower()]
df_flat_filtered = df_flat_filtered.drop(columns=cols_runway)

#print("Colonnes supprimées (>30% nulls) :", cols_to_drop)
#print("Colonnes runway supprimées :", cols_runway)

# ============================================
# ETAPE 3 : TRAITEMENT DE QUELQUES NULLS SIMPLES
# ============================================
if "departure_terminal" in df_flat_filtered.columns:
    mode_value = df_flat_filtered["departure_terminal"].mode()[0]
    df_flat_filtered["departure_terminal"] = df_flat_filtered["departure_terminal"].fillna(mode_value)

# ============================================
# ETAPE 4 : CALCUL DES DELAIS
# ============================================
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

df_flat_filtered["departure_delay_actual"] = df_flat_filtered.apply(
    lambda row: compute_delay(row.get("departure_actual"), row.get("departure_scheduled")),
    axis=1
)

df_flat_filtered["departure_delay_estimated"] = df_flat_filtered.apply(
    lambda row: compute_delay(row.get("departure_estimated"), row.get("departure_scheduled")),
    axis=1
)

df_flat_filtered["arrival_delay_actual"] = df_flat_filtered.apply(
    lambda row: compute_delay(row.get("arrival_actual"), row.get("arrival_scheduled")),
    axis=1
)

df_flat_filtered["arrival_delay_estimated"] = df_flat_filtered.apply(
    lambda row: compute_delay(row.get("arrival_estimated"), row.get("arrival_scheduled")),
    axis=1
)

df_flat_filtered["flight_duration_scheduled"] = df_flat_filtered.apply(
    lambda row: compute_duration(row.get("departure_scheduled"), row.get("arrival_scheduled")),
    axis=1
)

#print(df_flat_filtered[["departure_delay_actual", "departure_delay_estimated", "arrival_delay_actual", "arrival_delay_estimated", "flight_duration_scheduled"]].head())

# ============================================
# ETAPE 5 : AJOUT DES DONNEES METEO
# ============================================
for col in ["departure_actual", "departure_estimated", "departure_scheduled"]:
    if col in df_flat_filtered.columns:
        df_flat_filtered[col] = pd.to_datetime(df_flat_filtered[col], errors="coerce", utc=True)

airport_to_city = {
    "CDG": "Paris",
    "ORY": "Paris",
    "AMS": "Amsterdam",
    "LHR": "London",
    "JFK": "New York"
}

db_weather = client["flight_delay_db"]
weather_col = db_weather["weather_data"]

def find_closest_weather(city, target_dt):
    if pd.isna(target_dt):
        return None, None

    start = target_dt - pd.Timedelta(hours=6)
    end = target_dt + pd.Timedelta(hours=6)

    docs_weather = list(weather_col.find({
        "name": city,
        "collected_at": {
            "$gte": start.to_pydatetime(),
            "$lte": end.to_pydatetime()
        }
    }).sort("collected_at", 1))

    if not docs_weather:
        return None, None

    def time_diff(doc):
        collected = pd.to_datetime(doc["collected_at"], utc=True)
        return abs(collected - target_dt)

    closest = min(docs_weather, key=time_diff)
    description = closest["weather"][0]["description"]
    date_used = closest["collected_at"]

    return description, date_used

df_flat_filtered["departure_meteo"] = None
df_flat_filtered["departure_meteo_date"] = None

for idx, row in df_flat_filtered.iterrows():
    iata = row.get("departure_iata")
    city = airport_to_city.get(iata)

    if city is None:
        continue

    if pd.notna(row.get("departure_actual")):
        ref_dt = row["departure_actual"]
    elif pd.notna(row.get("departure_estimated")):
        ref_dt = row["departure_estimated"]
    else:
        ref_dt = row.get("departure_scheduled")

    meteo, meteo_dt = find_closest_weather(city, ref_dt)
    df_flat_filtered.at[idx, "departure_meteo"] = meteo
    df_flat_filtered.at[idx, "departure_meteo_date"] = meteo_dt

#print("Ajout des colonnes météo terminé.")

missing_count = df_flat_filtered["departure_meteo"].isna().sum()
total = len(df_flat_filtered)
missing_percent = (missing_count / total) * 100

#print(f"Valeurs manquantes météo : {missing_count} / {total} ({missing_percent:.2f}%)")
#print(df_flat_filtered["departure_meteo"].value_counts(dropna=False))

mode_meteo = df_flat_filtered["departure_meteo"].mode()[0]
df_flat_filtered["departure_meteo"] = df_flat_filtered["departure_meteo"].fillna(mode_meteo)
#print("Mode météo utilisé pour remplir les valeurs manquantes :", mode_meteo)

# ============================================
# ETAPE 6 : SUPPRESSION DES COLONNES INUTILES
# ============================================
cols_with_date = [c for c in df_flat_filtered.columns if "date" in c.lower()]

explicit_drop = [
    "flight_status",
    "collected_at",
    "filtered_at",
    "departure_scheduled",
    "departure_estimated",
    "departure_actual",
    "arrival_scheduled",
    "arrival_estimated",
    "arrival_actual",
    "departure_timezone",
]

other_useless = [
    "airline_icao",
    "aircraft_icao",
    "aircraft_icao24",
    "flight_icao",
    "flight_number",
    "flight_iata",
    "flight_codeshared",
    "arrival_terminal",
    "arrival_gate",
    "arrival_timezone",
    "arrival_baggage",
    "departure_terminal",
    "departure_gate",
    "departure_airport",
    "arrival_airport",
    "departure_icao",
    "arrival_icao",
    "airline_iata",
    "_id",
]

cols_to_remove = set(cols_with_date + explicit_drop + other_useless)
cols_to_remove = [c for c in cols_to_remove if c in df_flat_filtered.columns]

df_flat_filtered = df_flat_filtered.drop(columns=cols_to_remove)

#print("Colonnes supprimées :", cols_to_remove)
#print("Nombre total supprimé :", len(cols_to_remove))

# ============================================
# ETAPE 7 : SEPARATION FEATURES / TARGET
# ============================================
df_model = df_flat_filtered.dropna(subset=["arrival_delay_actual"])
feats = df_model.drop("arrival_delay_actual", axis=1)
target = df_model["arrival_delay_actual"]

X_train, X_test, y_train, y_test = train_test_split(
    feats, target, test_size=0.25, random_state=42
)

print("Taille train :", X_train.shape, "Taille test :", X_test.shape)

# ============================================
# ETAPE 8 : PIPELINE SKLEARN COMPLET
# ============================================
cat_cols = X_train.select_dtypes(include=["object"]).columns.tolist()

preprocess = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ],
    remainder="passthrough"
)

gbr = GradientBoostingRegressor(
    learning_rate=0.1,
    max_depth=2,
    n_estimators=50 , random_state=42
)

pipeline = Pipeline(steps=[
    ("preprocess", preprocess),
    ("model", gbr)
])

pipeline.fit(X_train, y_train)

y_train_pred = pipeline.predict(X_train)
y_test_pred = pipeline.predict(X_test)

print("GradientBoosting - R2 train :", r2_score(y_train, y_train_pred))
print("GradientBoosting - R2 test  :", r2_score(y_test, y_test_pred))


client.close()

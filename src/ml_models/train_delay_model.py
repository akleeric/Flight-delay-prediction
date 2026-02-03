# test ML pas à pas
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
from pprint import pprint

# ETAPE 0  : RECUPERATION DES DONNEES
load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["flight_delay_history_db"]
collection = db["aviationstack_historical_landed_flights"]

# Filtre : vols atterris avec données complètes minimales
query = {
    "flight_status": "landed",
    "arrival.actual": {"$nin": [None, ""]},
    "arrival.scheduled": {"$nin": [None, ""]},
    "departure.scheduled": {"$nin": [None, ""]},
    "departure.actual": {"$nin": [None, ""]},
}

docs = list(collection.find(query))



# ETAPE 1  : APPLATISSEMENT DES DONNEES
# 🔹 Aplatir les documents imbriqués
df_flat = pd.json_normalize(
    docs,
    sep="_"  # airline.name -> airline_name
)

# 🔹 Garder / renommer les colonnes utiles
cols_to_keep = [
    "_id",
    "flight_date",
    "flight_status",
    "collected_at",
    "filtered_at",
    "live",

    # Airline
    "airline_name",
    "airline_iata",
    "airline_icao",

    # Aircraft
    "aircraft_registration",
    "aircraft_iata",
    "aircraft_icao",
    "aircraft_icao24",

    # Departure
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

    # Arrival
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

    # Flight
    "flight_number",
    "flight_iata",
    "flight_icao",
    "flight_codeshared",
]

# Certaines colonnes peuvent ne pas exister pour tous les docs → on intersecte
existing_cols = [c for c in cols_to_keep if c in df_flat.columns]
df_flat = df_flat[existing_cols]

# Optionnel : conversion de quelques champs en datetime
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

# df_flat.head()

# ETAPE 2  : ANALYSE DES VALEURS NULLS ET SUPPRESSIONS DES COLONNES INUTILES
# Nombre de valeurs nulles par colonne
null_counts = df_flat.isnull().sum()

# Pourcentage de valeurs nulles par colonne
null_percent = (null_counts / len(df_flat)) * 100

# Résumé filtré : uniquement les colonnes avec plus de 30% de valeurs nulles
null_summary = (
    pd.DataFrame({
        "null_count": null_counts,
        "null_percent": null_percent.round(2)
    })
    .query("null_percent > 0")
    .sort_values(by="null_percent", ascending=False)
)

pprint(null_summary)

# On supprimme les colonnes qui ont plus de 30% de valeurs nulls
# Colonnes à supprimer : null_percent > 30%
cols_to_drop = null_summary[null_summary["null_percent"] > 30.0].index.tolist()

# Nouveau DataFrame nettoyé
df_flat_filtered = df_flat.drop(columns=cols_to_drop)

print(f"Colonnes supprimées : {len(cols_to_drop)}")
print(cols_to_drop)

# Suppressions des colonnes runway car inutiles
cols_runway = [col for col in df_flat_filtered.columns if "runway" in col.lower()]

df_flat_filtered = df_flat_filtered.drop(columns=cols_runway)

print("Colonnes runway supprimées :", cols_runway)

# df_flat_filtered.head()

# ETAPE 3  : TRAITEMENT DES VALEURS NULLS
# Ici c'est la colonne departure_terminal
pprint(df_flat_filtered['departure_terminal'].value_counts()) 
mode_value = df_flat_filtered['departure_terminal'].mode()[0]
df_flat_filtered['departure_terminal'] = df_flat_filtered['departure_terminal'].fillna(mode_value)

# Vérification si il y a encore des valeurs nulls
df_flat_filtered.isnull().any().any()

# ETAPE 4 : CALCUL DES DÉLAIS
# Fonction utilitaire pour calculer un délai en minutes
def compute_delay(actual, scheduled):
    if pd.isna(actual) or pd.isna(scheduled):
        return None
    delay = (actual - scheduled).total_seconds() / 60
    return max(delay, 0)  # clamp à 0

# Délais départ
df_flat_filtered["departure_delay_actual"] = df_flat_filtered.apply(
    lambda row: compute_delay(row["departure_actual"], row["departure_scheduled"]),
    axis=1
)

df_flat_filtered["departure_delay_estimated"] = df_flat_filtered.apply(
    lambda row: compute_delay(row["departure_estimated"], row["departure_scheduled"]),
    axis=1
)

# Délais arrivée
df_flat_filtered["arrival_delay_actual"] = df_flat_filtered.apply(
    lambda row: compute_delay(row["arrival_actual"], row["arrival_scheduled"]),
    axis=1
)

df_flat_filtered["arrival_delay_estimated"] = df_flat_filtered.apply(
    lambda row: compute_delay(row["arrival_estimated"], row["arrival_scheduled"]),
    axis=1
)

# Vérification rapide
df_flat_filtered[[
    "departure_delay_actual",
    "departure_delay_estimated",
    "arrival_delay_actual",
    "arrival_delay_estimated"
]].sort_values(by="arrival_delay_actual", ascending=False).head()

#df_flat_filtered.sort_values(by="arrival_delay_actual", ascending=False).head()

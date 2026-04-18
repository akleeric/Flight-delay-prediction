import os
import sys
import json
import requests

# ---------------------------------------------------------
# 1. Ajouter la racine du projet au PYTHONPATH
# ---------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------
# 2. Imports internes (après le sys.path)
# ---------------------------------------------------------
from src.collectors.prediction_collector import PredictionCollector


API_URL = "http://127.0.0.1:8000/predict"


def run_prediction():
    collector = PredictionCollector()

    print("✈️ Récupération des vols actifs/scheduled...")
    flights = collector.get_live_flights()
    print(f"➡️ {len(flights)} vols récupérés")

    print("🌦️ Récupération des météos...")
    weather = collector.collect_weather_for_flights(flights)
    print(f"➡️ {len(weather)} villes météo récupérées")

    print("🧮 Construction des features pour la prédiction...")
    features = collector.build_processed_features(flights, weather)
    print(f"➡️ {len(features)} lignes de features générées")

    print("🔮 Envoi des features à l’API pour prédiction...")

    payload = {"flights": features}

    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        response.raise_for_status()
        predictions = response.json().get("predictions", [])
    except Exception as e:
        print(f"❌ Erreur lors de l'appel API : {e}")
        return

    print("📊 Prédictions reçues :")
    for idx, pred in enumerate(predictions):
        print(f"  - Vol {idx+1}: retard estimé = {pred:.2f} minutes")

    print("✅ Pipeline complète terminée.")


if __name__ == "__main__":
    run_prediction()

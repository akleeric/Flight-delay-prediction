import json
import requests
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

    print("📁 Données brutes sauvegardées dans data/raw/")

    print("🧮 Construction des features pour la prédiction...")
    features = collector.build_processed_features(flights, weather)
    print(f"➡️ {len(features)} lignes de features générées")

    print("📁 Données transformées sauvegardées dans data/processed/prediction_features.json")

    # ---------------------------------------------------------
    # 4. Appel API pour obtenir les prédictions
    # ---------------------------------------------------------
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

import requests
import os

from src.collectors.prediction_collector import PredictionCollector
from src.utils.transformers import build_features
from src.utils.storage import save_processed
from config.settings import settings


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_prediction():
    collector = PredictionCollector()

    # 1. Récupérer un vol réel
    flight = collector.get_one_flight_from_cdg()
    if not flight:
        print("❌ Aucun vol trouvé au départ de CDG")
        return

    # 2. Récupérer la météo
    weather = collector.get_weather_paris()

    # 3. Transformer en features
    features = build_features(flight, weather)

    # 🔥 Sauvegarde des features transformées
    save_processed("features_for_api", features)

    print("Features envoyées :", features)

    # 4. Appeler ton API FastAPI
    response = requests.post(f"{settings.API_URL}/predict", json=features)
    print("Prediction:", response.json())


if __name__ == "__main__":
    run_prediction()

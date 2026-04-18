from fastapi import FastAPI, HTTPException
from src.api.schemas import FlightBatchInput
from src.api.predict import predict_batch
import json
import subprocess
import os

app = FastAPI(
    title="Flight Delay Prediction API",
    description="API pour consulter les données collectées, relancer la collecte, entraîner le modèle et prédire les retards.",
    version="2.0.0"
)

# ---------------------------------------------------------
# Détection automatique de la racine du projet
# ---------------------------------------------------------
# __file__ = src/api/main.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_RAW = os.path.join(PROJECT_ROOT, "data", "raw")
DATA_PROCESSED = os.path.join(PROJECT_ROOT, "data", "processed")


@app.get("/")
def root():
    return {"message": "Flight Delay Prediction API is running"}


# ---------------------------------------------------------
# 1. Récupérer les données RAW
# ---------------------------------------------------------
@app.get("/flights/raw")
def get_flights_raw():
    path = os.path.join(DATA_RAW, "flights_raw.json")
    if not os.path.exists(path):
        raise HTTPException(404, "flights_raw.json introuvable")
    return json.load(open(path))


@app.get("/weather/raw")
def get_weather_raw():
    path = os.path.join(DATA_RAW, "weather_raw.json")
    if not os.path.exists(path):
        raise HTTPException(404, "weather_raw.json introuvable")
    return json.load(open(path))


# ---------------------------------------------------------
# 2. Récupérer les données PROCESSED
# ---------------------------------------------------------
@app.get("/flights/processed")
def get_processed_features():
    path = os.path.join(DATA_PROCESSED, "prediction_features.json")
    if not os.path.exists(path):
        raise HTTPException(404, "prediction_features.json introuvable")
    return json.load(open(path))


# ---------------------------------------------------------
# 3. Lancer la prédiction (batch)
# ---------------------------------------------------------
@app.post("/predict")
def predict(input_data: FlightBatchInput):
    return predict_batch(input_data)


# ---------------------------------------------------------
# 4. Relancer la collecte (run_collector)
# ---------------------------------------------------------
@app.post("/run/collector")
def run_collector():
    """
    Lance uniquement la collecte (flights_raw + weather_raw)
    et la transformation processed.
    """
    try:
        script_path = os.path.join(PROJECT_ROOT, "scripts", "run_collectors.py")

        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(
                500,
                f"Erreur lors de la collecte : {result.stderr}"
            )

        return {"status": "OK", "message": "Collecte exécutée avec succès"}

    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la collecte : {e}")


# ---------------------------------------------------------
# 5. Relancer l'entraînement du modèle
# ---------------------------------------------------------
@app.post("/run/training")
def run_training():
    """
    Lance l'entraînement du modèle ML.
    """
    try:
        script_path = os.path.join(PROJECT_ROOT, "scripts", "run_training.py")

        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(
                500,
                f"Erreur lors du training : {result.stderr}"
            )

        return {"status": "OK", "message": "Training exécuté avec succès"}

    except Exception as e:
        raise HTTPException(500, f"Erreur lors du training : {e}")

# ---------------------------------------------------------
# 6. Lancer la prédiction live (collecte + features + prédiction)
# ---------------------------------------------------------
@app.post("/run/live_prediction")
def run_live_prediction():
    """
    Collecte les vols live + météo, génère les features,
    appelle l'API /predict et renvoie les prédictions.
    """
    try:
        script_path = os.path.join(PROJECT_ROOT, "scripts", "run_live_prediction.py")

        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(
                500,
                f"Erreur lors de la prédiction live : {result.stderr}"
            )

        return {
            "status": "OK",
            "message": "Prédiction live exécutée avec succès",
            "output": result.stdout
        }

    except Exception as e:
        raise HTTPException(500, f"Erreur lors de la prédiction live : {e}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    path_as = os.path.join(DATA_RAW, "flights_raw.json")
    path_al = os.path.join(DATA_RAW, "airlabs_flights_raw.json")
    flights = []
    if os.path.exists(path_as):
        flights += json.load(open(path_as))
    if os.path.exists(path_al):
        for f in json.load(open(path_al)):
            flights.append({
                "flight_date": f.get("dep_time_utc", "")[:10],
                "flight_status": f.get("status", "active"),
                "departure": {
                    "iata": f.get("dep_iata"),
                    "scheduled": f.get("dep_time_utc", "").replace(" ", "T") + ":00+00:00" if f.get("dep_time_utc") else "",
                    "actual": f.get("dep_actual_utc", "").replace(" ", "T") + ":00+00:00" if f.get("dep_actual_utc") else None,
                    "delay": f.get("delayed"),
                },
                "arrival": {
                    "iata": f.get("arr_iata"),
                    "scheduled": f.get("arr_time_utc", "").replace(" ", "T") + ":00+00:00" if f.get("arr_time_utc") else "",
                },
                "airline": {
                    "iata": f.get("airline_iata", ""),
                    "name": f.get("airline_iata", ""),
                },
                "flight": {
                    "iata": f.get("flight_iata", ""),
                    "number": f.get("flight_number", ""),
                }
            })
    if not flights:
        raise HTTPException(404, "Aucun vol disponible")
    return flights


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
    Lance l'entraînement du modèle ML en arrière-plan.

    Le réentraînement dure plusieurs minutes. On lance donc le script en
    tâche détachée (fire-and-forget) et on répond immédiatement, afin
    d'éviter le timeout de la passerelle Railway (erreur 502).
    """
    try:
        script_path = os.path.join(PROJECT_ROOT, "scripts", "run_training.py")

        subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return JSONResponse(
            status_code=202,
            content={
                "status": "STARTED",
                "message": "Entraînement lancé en arrière-plan (plusieurs minutes).",
            },
        )

    except Exception as e:
        raise HTTPException(500, f"Erreur lors du lancement du training : {e}")

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

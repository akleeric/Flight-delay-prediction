from fastapi import FastAPI
from src.api.schemas import FlightBatchInput
from src.api.predict import predict_batch

app = FastAPI(
    title="Flight Delay Prediction API",
    description="API permettant de prédire le retard d'arrivée d'un ou plusieurs vols",
    version="2.0.0"
)

@app.get("/")
def root():
    return {"message": "Flight Delay Prediction API is running"}


@app.post("/predict")
def predict(input_data: FlightBatchInput):
    """
    Endpoint principal : reçoit une liste de vols featurés
    et renvoie une liste de retards prédits.
    """
    return predict_batch(input_data)

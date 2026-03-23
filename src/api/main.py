from fastapi import FastAPI
from src.api.schemas import FlightInput
from src.api.predict import predict_delay

app = FastAPI(
    title="Flight Delay Prediction API",
    description="API permettant de prédire le retard d'arrivée d'un vol",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "Flight Delay Prediction API is running"}

@app.post("/predict")
def predict(input_data: FlightInput):
    """
    Endpoint principal : reçoit les features d'un vol et renvoie le retard prédit.
    """
    return predict_delay(input_data)

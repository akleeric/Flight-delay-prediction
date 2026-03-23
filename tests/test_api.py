from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_predict():
    payload = {
        "airline_name": "easyJet",
        "departure_iata": "ORY",
        "arrival_iata": "LIS",
        "departure_delay_actual": 54.0,
        "departure_delay_estimated": 0.0,
        "arrival_delay_estimated": 18.0,
        "flight_duration_scheduled": 95.0,
        "departure_meteo": "broken clouds"
    }

    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    assert "predicted_delay" in response.json()

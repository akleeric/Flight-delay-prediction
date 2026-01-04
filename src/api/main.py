"""Application FastAPI principale"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from src.api.schemas import (
    FlightPredictionRequest, 
    FlightPredictionResponse,
    HealthResponse,
    StatsResponse
)
from src.api.predict import get_predictor
from src.data_processing import get_mongodb_client

# Créer l'application
app = FastAPI(
    title="Flight Delay Prediction API",
    description="API de prédiction de retards de vols",
    version="1.0.0"
)

# CORS (pour permettre les appels depuis un frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
async def root():
    """Endpoint racine"""
    return {
        "message": "Flight Delay Prediction API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "stats": "/stats",
            "predict": "/predict",
            "docs": "/docs"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Vérification de santé de l'API"""
    model_loaded = False
    db_connected = False
    
    # Vérifier le modèle
    try:
        predictor = get_predictor()
        model_loaded = predictor.model_data is not None
    except:
        pass
    
    # Vérifier la DB
    try:
        mongo = get_mongodb_client()
        mongo.get_statistics()
        db_connected = True
        mongo.close()
    except:
        pass
    
    return {
        "status": "healthy" if (model_loaded and db_connected) else "degraded",
        "timestamp": datetime.utcnow(),
        "model_loaded": model_loaded,
        "database_connected": db_connected
    }

@app.get("/stats", response_model=StatsResponse, tags=["Stats"])
async def get_stats():
    """Statistiques de la base de données"""
    try:
        mongo = get_mongodb_client()
        stats = mongo.get_statistics()
        
        # Dernier vol
        last_flights = mongo.get_aviationstack_flights(limit=1)
        last_update = None
        if last_flights:
            last_update = last_flights[0].get('collected_at')
            if last_update:
                last_update = str(last_update)
        
        mongo.close()
        
        return {
            "total_flights": stats.get('aviationstack', 0),
            "total_weather": stats.get('weather', 0),
            "last_update": last_update
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict", response_model=FlightPredictionResponse, tags=["Prediction"])
async def predict_delay(flight: FlightPredictionRequest):
    """
    Prédire si un vol sera retardé
    
    Exemple de requête:
```json
    {
        "airline_iata": "AF",
        "departure_airport": "CDG",
        "arrival_airport": "JFK",
        "scheduled_hour": 14,
        "day_of_week": 2,
        "month": 1
    }
```
    """
    try:
        predictor = get_predictor()
        
        # Prédiction
        result = predictor.predict({
            'airline_iata': flight.airline_iata,
            'departure_airport': flight.departure_airport,
            'arrival_airport': flight.arrival_airport,
            'scheduled_hour': flight.scheduled_hour,
            'day_of_week': flight.day_of_week,
            'month': flight.month
        })
        
        # Construire la réponse
        is_weekend = flight.day_of_week >= 5
        
        return {
            "is_delayed": result['is_delayed'],
            "delay_probability": result['delay_probability'],
            "confidence": result['confidence'],
            "flight_info": {
                "route": f"{flight.departure_airport} → {flight.arrival_airport}",
                "airline": flight.airline_iata,
                "departure_time": f"{flight.scheduled_hour:02d}:00",
                "is_weekend": is_weekend,
                "probabilities": result['probabilities']
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""Schémas Pydantic pour l'API"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FlightPredictionRequest(BaseModel):
    """Requête de prédiction de retard"""
    airline_iata: str = Field(..., example="AF", description="Code IATA compagnie")
    departure_airport: str = Field(..., example="CDG", description="Aéroport départ")
    arrival_airport: str = Field(..., example="JFK", description="Aéroport arrivée")
    scheduled_hour: int = Field(..., ge=0, le=23, example=14, description="Heure départ (0-23)")
    day_of_week: int = Field(..., ge=0, le=6, example=2, description="Jour semaine (0=Lundi)")
    month: int = Field(..., ge=1, le=12, example=1, description="Mois (1-12)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "airline_iata": "AF",
                "departure_airport": "CDG",
                "arrival_airport": "JFK",
                "scheduled_hour": 14,
                "day_of_week": 2,
                "month": 1
            }
        }

class FlightPredictionResponse(BaseModel):
    """Réponse de prédiction"""
    is_delayed: bool = Field(..., description="Vol retardé?")
    delay_probability: float = Field(..., description="Probabilité de retard (0-1)")
    confidence: str = Field(..., description="Niveau de confiance")
    flight_info: dict = Field(..., description="Infos du vol")

class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str
    timestamp: datetime
    model_loaded: bool
    database_connected: bool

class StatsResponse(BaseModel):
    """Statistiques de la base de données"""
    total_flights: int
    total_weather: int
    last_update: Optional[str]

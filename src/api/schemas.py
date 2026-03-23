from pydantic import BaseModel, Field

class FlightInput(BaseModel):
    airline_name: str = Field(..., description="Nom de la compagnie aérienne")
    departure_iata: str = Field(..., description="Code IATA de l'aéroport de départ")
    arrival_iata: str = Field(..., description="Code IATA de l'aéroport d'arrivée")
    departure_delay_actual: float = Field(..., description="Retard réel au départ (minutes)")
    departure_delay_estimated: float = Field(..., description="Retard estimé au départ (minutes)")
    arrival_delay_estimated: float = Field(..., description="Retard estimé à l'arrivée (minutes)")
    flight_duration_scheduled: float = Field(..., description="Durée prévue du vol (minutes)")
    departure_meteo: str = Field(..., description="Description météo au départ")

    class Config:
        schema_extra = {
            "example": {
                "airline_name": "easyJet",
                "departure_iata": "ORY",
                "arrival_iata": "LIS",
                "departure_delay_actual": 54.0,
                "departure_delay_estimated": 0.0,
                "arrival_delay_estimated": 18.0,
                "flight_duration_scheduled": 95.0,
                "departure_meteo": "broken clouds"
            }
        }

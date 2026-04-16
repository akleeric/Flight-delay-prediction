from typing import List
from pydantic import BaseModel, Field


class FlightFeatures(BaseModel):
    # Identité vol
    airline_name: str = Field(..., description="Nom de la compagnie aérienne")
    departure_iata: str = Field(..., description="Code IATA de l'aéroport de départ")
    arrival_iata: str = Field(..., description="Code IATA de l'aéroport d'arrivée")

    # Features temporelles
    scheduled_hour: int = Field(..., description="Heure de départ prévue (0-23)")
    day_of_week: int = Field(..., description="Jour de la semaine (1=lundi ... 7=dimanche)")
    month: int = Field(..., description="Mois (1-12)")
    is_weekend: int = Field(..., description="1 si week-end, 0 sinon")

    # Retards & durée
    departure_delay_actual: float = Field(..., description="Retard réel au départ (minutes, >= 0)")
    departure_delay_estimated: float = Field(..., description="Retard estimé au départ (minutes, >= 0)")
    arrival_delay_estimated: float = Field(..., description="Retard estimé à l'arrivée (minutes, >= 0)")
    flight_duration_scheduled: float = Field(..., description="Durée prévue du vol (minutes, >= 0)")

    # Météo départ
    dep_temperature: float | None = Field(None, description="Température au départ (°C)")
    dep_wind_speed: float | None = Field(None, description="Vitesse du vent au départ (m/s)")
    dep_visibility: float | None = Field(None, description="Visibilité au départ (m)")
    dep_precipitation: float | None = Field(None, description="Précipitations au départ (mm/h)")
    dep_weather_bad: int | None = Field(None, description="1 si météo mauvaise au départ, 0 sinon")

    # Météo arrivée
    arr_temperature: float | None = Field(None, description="Température à l'arrivée (°C)")
    arr_wind_speed: float | None = Field(None, description="Vitesse du vent à l'arrivée (m/s)")
    arr_visibility: float | None = Field(None, description="Visibilité à l'arrivée (m)")
    arr_precipitation: float | None = Field(None, description="Précipitations à l'arrivée (mm/h)")
    arr_weather_bad: int | None = Field(None, description="1 si météo mauvaise à l'arrivée, 0 sinon")

    class Config:
        schema_extra = {
            "example": {
                "airline_name": "Kenya Airways",
                "departure_iata": "CDG",
                "arrival_iata": "BCN",
                "scheduled_hour": 18,
                "day_of_week": 4,
                "month": 4,
                "is_weekend": 0,
                "departure_delay_actual": 20.0,
                "departure_delay_estimated": 0.0,
                "arrival_delay_estimated": 0.0,
                "flight_duration_scheduled": 105.0,
                "dep_temperature": 18.07,
                "dep_wind_speed": 3.09,
                "dep_visibility": 10000,
                "dep_precipitation": 0.0,
                "dep_weather_bad": 0,
                "arr_temperature": 20.24,
                "arr_wind_speed": 3.6,
                "arr_visibility": 10000,
                "arr_precipitation": 0.0,
                "arr_weather_bad": 0,
            }
        }


class FlightBatchInput(BaseModel):
    flights: List[FlightFeatures]

    class Config:
        schema_extra = {
            "example": {
                "flights": [
                    {
                        "airline_name": "Kenya Airways",
                        "departure_iata": "CDG",
                        "arrival_iata": "BCN",
                        "scheduled_hour": 18,
                        "day_of_week": 4,
                        "month": 4,
                        "is_weekend": 0,
                        "departure_delay_actual": 20.0,
                        "departure_delay_estimated": 0.0,
                        "arrival_delay_estimated": 0.0,
                        "flight_duration_scheduled": 105.0,
                        "dep_temperature": 18.07,
                        "dep_wind_speed": 3.09,
                        "dep_visibility": 10000,
                        "dep_precipitation": 0.0,
                        "dep_weather_bad": 0,
                        "arr_temperature": 20.24,
                        "arr_wind_speed": 3.6,
                        "arr_visibility": 10000,
                        "arr_precipitation": 0.0,
                        "arr_weather_bad": 0,
                    }
                ]
            }
        }

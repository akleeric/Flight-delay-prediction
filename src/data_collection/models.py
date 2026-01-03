"""Data Models adaptés à votre structure"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class FlightStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    LANDED = "landed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"
    UNKNOWN = "unknown"

class Airport(BaseModel):
    iata_code: str = Field(..., min_length=3, max_length=3)
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class Airline(BaseModel):
    iata_code: str = Field(..., min_length=2, max_length=2)
    name: str

class FlightLeg(BaseModel):
    airport: str
    iata: str = Field(..., min_length=3, max_length=3)
    terminal: Optional[str] = None
    gate: Optional[str] = None
    scheduled: Optional[datetime] = None
    actual: Optional[datetime] = None
    delay: Optional[int] = None

class FlightRealtime(BaseModel):
    flight_iata: str
    flight_number: str
    airline: Airline
    departure: FlightLeg
    arrival: FlightLeg
    status: FlightStatus = FlightStatus.UNKNOWN
    data_source: str
    collected_at: datetime = Field(default_factory=datetime.utcnow)

class WeatherData(BaseModel):
    city: str
    temperature: Optional[float] = None
    humidity: Optional[int] = None
    wind_speed: Optional[float] = None
    weather_condition: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)

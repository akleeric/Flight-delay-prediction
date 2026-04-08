from datetime import datetime

def to_minutes(date1, date2):
    if not date1 or not date2:
        return 0.0
    d1 = datetime.fromisoformat(date1.replace("Z", "+00:00"))
    d2 = datetime.fromisoformat(date2.replace("Z", "+00:00"))
    return (d1 - d2).total_seconds() / 60

def extract_weather_description(weather_json):
    return weather_json["weather"][0]["description"]

def build_features(flight_json, weather_json):
    dep = flight_json["departure"]
    arr = flight_json["arrival"]
    airline = flight_json["airline"]

    return {
        "airline_name": airline["name"],
        "departure_iata": dep["iata"],
        "arrival_iata": arr["iata"],
        "departure_delay_actual": to_minutes(dep["actual"], dep["scheduled"]),
        "departure_delay_estimated": to_minutes(dep["estimated"], dep["scheduled"]),
        "arrival_delay_estimated": to_minutes(arr["estimated"], arr["scheduled"]),
        "flight_duration_scheduled": to_minutes(arr["scheduled"], dep["scheduled"]),
        "departure_meteo": extract_weather_description(weather_json)
    }

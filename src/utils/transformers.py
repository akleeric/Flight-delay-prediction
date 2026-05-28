# src/utils/transformers.py

from datetime import datetime
from src.ml.features import extract_weather_fields
from src.utils.iata import IATA_TO_CITY


def to_minutes(date1, date2):
    if not date1 or not date2:
        return 0.0
    d1 = datetime.fromisoformat(date1.replace("Z", "+00:00"))
    d2 = datetime.fromisoformat(date2.replace("Z", "+00:00"))
    diff = (d1 - d2).total_seconds() / 60
    return max(diff, 0.0)


def build_features(flight_json, dep_weather_json, arr_weather_json):
    dep = flight_json["departure"]
    arr = flight_json["arrival"]
    airline = flight_json["airline"]

    scheduled_dt = datetime.fromisoformat(dep["scheduled"].replace("Z", "+00:00"))

    scheduled_hour = scheduled_dt.hour
    day_of_week = scheduled_dt.weekday() + 1
    month = scheduled_dt.month
    is_weekend = 1 if day_of_week in [6, 7] else 0

    departure_delay_actual = to_minutes(dep.get("actual"), dep.get("scheduled"))
    departure_delay_estimated = to_minutes(dep.get("estimated"), dep.get("scheduled"))
    arrival_delay_estimated = to_minutes(arr.get("estimated"), arr.get("scheduled"))
    flight_duration_scheduled = to_minutes(arr.get("scheduled"), dep.get("scheduled"))

    dep_fields = extract_weather_fields(dep_weather_json)
    arr_fields = extract_weather_fields(arr_weather_json)

    return {
        "flight_iata": flight_json.get("flight", {}).get("iata", ""),
        "airline_iata": airline.get("iata", ""),
        "airline_name": airline["name"],
        "departure_iata": dep["iata"],
        "arrival_iata": arr["iata"],

        "scheduled_hour": scheduled_hour,
        "day_of_week": day_of_week,
        "month": month,
        "is_weekend": is_weekend,

        "departure_delay_actual": departure_delay_actual,
        "departure_delay_estimated": departure_delay_estimated,
        "arrival_delay_estimated": arrival_delay_estimated,
        "flight_duration_scheduled": flight_duration_scheduled,

        "dep_temperature": dep_fields["temperature"],
        "dep_wind_speed": dep_fields["wind_speed"],
        "dep_visibility": dep_fields["visibility"],
        "dep_precipitation": dep_fields["precipitation"],
        "dep_weather_bad": dep_fields["weather_bad"],

        "arr_temperature": arr_fields["temperature"],
        "arr_wind_speed": arr_fields["wind_speed"],
        "arr_visibility": arr_fields["visibility"],
        "arr_precipitation": arr_fields["precipitation"],
        "arr_weather_bad": arr_fields["weather_bad"],
    }


def build_features_for_flights(flights, weather_list):
    """
    Transforme une liste de vols + liste de météos brutes
    en une liste de features prêtes pour le modèle.
    """

    # Index météo par ville
    weather_by_city = {w["city"]: w for w in weather_list if "city" in w}

    features = []

    for f in flights:
        dep_iata = f.get("departure", {}).get("iata")
        arr_iata = f.get("arrival", {}).get("iata")

        # Mapping IATA -> ville
        dep_city = IATA_TO_CITY.get(dep_iata)
        arr_city = IATA_TO_CITY.get(arr_iata)

        # Si on n'a pas la météo pour l'une des deux villes, on peut choisir de skipper
        if not dep_city or not arr_city:
            continue
        if dep_city not in weather_by_city or arr_city not in weather_by_city:
            continue

        dep_weather = weather_by_city[dep_city]
        arr_weather = weather_by_city[arr_city]

        feat = build_features(f, dep_weather, arr_weather)
        features.append(feat)

    return features

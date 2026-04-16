import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet

MODEL_PATH = "data/models/flight_delay_model.pkl"


def build_model():
    # -----------------------------
    # Colonnes catégorielles
    # -----------------------------
    categorical_features = [
        "airline_name",
        "departure_iata",
        "arrival_iata",
    ]

    # -----------------------------
    # Colonnes numériques
    # -----------------------------
    numeric_features = [
        # Features temporelles
        "scheduled_hour",
        "day_of_week",
        "month",
        "is_weekend",

        # Retards & durée
        "departure_delay_actual",
        "departure_delay_estimated",
        "arrival_delay_estimated",
        "flight_duration_scheduled",

        # Météo départ
        "dep_temperature",
        "dep_wind_speed",
        "dep_visibility",
        "dep_precipitation",
        "dep_weather_bad",

        # Météo arrivée
        "arr_temperature",
        "arr_wind_speed",
        "arr_visibility",
        "arr_precipitation",
        "arr_weather_bad",
    ]

    # -----------------------------
    # Préprocesseur
    # -----------------------------
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore"))
            ]), categorical_features),

            ("num", SimpleImputer(strategy="mean"), numeric_features)
        ]
    )

    # -----------------------------
    # Modèle ML
    # -----------------------------
    model = ElasticNet(alpha=0.1, l1_ratio=0.2, random_state=42)

    return Pipeline([
        ("preprocess", preprocessor),
        ("model", model),
    ])


def save_model(model):
    joblib.dump(model, MODEL_PATH)


def load_model():
    return joblib.load(MODEL_PATH)

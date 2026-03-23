import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor

MODEL_PATH = "data/models/flight_delay_model.pkl"


def build_model():
    """
    Construit le pipeline sklearn complet :
    - OneHotEncoder sur les variables catégorielles
    - GradientBoostingRegressor comme modèle
    """
    categorical_features = [
        "airline_name",
        "departure_iata",
        "arrival_iata",
        "departure_meteo",
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="passthrough",
    )

    gbr = GradientBoostingRegressor(
        learning_rate=0.1,
        max_depth=2,
        n_estimators=50,
        random_state=42,
    )

    model = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", gbr),
        ]
    )

    return model


def save_model(model):
    joblib.dump(model, MODEL_PATH)


def load_model():
    return joblib.load(MODEL_PATH)

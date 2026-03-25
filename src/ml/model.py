import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingRegressor

MODEL_PATH = "data/models/flight_delay_model.pkl"


def build_model(categorical_features):
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ],
        remainder="passthrough",
    )

    model = GradientBoostingRegressor(
        learning_rate=0.1,
        max_depth=2,
        n_estimators=50,
        random_state=42
    )

    return Pipeline([
        ("preprocess", preprocessor),
        ("model", model),
    ])


def save_model(model):
    joblib.dump(model, MODEL_PATH)


def load_model():
    return joblib.load(MODEL_PATH)

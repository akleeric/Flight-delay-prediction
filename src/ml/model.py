import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor 
from sklearn.linear_model import Ridge 
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import HistGradientBoostingRegressor  # <-- modèle qui gère les NaN

MODEL_PATH = "data/models/flight_delay_model.pkl"



def build_model():
    # Définition des features selon FlightInput
    categorical_features = [
        "airline_name",
        "departure_iata",
        "arrival_iata",
        "departure_meteo"
    ]

    numeric_features = [
        "departure_delay_actual",
        "departure_delay_estimated",
        "arrival_delay_estimated",
        "flight_duration_scheduled"
    ]

    # Préprocesseur
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore"))
            ]), categorical_features),

            ("num", SimpleImputer(strategy="mean"), numeric_features)
        ]
    )

    #model = GradientBoostingRegressor(learning_rate=0.1,max_depth=2,n_estimators=50,random_state=42) #Gradientboost
    #model = RandomForestRegressor(n_estimators=50,max_depth=4,min_samples_split=4, random_state=42,n_jobs=-1, ) # RandomForest
    #model = Ridge( alpha=1.0,  random_state=42 ) # Ridge
    model = ElasticNet(alpha=0.1, l1_ratio=0.2, random_state=42)
    

    return Pipeline([
        ("preprocess", preprocessor),
        ("model", model),
    ])


def save_model(model):
    joblib.dump(model, MODEL_PATH)


def load_model():
    return joblib.load(MODEL_PATH)

import logging
import pandas as pd
from sklearn.metrics import r2_score

from src.utils.mongo import load_historical_flights_as, load_historical_flights_al
from src.ml.features import build_training_dataset
from src.ml.model import build_model, save_model

logger = logging.getLogger(__name__)


def harmonize_airlabs(df_al: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les colonnes AirLabs vers le schéma Aviationstack
    pour que features.py puisse traiter les deux sources.
    """
    if df_al.empty:
        return df_al

    df = df_al.copy()

    rename_map = {
        "dep_time_utc": "departure_scheduled",
        "dep_estimated_utc": "departure_estimated",
        "dep_actual_utc": "departure_actual",
        "arr_time_utc": "arrival_scheduled",
        "arr_estimated_utc": "arrival_estimated",
    }
    df.rename(columns=rename_map, inplace=True)

    if "dep_iata" in df.columns:
        df["departure_iata"] = df["dep_iata"]
    if "arr_iata" in df.columns:
        df["arrival_iata"] = df["arr_iata"]

    if "airline_iata" not in df.columns:
        df["airline_iata"] = "UNK"

    return df


def train_model():
    logger.info("Chargement des données historiques...")

    df_as = load_historical_flights_as()
    df_al = load_historical_flights_al()

    logger.info(f"Aviationstack : {len(df_as)} documents")
    logger.info(f"AirLabs       : {len(df_al)} documents")

    df_al_h = harmonize_airlabs(df_al)

    df_all = pd.concat([df_as, df_al_h], ignore_index=True, sort=False)
    logger.info(f"Total fusionné : {len(df_all)} documents")

    logger.info("Construction du dataset de features...")
    X_train, X_test, y_train, y_test = build_training_dataset(df_all)

    logger.info(f"X_train : {X_train.shape}")
    logger.info(f"X_test  : {X_test.shape}")

    logger.info("Construction du modèle...")
    model = build_model()

    logger.info("Entraînement...")
    model.fit(X_train, y_train)

    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    logger.info(f"R2 train : {r2_score(y_train, y_train_pred):.4f}")
    logger.info(f"R2 test  : {r2_score(y_test, y_test_pred):.4f}")

    logger.info("Sauvegarde du modèle...")
    save_model(model)

    logger.info("OK.")
    return model

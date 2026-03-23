# src/ml/training.py

import logging
from sklearn.metrics import r2_score

from src.utils.mongo import load_historical_flights
from src.ml.features import build_training_dataset
from src.ml.model import build_model, save_model

logger = logging.getLogger(__name__)


def train_model():
    """
    Pipeline complet d'entraînement :
    - chargement des données (Mongo)
    - construction du dataset d'entraînement
    - entraînement du modèle
    - évaluation simple
    - sauvegarde du modèle
    """
    logger.info("Chargement des données historiques...")
    df_raw = load_historical_flights()

    logger.info("Construction du dataset d'entraînement...")
    X_train, X_test, y_train, y_test = build_training_dataset(df_raw)

    logger.info("Construction du modèle...")
    model = build_model()

    logger.info("Entraînement du modèle...")
    model.fit(X_train, y_train)

    logger.info("Évaluation du modèle...")
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    r2_train = r2_score(y_train, y_train_pred)
    r2_test = r2_score(y_test, y_test_pred)

    logger.info(f"R2 train : {r2_train:.4f}")
    logger.info(f"R2 test  : {r2_test:.4f}")

    logger.info("Sauvegarde du modèle...")
    save_model(model)

    logger.info("Entraînement terminé.")
    return model

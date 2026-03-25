import logging
from sklearn.metrics import r2_score

from src.utils.mongo import load_historical_flights
from src.ml.features import build_training_dataset
from src.ml.model import build_model, save_model

logger = logging.getLogger(__name__)


def train_model():
    logger.info("Chargement des données Mongo...")
    docs = load_historical_flights()

    logger.info("Construction du dataset...")
    X_train, X_test, y_train, y_test = build_training_dataset(docs)

    logger.info(f"Taille X_train : {X_train.shape}")
    logger.info(f"Taille X_test  : {X_test.shape}")

    categorical_features = X_train.select_dtypes(include=["object"]).columns.tolist()

    logger.info("Construction du modèle GradientBoosting...")
    model = build_model(categorical_features)

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

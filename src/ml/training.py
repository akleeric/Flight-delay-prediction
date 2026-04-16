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

    logger.info("Construction du modèle ML (ElasticNet)...")
    model = build_model()

    logger.info("Entraînement du modèle...")
    
    # Vérifier les NaN dans X_train (utile pour debug)
    nan_counts = X_train.isna().sum()
    print("\n=== Colonnes contenant des NaN ===")
    print(nan_counts[nan_counts > 0])

    model.fit(X_train, y_train)

    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    logger.info(f"R2 train : {r2_score(y_train, y_train_pred):.4f}")
    logger.info(f"R2 test  : {r2_score(y_test, y_test_pred):.4f}")

    logger.info("Sauvegarde du modèle...")
    save_model(model)

    logger.info("OK.")
    return model

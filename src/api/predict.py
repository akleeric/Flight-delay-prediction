import pandas as pd
from fastapi import HTTPException
from src.api.schemas import FlightBatchInput
from src.ml.model import load_model

# Chargement du modèle une seule fois
try:
    model = load_model()
except Exception as e:
    raise RuntimeError(f"Impossible de charger le modèle ML : {e}")


def predict_batch(data: FlightBatchInput):
    """
    Reçoit un batch de vols déjà featurés,
    exécute la prédiction pour chacun,
    et renvoie une liste de retards prédits.
    """

    try:
        # Conversion en DataFrame
        df = pd.DataFrame([flight.dict() for flight in data.flights])

        # Prédictions
        preds = model.predict(df)

        # Correction métier : pas de retard négatif
        preds = [float(p) if p > 0 else 0.0 for p in preds]

        return {
            "predictions": preds
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la prédiction batch : {str(e)}"
        )

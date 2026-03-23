import pandas as pd
from fastapi import HTTPException
from src.api.schemas import FlightInput
from src.ml.model import load_model

# Chargement du modèle une seule fois au démarrage de l'API
try:
    model = load_model()
except Exception as e:
    raise RuntimeError(f"Impossible de charger le modèle ML : {e}")


def predict_delay(data: FlightInput):
    """
    Reçoit un FlightInput, le transforme en DataFrame,
    exécute la prédiction et renvoie le retard estimé.
    """

    try:
        # Conversion en DataFrame
        df = pd.DataFrame([data.dict()])

        # Prédiction
        prediction = model.predict(df)[0]

        # Conversion float pour JSON
        return {
            "predicted_delay": float(prediction)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la prédiction : {str(e)}"
        )

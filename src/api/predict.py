"""Service de prédiction de retard"""
import joblib
from pathlib import Path
import numpy as np
from typing import Dict, Any

class FlightPredictor:
    """Chargement et utilisation du modèle ML"""
    
    def __init__(self, model_path: str = "data/models/baseline_model.pkl"):
        self.model_path = Path(model_path)
        self.model_data = None
        self.load_model()
    
    def load_model(self):
        """Charge le modèle depuis le disque"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        self.model_data = joblib.load(self.model_path)
        print(f"✓ Model loaded from {self.model_path}")
    
    def predict(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prédiction pour un vol"""
        if not self.model_data:
            raise RuntimeError("Model not loaded")
        
        model = self.model_data['model']
        le_airline = self.model_data['le_airline']
        le_dep = self.model_data['le_dep']
        le_arr = self.model_data['le_arr']
        
        # Encoder les variables catégorielles
        try:
            airline_encoded = le_airline.transform([flight_data['airline_iata']])[0]
        except:
            airline_encoded = 0
        
        try:
            dep_encoded = le_dep.transform([flight_data['departure_airport']])[0]
        except:
            dep_encoded = 0
        
        try:
            arr_encoded = le_arr.transform([flight_data['arrival_airport']])[0]
        except:
            arr_encoded = 0
        
        # Créer le vecteur de features
        is_weekend = 1 if flight_data['day_of_week'] >= 5 else 0
        
        features = np.array([[
            flight_data['scheduled_hour'],
            flight_data['day_of_week'],
            flight_data['month'],
            is_weekend,
            airline_encoded,
            dep_encoded,
            arr_encoded
        ]])
        
        # Prédiction
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0]
        
        delay_prob = probability[1] if len(probability) > 1 else 0.0
        
        if delay_prob > 0.7:
            confidence = "HIGH"
        elif delay_prob > 0.3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return {
            'is_delayed': bool(prediction),
            'delay_probability': float(delay_prob),
            'confidence': confidence,
            'probabilities': {
                'on_time': float(probability[0]),
                'delayed': float(delay_prob)
            }
        }

_predictor = None

def get_predictor():
    """Retourne l'instance du prédicteur"""
    global _predictor
    if _predictor is None:
        _predictor = FlightPredictor()
    return _predictor

#!/usr/bin/env python3
"""Entraînement modèle de base"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import joblib

print("="*60)
print("ENTRAÎNEMENT MODELE DE BASE")
print("="*60)

# Charger les données
df = pd.read_csv('data/processed/flights_features.csv')
print(f"\n✓ Dataset chargé: {len(df)} vols")

# Encoder les variables catégorielles
le_airline = LabelEncoder()
le_dep = LabelEncoder()
le_arr = LabelEncoder()

df['airline_encoded'] = le_airline.fit_transform(df['airline_iata'])
df['dep_encoded'] = le_dep.fit_transform(df['departure_airport'])
df['arr_encoded'] = le_arr.fit_transform(df['arrival_airport'])

# Features pour le modèle
features = [
    'scheduled_hour', 'day_of_week', 'month', 'is_weekend',
    'airline_encoded', 'dep_encoded', 'arr_encoded'
]

X = df[features]
y = df['is_delayed']

print(f"\nFeatures: {features}")
print(f"Distribution target: {y.value_counts().to_dict()}")

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n✓ Train: {len(X_train)}, Test: {len(X_test)}")

# Entraîner avec class_weight pour gérer le déséquilibre
print("\nEntraînement Random Forest...")
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    class_weight='balanced',  # Important pour déséquilibre
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)
print("✓ Modèle entraîné")

# Évaluation
y_pred = model.predict(X_test)

print("\n" + "="*60)
print("RESULTATS")
print("="*60)
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Feature importance
print("\nFeature Importance:")
importances = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(importances)

# Sauvegarder
model_path = Path('data/models/baseline_model.pkl')
model_path.parent.mkdir(parents=True, exist_ok=True)
joblib.dump({
    'model': model,
    'le_airline': le_airline,
    'le_dep': le_dep,
    'le_arr': le_arr,
    'features': features
}, model_path)

print(f"\n Modèle sauvegardé: {model_path}")
print("="*60)

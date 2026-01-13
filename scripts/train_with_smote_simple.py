#!/usr/bin/env python3
"""Entraînement avec SMOTE - Dataset simplifié"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE
import joblib

print("="*70)
print("ENTRAÎNEMENT AVEC SMOTE - DATASET 2294 VOLS")
print("="*70)

print("\n[1/6] Chargement dataset...")
df = pd.read_csv('data/processed/flights_features.csv')
print(f"  {len(df)} vols chargés")

print("\n[2/6] Encodage features...")
le_airline = LabelEncoder()
le_dep = LabelEncoder()
le_arr = LabelEncoder()

df['airline_encoded'] = le_airline.fit_transform(df['airline_iata'].fillna('UNK'))
df['dep_encoded'] = le_dep.fit_transform(df['departure_airport'].fillna('UNK'))
df['arr_encoded'] = le_arr.fit_transform(df['arrival_airport'].fillna('UNK'))

features = [
    'scheduled_hour', 'day_of_week', 'month', 'is_weekend',
    'airline_encoded', 'dep_encoded', 'arr_encoded'
]

X = df[features]
y = df['is_delayed']

print(f"\n  Distribution AVANT SMOTE:")
print(f"    - Classe 0 (à l'heure): {(y == 0).sum()}")
print(f"    - Classe 1 (retard): {(y == 1).sum()}")

print("\n[3/6] Split train/test...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print("\n[4/6]  APPLICATION SMOTE...")
smote = SMOTE(random_state=42, k_neighbors=min(5, (y_train == 1).sum() - 1))
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)

print(f"  Distribution APRÈS SMOTE:")
print(f"    - Classe 0: {(y_train_balanced == 0).sum()}")
print(f"    - Classe 1: {(y_train_balanced == 1).sum()}")
print(f"  Classes équilibrées !")

print("\n[5/6] Entraînement Random Forest...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=4,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train_balanced, y_train_balanced)
print("   Modèle entraîné")

print("\n[6/6] Évaluation...")
y_pred = model.predict(X_test)

print("\n" + "="*70)
print("RÉSULTATS")
print("="*70)

print("\nClassification Report:")
print(classification_report(y_test, y_pred, digits=3))

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(cm)

tn, fp, fn, tp = cm.ravel()
print(f"\nDétail:")
print(f"  True Negatives: {tn} | False Positives: {fp}")
print(f"  False Negatives: {fn} | True Positives: {tp}")

if len(np.unique(y_test)) > 1:
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"\n AUC-ROC Score: {auc_score:.4f}")

print("\nFeature Importance:")
importances = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(importances.to_string(index=False))

print("\n[7/7] Sauvegarde...")
model_path = Path('data/models/smote_model.pkl')
model_path.parent.mkdir(parents=True, exist_ok=True)

joblib.dump({
    'model': model,
    'features': features,
    'encoders': {
        'airline': le_airline,
        'dep': le_dep,
        'arr': le_arr
    },
    'test_accuracy': (y_pred == y_test).mean()
}, model_path)

print(f" Modèle sauvegardé: {model_path}")
print("="*70)

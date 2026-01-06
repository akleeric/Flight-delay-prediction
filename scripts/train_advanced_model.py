#!/usr/bin/env python3
"""Entraînement modèle avancé avec 24 features UML"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib

print("="*70)
print("ENTRAÎNEMENT MODÈLE AVANCÉ - 24 FEATURES UML")
print("="*70)

print("\n[1/7] Chargement dataset enhanced...")
df = pd.read_csv('data/processed/flights_features_enhanced.csv')
print(f"  ✓ Dataset chargé: {len(df)} vols")
print(f"  ✓ Features disponibles: {df.shape[1]} colonnes")

print("\n[2/7] Préparation features...")

le_season = LabelEncoder()
le_time_of_day = LabelEncoder()

df['season_encoded'] = le_season.fit_transform(df['season'])
df['time_of_day_encoded'] = le_time_of_day.fit_transform(df['time_of_day'])

features = [
    'scheduled_hour', 'day_of_week', 'month', 'is_weekend',
    'is_holiday', 'season_encoded', 'time_of_day_encoded',
    'dep_temperature', 'dep_wind_speed', 'dep_visibility',
    'dep_precipitation', 'dep_weather_bad',
    'arr_temperature', 'arr_wind_speed', 'arr_visibility',
    'arr_precipitation', 'arr_weather_bad',
    'flight_distance_km', 'scheduled_duration_min',
    'airline_encoded', 'dep_encoded', 'arr_encoded',
    'airline_avg_delay', 'route_avg_delay',
    'airport_congestion', 'prev_flight_delay'
]

missing_features = [f for f in features if f not in df.columns]
if missing_features:
    print(f"  Features manquantes: {missing_features}")
    features = [f for f in features if f in df.columns]

print(f"  ✓ {len(features)} features sélectionnées")


# Remplir NaN avec valeurs par défaut au lieu de supprimer
df_clean = df[features + ['is_delayed']].copy()
df_clean = df_clean.fillna({
    'airline_avg_delay': 0.0,
    'route_avg_delay': 0.0,
    'airport_congestion': 0.5,
    'prev_flight_delay': 0,
    'flight_distance_km': df_clean['flight_distance_km'].median(),
    'scheduled_duration_min': df_clean['scheduled_duration_min'].median()
})
# Supprimer lignes avec NaN restants (si présents)
df_clean = df_clean.dropna()


print(f"  ✓ {len(df_clean)} vols après suppression NaN")

X = df_clean[features]
y = df_clean['is_delayed']

print(f"\n  Distribution cible:")
print(f"    - Classe 0 (à l'heure): {(y == 0).sum()} ({(y == 0).sum()/len(y)*100:.1f}%)")
print(f"    - Classe 1 (en retard): {(y == 1).sum()} ({(y == 1).sum()/len(y)*100:.1f}%)")

print("\n[3/7] Split train/test...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  ✓ Train: {len(X_train)} vols")
print(f"  ✓ Test: {len(X_test)} vols")

print("\n[4/7] Entraînement Random Forest avancé...")
print("  Configuration:")
print("    - n_estimators: 200 (vs 100 baseline)")
print("    - max_depth: 15 (vs 10 baseline)")
print("    - min_samples_split: 10")
print("    - min_samples_leaf: 4")
print("    - class_weight: balanced")
print("    - random_state: 42")

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=4,
    class_weight='balanced',
    random_state=42,
    n_jobs=-1,
    verbose=1
)

model.fit(X_train, y_train)
print("  ✓ Modèle entraîné")

print("\n[5/7] Validation croisée (5-fold)...")
cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
print(f"  ✓ CV Accuracy: {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")

print("\n[6/7] Évaluation sur test set...")
y_pred = model.predict(X_test)

# Gérer le cas où il n'y a qu'une seule classe
if model.predict_proba(X_test).shape[1] > 1:
    y_pred_proba = model.predict_proba(X_test)[:, 1]
else:
    y_pred_proba = model.predict_proba(X_test)[:, 0]

print("\n" + "="*70)
print("RÉSULTATS")
print("="*70)

print("\nClassification Report:")
print(classification_report(y_test, y_pred, digits=3))

print("\nConfusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(cm)

tn, fp, fn, tp = cm.ravel()
print(f"\nDétail confusion matrix:")
print(f"  - True Negatives (TN): {tn}")
print(f"  - False Positives (FP): {fp}")
print(f"  - False Negatives (FN): {fn}")
print(f"  - True Positives (TP): {tp}")


if len(np.unique(y_test)) > 1 and model.predict_proba(X_test).shape[1] > 1:
    auc_score = roc_auc_score(y_test, y_pred_proba)
    print(f"\n AUC-ROC Score: {auc_score:.4f}")
else:
    print("\n Une seule classe dans les données - AUC-ROC non calculable")


print("\n[7/7] Feature Importance...")

importances = pd.DataFrame({
    'feature': features,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\nTop 10 features:")
print(importances.head(10).to_string(index=False))

importances.to_csv('data/models/feature_importance_advanced.csv', index=False)
print("\n  ✓ Feature importance sauvegardée: data/models/feature_importance_advanced.csv")

print("\n[8/8] Sauvegarde modèle...")

model_path = Path('data/models/advanced_model.pkl')
model_path.parent.mkdir(parents=True, exist_ok=True)

joblib.dump({
    'model': model,
    'features': features,
    'le_season': le_season,
    'le_time_of_day': le_time_of_day,
    'cv_scores': cv_scores,
    'test_accuracy': (y_pred == y_test).mean(),
    'feature_importance': importances.to_dict('records')
}, model_path)

print(f"  ✓ Modèle sauvegardé: {model_path}")

print("\n" + "="*70)
print("COMPARAISON BASELINE vs AVANCE")
print("="*70)

try:
    baseline = joblib.load('data/models/baseline_model.pkl')
    print("\nBaseline (7 features):")
    print("  - Features: scheduled_hour, day_of_week, month, is_weekend, airline, dep, arr")
    print("  - Hyperparams: n_estimators=100, max_depth=10")

    print("\nModèle Avancé (24 features):")
    print("  - Features: 7 temporelles + 10 météo + 3 opérationnelles + 4 agrégées")
    print("  - Hyperparams: n_estimators=200, max_depth=15")
    print(f"  - CV Accuracy: {cv_scores.mean():.2%}")
    print(f"  - Test Accuracy: {(y_pred == y_test).mean():.2%}")

except FileNotFoundError:
    print("  Baseline model non trouvé (comparaison impossible)")

print("\n" + "="*70)
print("RECOMMANDATIONS POUR AMÉLIORATION")
print("="*70)
print("""
1. Enrichir le dataset:
   - Collecter plus de vols en retard (actuellement <2%)
   - Cibler aéroports/périodes à fort taux de retard
   - Utiliser oversampling (SMOTE) sur classe minoritaire

2. Features supplémentaires:
   - Événements spéciaux (grèves, météo extrême)
   - Trafic aérien temps réel
   - Historique avion spécifique (si immatriculation disponible)

3. Modèles alternatifs:
   - Tester XGBoost, LightGBM (meilleurs sur déséquilibre)
   - Réseaux de neurones avec couche d'attention
   - Ensemble de modèles

4. Hyperparameter tuning:
   - GridSearch/RandomSearch sur RF
   - Optimiser seuils de classification
""")

print("="*70)
print("✓ ENTRAÎNEMENT TERMINÉ")
print("="*70)

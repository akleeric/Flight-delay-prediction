#!/usr/bin/env python3
import pandas as pd
import joblib

print("\n" + "="*70)
print(" RÉSULTATS FINAUX - COLLECTE SYNCHRONISEE")
print("="*70)

model = joblib.load('data/models/advanced_model.pkl')

print(f"\n PERFORMANCE:")
print(f"  CV Accuracy: {model['cv_scores'].mean():.2%}")
print(f"  Test Accuracy: {model['test_accuracy']:.2%}")

print(f"\n TOP 10 FEATURES:")
fi = pd.DataFrame(model['feature_importance'])
for i, row in fi.head(10).iterrows():
    icon = "🌤️" if any(x in row['feature'] for x in ['weather','temp','wind','visibility','precipitation']) else "📅"
    print(f"  {icon} {i+1}. {row['feature']:30s} {row['importance']:6.2%}")

df = pd.read_csv('data/processed/flights_features_enhanced.csv')
print(f"\n DATASET: {len(df)} vols, {(df['is_delayed']==1).sum()} retards")

from src.data_processing import get_mongodb_client
client = get_mongodb_client()
meteo = client.db.weather_data.count_documents({})
print(f"  Météo: {meteo} obs")
client.close()

print(f"\n COMPARAISON:")
print(f"  Baseline: 7 features, 98% acc, 25% recall")
print(f"  Avancé: 24 features, {model['test_accuracy']:.1%} acc, 60-70% recall attendu")

print("\n" + "="*70)
print(" TERMINÉ - Prêt pour le rapport !")
print("="*70 + "\n")

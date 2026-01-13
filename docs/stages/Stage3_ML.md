# Stage 3 - Consommation des données et ML

## Date de réalisation
11-13 janvier 2026

## Objectifs atteints

### 1. Collecte de données (3 sources)
-  AviationStack : 1294 vols (historique)
-  Air France-KLM : 1000 vols (temps réel)
-  OpenWeatherMap : 66 observations (synchronisée)
- **Total : 2294 vols**

### 2. Architecture adaptative
- Script unique : `collect_sync.py`
- Détection automatique rate limits
- Basculement intelligent entre sources

### 3. Dataset ML unifié
- Script : `prepare_ml_data.py`
- Format standardisé (13 features)
- Output : `data/processed/flights_features.csv`

### 4. Modèle avec SMOTE
- Problème : Déséquilibre 0.8% retards (18/2294)
- Solution : SMOTE → 1821 vs 1821 classes équilibrées
- Résultats :
  - **AUC-ROC : 0.9890**
  - **Recall retards : 100%**
  - Modèle : `data/models/smote_model.pkl`

## Défis techniques résolus

### Bug API Air France-KLM
- Problème : Header `'API-Key'` vs `'Api-Key'`
- Impact : 0 vols collectés
- Solution : Correction header
- Résultat : 100 vols/collecte 

### Gestion rate limits
- AviationStack : 100 req/mois dépassé
- AF-KLM : 100 req/jour, 1 req/sec
- Solution : Système adaptatif automatique

## Livrables

- 3 collecteurs opérationnels
- 2294 vols collectés
- Dataset ML unifié
- Modèle Random Forest avec SMOTE (AUC 0.99)
- Documentation technique

## Prochaine étape
**Stage 4 : Déploiement** (API + Dashboard)

#  PHASE 2 - MIGRATION VERS ARCHITECTURE COMPLÈTE

##  Vue d'Ensemble

Migration de **Phase 1 (Baseline - 7 features)** vers **Phase 2 (Architecture UML - 24 features)**.

---

## Comparaison

| Composant | Phase 1 | Phase 2 |
|-----------|---------|---------|
| Features | 7 | 24 |
| Base ML | MongoDB + CSV | Snowflake |
| Météo | 0 features | 10 features |
| Agrégées | 0 features | 4 features |
| Modèle | RF (100, depth=10) | RF (200, depth=15) |

---

## Nouveaux Scripts

### 1. feature_calculator.py
**Emplacement:** `src/data_processing/feature_calculator.py`

**Fonction:** Calcule 4 features agrégées
- airline_avg_delay (30 jours)
- route_avg_delay (30 jours)
- airport_congestion (score 0-1.5)
- prev_flight_delay

**Test:**
```bash
cd ~/flight-delay-prediction
python3 src/data_processing/feature_calculator.py
```

---

### 2. collect_weather_continuous.py
**Emplacement:** `scripts/collect_weather_continuous.py`

**Fonction:** Collecte météo automatisée toutes les 30 minutes

**Lancement en background:**
```bash
cd ~/flight-delay-prediction
nohup python3 scripts/collect_weather_continuous.py > logs/weather.log 2>&1 &
```

**Vérifier logs:**
```bash
tail -f logs/weather.log
```

**Arrêter:**
```bash
pkill -f collect_weather_continuous.py
```

---

### 3. enhanced_feature_engineering.py
**Emplacement:** `scripts/enhanced_feature_engineering.py`

**Fonction:** Génère dataset avec 24 features UML

**Exécution:**
```bash
cd ~/flight-delay-prediction
python3 scripts/enhanced_feature_engineering.py
```

**Output:** `data/processed/flights_features_enhanced.csv`

---

### 4. train_advanced_model.py
**Emplacement:** `scripts/train_advanced_model.py`

**Fonction:** Entraîne modèle avec 24 features

**Exécution:**
```bash
cd ~/flight-delay-prediction
python3 scripts/train_advanced_model.py
```

**Outputs:**
- `data/models/advanced_model.pkl`
- `data/models/feature_importance_advanced.csv`

---

## PLANNING MIGRATION

### Janvier-Mars 2026 (Maintenant)
- [x] Créer les 4 scripts Phase 2
- [ ] Lancer collecte météo en background (48h minimum)
- [ ] Tester feature engineering
- [ ] Tester entraînement modèle avancé

### Avril 2026
- [ ] Activer Snowflake
- [ ] Migrer MongoDB → Snowflake
- [ ] Pipeline complet avec 24 features

### Mai 2026
- [ ] Étape 4: Déploiement Docker
- [ ] Étape 5: Airflow + Monitoring
- [ ] Étape 6: Soutenance (25 mai)

---

## AMÉLIORATION ATTENDUE

**Baseline (Phase 1):**
- Accuracy: 98%
- Recall retards: 25% 

**Avancé (Phase 2) - Objectif:**
- Accuracy: 97-99%
- Recall retards: 60-70% 

---

## CHECKLIST

- [x] feature_calculator.py créé
- [x] collect_weather_continuous.py créé
- [x] enhanced_feature_engineering.py créé
- [x] train_advanced_model.py créé
- [ ] Collecte météo lancée (48h+)
- [ ] Dataset enhanced généré
- [ ] Modèle avancé entraîné

---

## DÉPANNAGE

**Erreur: Module not found**
```bash
export PYTHONPATH="${PYTHONPATH}:~/flight-delay-prediction"
```

**Vérifier météo collectée:**
```bash
python3 << 'EOF'
from src.data_processing import get_mongodb_client
client = get_mongodb_client()
print(f"Météo: {client.db.weather_data.count_documents({})}")
client.close()
EOF
```

**Vérifier processus météo:**
```bash
ps aux | grep collect_weather
```

---

**Dernière mise à jour:** 04 Janvier 2026  
**Auteurs:** Brice Eric AKLE - Gaël Joseph FARALAHIMANANA

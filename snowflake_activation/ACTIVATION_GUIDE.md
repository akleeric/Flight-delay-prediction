# GUIDE D'ACTIVATION SNOWFLAKE
**Flight Delay Prediction System - Datascientest 2026**

---

## QUAND UTILISER CE GUIDE ?

**1 MOIS AVANT VOTRE PRÉSENTATION**

Ce guide vous permet d'activer Snowflake et de migrer toutes vos données MongoDB en 30 minutes à 2 heures maximum.

---

##  PRÉREQUIS

Avant de commencer :
-  Système MongoDB fonctionnel avec données collectées
-  Données dans MongoDB (aviationstack_flights, afklm_flights, weather_data)
-  Connexion Internet stable
-  Budget : ~$25-40 pour 1 mois Snowflake (ou essai gratuit)

---

##  ÉTAPE 1 : SOUSCRIRE À SNOWFLAKE (15 minutes)

### Option : Nouveau compte d'essai (Recommandé)

1. **Aller sur** : https://signup.snowflake.com/
2. **Choisir** :
   - Edition: **Standard** (suffisant pour projet)
   - Cloud Provider: **AWS** (recommended)
   - Region: **EU (Frankfurt)** ou **EU (Ireland)** (proche de Paris)
3. **Remplir** :
   - Email (différent si déjà utilisé)
   - Nom
   - Entreprise: "Datascientest Student Project"
4. **Valider email** et **créer mot de passe**

Vous obtenez : **30 jours gratuits + $400 de crédits**

---

## ÉTAPE 2 : RÉCUPÉRER VOS CREDENTIALS (5 minutes)

Une fois connecté à Snowflake :

1. **Account Identifier** :
   - En haut à gauche, cliquer sur votre nom
   - Copier l'URL : https://XXXXXXX.snowflakecomputing.com
   - Votre account = XXXXXXX.eu-west-1 (par exemple)

2. **Créer un User** (si nécessaire) :
   - Admin → Users → Create User
   - Username: votre_nom
   - Password: choisir mot de passe fort

3. **Noter credentials** :
```
   Account: XXXXXXX.eu-west-1
   User: votre_nom
   Password: votre_password
```

---

##  ÉTAPE 3 : CONFIGURER .env (2 minutes)

Sur votre serveur Ubuntu :
```bash
nano ~/flight-delay-prediction/.env
```

**Ajouter** (ou décommenter) :
```bash
# Snowflake
SNOWFLAKE_ACCOUNT=XXXXXXX.eu-west-1
SNOWFLAKE_USER=votre_nom
SNOWFLAKE_PASSWORD=votre_password
SNOWFLAKE_WAREHOUSE=FLIGHT_WH
SNOWFLAKE_DATABASE=FLIGHT_DELAYS_DB
SNOWFLAKE_SCHEMA=RAW_DATA
```

**Sauvegarder** : Ctrl+O → Enter → Ctrl+X

---

##  ÉTAPE 4 : INSTALLER DÉPENDANCES (2 minutes)
```bash
source ~/mon_env/bin/activate
pip install snowflake-connector-python
```

---

##  ÉTAPE 5 : TESTER LA CONNEXION (2 minutes)
```bash
cd ~/flight-delay-prediction/snowflake_activation
python 00_test_snowflake_connection.py
```

**Résultat attendu** :
```
✓ Connexion OK
✓ Warehouse FLIGHT_WH actif
✓ Database accessible
Schemas manquants (normal, on les crée après)
```

**Si erreur** : Vérifier credentials dans .env

---

##  ÉTAPE 6 : CRÉER LA STRUCTURE SNOWFLAKE (5 minutes)

### Via l'interface Web Snowflake (Recommandé)

1. **Se connecter** : https://app.snowflake.com/
2. **Worksheets** → **+ Worksheet**
3. **Copier-coller** le contenu de `01_snowflake_setup.sql`
4. **Run All** (bouton en haut)
5. **Attendre** 2-3 minutes

**Vérification** :
```bash
python 00_test_snowflake_connection.py
```

Maintenant **tous les ✓ doivent être verts** !

---

##  ÉTAPE 7 : MIGRER LES DONNÉES (30 min - 2h selon volume)
```bash
python 02_migrate_to_snowflake.py
```

**Ce qui se passe** :
1. Connexion à MongoDB ✓
2. Extraction de tous les vols ✓
3. Extraction données météo ✓
4. Connexion à Snowflake ✓
5. Insertion données de référence (aéroports, compagnies) ✓
6. Migration vols MongoDB → Snowflake ✓
7. Migration météo MongoDB → Snowflake ✓
8. Logging dans MONITORING.ETL_LOGS ✓

**Progression affichée** :
```
Connexion à MongoDB... ✓
Extraction des vols... ✓
  aviationstack_flights: 8547 vols
Total extrait: 9781 vols

Connexion à Snowflake... ✓
Chargement de 9781 vols...
  Progression: 100/9781
  Progression: 200/9781
  ...
✓ Vols chargés: 9781 insérés, 0 échoués
```

---

##  ÉTAPE 8 : VÉRIFICATION (5 minutes)

### Via interface Snowflake

1. **Se connecter** : https://app.snowflake.com/
2. **Databases** → **FLIGHT_DELAYS_DB** → **RAW_DATA** → **FLIGHTS**
3. **Preview Data**
4. **Vérifier** que vos vols sont là !

### Via SQL
```sql
-- Compter vols
SELECT COUNT(*) FROM FLIGHT_DELAYS_DB.RAW_DATA.FLIGHTS;

-- Vols par compagnie
SELECT * FROM FLIGHT_DELAYS_DB.RAW_DATA.VW_AIRLINE_STATS;

-- Derniers vols
SELECT * FROM FLIGHT_DELAYS_DB.RAW_DATA.VW_FLIGHTS_ENRICHED
ORDER BY flight_date DESC
LIMIT 10;
```

---

##  CHECKLIST FINALE

Avant votre présentation :

- [ ]  Snowflake actif et accessible
- [ ]  Toutes les données migrées
- [ ]  MongoDB continue de fonctionner
- [ ]  API fonctionne
- [ ]  Dashboard fonctionne

---

## ARCHITECTURE FINALE
```
┌─────────────────────────────────────────┐
│        MONGODB (Temps Réel)             │
│  - Collecte continue                    │
└──────────────┬──────────────────────────┘
               ↓ (Migration)
┌─────────────────────────────────────────┐
│        SNOWFLAKE (Data Warehouse)       │
│  - 10 000+ vols historiques             │
│  - Analytics / BI                       │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│            ML & API                     │
└─────────────────────────────────────────┘
```

---

##  TROUBLESHOOTING

### Erreur "Trial period expired"
→ Créer nouveau compte ou souscrire abonnement

### Erreur "Invalid credentials"
→ Vérifier .env (ACCOUNT, USER, PASSWORD)

### Erreur "Database not found"
→ Exécuter 01_snowflake_setup.sql d'abord

### Migration très lente
→ Normal si 10 000+ vols. Compter 1-2h.

---

##  FÉLICITATIONS !

Votre système est maintenant complet avec MongoDB + Snowflake !

**Vous êtes prêt pour votre présentation ! **

---

**Projet** : Flight Delay Prediction - Datascientest 2026
**Équipe** : AKLE BRICE & FARALAHIMANANA GAEL

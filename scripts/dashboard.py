"""Dashboard Streamlit - Flight Delay Prediction v2 (fusion Brice + Gaël)"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Flight Delay Predictor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.title("✈️ Flight Delay Predictor")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["Prédiction", "Prédiction Temps Réel", "Données", "A Propos"]
)

st.sidebar.markdown("---")

try:
    response = requests.get(f"{API_URL}/", timeout=2)
    if response.status_code == 200:
        st.sidebar.success("API Opérationnelle")
    else:
        st.sidebar.error("API Inaccessible")
except:
    st.sidebar.error("API Hors ligne")

# ==========================================
# PAGE 1 : PRÉDICTION MANUELLE
# ==========================================
if page == "Prédiction":
    st.title("Prédiction de Retard de Vol")
    st.markdown("Estimez le retard d'un vol en minutes à partir de ses paramètres de départ.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations du Vol")
        airline = st.text_input("Compagnie aérienne", value="Air France")
        dep_airport = st.selectbox(
            "Aéroport de Départ",
            ["CDG", "ORY", "AMS", "LHR", "JFK", "LAX", "FRA", "BCN", "MAD", "FCO"],
        )
        arr_airport = st.selectbox(
            "Aéroport d'Arrivée",
            ["JFK", "LAX", "LHR", "CDG", "AMS", "FRA", "ORY", "BCN", "MAD", "FCO"],
        )
        duration = st.number_input("Durée prévue du vol (minutes)", min_value=30, max_value=900, value=120)

    with col2:
        st.subheader("Horaires")
        hour = st.slider("Heure de Départ", 0, 23, 14)
        day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        day_of_week = st.select_slider(
            "Jour de la Semaine",
            options=list(range(1, 8)),
            format_func=lambda x: day_names[x - 1],
            value=2
        )
        month = st.slider("Mois", 1, 12, 1)

        st.subheader("Météo (optionnel)")
        dep_temp = st.number_input("Température départ (°C)", value=15.0)
        dep_wind = st.number_input("Vent départ (m/s)", value=5.0)
        arr_temp = st.number_input("Température arrivée (°C)", value=15.0)

    st.markdown("---")

    is_weekend = 1 if day_of_week >= 6 else 0

    if st.button("Prédire le Retard", type="primary"):
        payload = {
            "flights": [{
                "airline_name": airline,
                "departure_iata": dep_airport,
                "arrival_iata": arr_airport,
                "scheduled_hour": hour,
                "day_of_week": day_of_week,
                "month": month,
                "is_weekend": is_weekend,
                "departure_delay_actual": 0.0,
                "departure_delay_estimated": 0.0,
                "arrival_delay_estimated": 0.0,
                "flight_duration_scheduled": float(duration),
                "dep_temperature": dep_temp,
                "dep_wind_speed": dep_wind,
                "dep_visibility": 10000.0,
                "dep_precipitation": 0.0,
                "dep_weather_bad": 0,
                "arr_temperature": arr_temp,
                "arr_wind_speed": 5.0,
                "arr_visibility": 10000.0,
                "arr_precipitation": 0.0,
                "arr_weather_bad": 0
            }]
        }

        try:
            with st.spinner("Analyse en cours..."):
                response = requests.post(f"{API_URL}/predict", json=payload, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    delay = result["predictions"][0]

                    st.markdown("### Résultat de la Prédiction")

                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        if delay > 15:
                            st.metric("Prédiction", "RETARD", delta=f"+{delay:.0f} min")
                        else:
                            st.metric("Prédiction", "À L'HEURE", delta="Ponctuel")
                    with col_m2:
                        st.metric("Retard estimé", f"{delay:.1f} min")
                    with col_m3:
                        if delay > 60:
                            niveau = "🔴 ÉLEVÉ"
                        elif delay > 15:
                            niveau = "🟡 MODÉRÉ"
                        else:
                            niveau = "🟢 FAIBLE"
                        st.metric("Niveau de risque", niveau)

                    # Jauge
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=delay,
                        title={"text": "Retard estimé (minutes)"},
                        gauge={
                            "axis": {"range": [0, 120]},
                            "bar": {"color": "darkblue"},
                            "steps": [
                                {"range": [0, 15], "color": "#2ecc71"},
                                {"range": [15, 60], "color": "#f39c12"},
                                {"range": [60, 120], "color": "#e74c3c"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 15
                            }
                        }
                    ))
                    fig.update_layout(height=350)
                    st.plotly_chart(fig, use_container_width=True)

                    st.info(f"""
                    **Route**: {dep_airport} → {arr_airport}  
                    **Compagnie**: {airline}  
                    **Heure**: {hour:02d}:00  
                    **Jour**: {day_names[day_of_week - 1]}  
                    **Weekend**: {"Oui" if is_weekend else "Non"}
                    """)
                else:
                    st.error(f"Erreur API: {response.status_code} — {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")

# ==========================================
# PAGE 2 : PRÉDICTION TEMPS RÉEL
# ==========================================
elif page == "Prédiction Temps Réel":
    st.title("Prédiction en Temps Réel")
    st.markdown("Lance le pipeline complet : collecte des vols actifs + météo + prédiction.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Relancer la Collecte", use_container_width=True):
            try:
                with st.spinner("Collecte en cours..."):
                    r = requests.post(f"{API_URL}/run/collector", timeout=60)
                    if r.status_code == 200:
                        st.success("Collecte terminée")
                    else:
                        st.error(f"Erreur: {r.text}")
            except Exception as e:
                st.error(f"Erreur: {e}")

    with col2:
        if st.button("Réentraîner le Modèle", use_container_width=True):
            try:
                with st.spinner("Entraînement en cours..."):
                    r = requests.post(f"{API_URL}/run/training", timeout=120)
                    if r.status_code == 200:
                        st.success("Modèle entraîné")
                    else:
                        st.error(f"Erreur: {r.text}")
            except Exception as e:
                st.error(f"Erreur: {e}")

    with col3:
        if st.button("Prédiction Live", type="primary", use_container_width=True):
            try:
                with st.spinner("Pipeline temps réel en cours..."):
                    r = requests.post(f"{API_URL}/run/live_prediction", timeout=60)
                    if r.status_code == 200:
                        result = r.json()
                        st.success("Pipeline terminé")
                        st.code(result.get("output", ""))
                    else:
                        st.error(f"Erreur: {r.text}")
            except Exception as e:
                st.error(f"Erreur: {e}")

    st.markdown("---")
    st.subheader("Données Processed (dernière collecte)")
    try:
        r = requests.get(f"{API_URL}/flights/processed", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                st.dataframe(df.head(20), use_container_width=True)
            else:
                st.info("Aucune donnée processed disponible.")
        else:
            st.warning("Données non disponibles.")
    except Exception as e:
        st.error(f"Erreur: {e}")

# ==========================================
# PAGE 3 : DONNÉES
# ==========================================
elif page == "Données":
    st.title("Données Collectées")

    tab1, tab2 = st.tabs(["Vols Bruts", "Météo Brute"])

    with tab1:
        try:
            r = requests.get(f"{API_URL}/flights/raw", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    st.success(f"{len(data)} vols en base")
                    df = pd.DataFrame(data)
                    st.dataframe(df.head(50), use_container_width=True)
                else:
                    st.json(data)
            else:
                st.warning("Données non disponibles.")
        except Exception as e:
            st.error(f"Erreur: {e}")

    with tab2:
        try:
            r = requests.get(f"{API_URL}/weather/raw", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    st.success(f"{len(data)} observations météo")
                    df = pd.DataFrame(data)
                    st.dataframe(df.head(50), use_container_width=True)
                else:
                    st.json(data)
            else:
                st.warning("Données non disponibles.")
        except Exception as e:
            st.error(f"Erreur: {e}")

# ==========================================
# PAGE 4 : A PROPOS
# ==========================================
elif page == "A Propos":
    st.title("A Propos du Projet")

    st.markdown("""
    ## Flight Delay Prediction System

    ### Le projet
    On s'est posé une question simple : peut-on savoir à l'avance qu'un vol va être en retard ?
    Pour y répondre, on a tout construit de zéro — la collecte des données, le stockage, l'entraînement du modèle, et la mise en production via une API déployée sur AWS.

    ### Ce qu'on a construit
    - Collecte automatique de vols en temps réel via AviationStack et Air France-KLM
    - Données météo intégrées (départ + arrivée) avec correspondance IATA réelle
    - Pipeline ML complet : features engineering → ElasticNet → prédiction en minutes
    - Prédiction temps réel sur vols actifs
    - API REST FastAPI v2.0 déployée sur AWS EC2
    - Ce dashboard Streamlit pour visualiser et interagir avec les résultats

    ### Stack technique
    FastAPI · MongoDB · Scikit-learn (ElasticNet) · Streamlit · Plotly · AviationStack · OpenWeatherMap · Air France-KLM API

    ### Modèle ML
    - **Type** : Régression (ElasticNet) — prédit les minutes de retard
    - **Features** : 21 features (temporelles + météo départ/arrivée + retards estimés + durée)
    - **Cible** : `arrival_delay_actual` — retard réel à l'arrivée en minutes

    ### Ce qu'on ferait ensuite
    Enrichir le dataset sur des périodes de perturbation, tester XGBoost/LightGBM, et connecter Snowflake pour l'analytique avancée.

    ### Projet Datascientest 2026
    **Brice AKLE & Gaël Faralahimanana**
    """)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"""
        **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        **Python**: {sys.version.split()[0]}
        """)
    with col2:
        try:
            r = requests.get(f"{API_URL}/")
            if r.status_code == 200:
                st.success("API v2.0 opérationnelle")
        except:
            st.error("API non accessible")

st.markdown("---")
st.markdown(
    "<div style='text-align: center'>Flight Delay Prediction System v2.0 — Datascientest 2026</div>",
    unsafe_allow_html=True
)

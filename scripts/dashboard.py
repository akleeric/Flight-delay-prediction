"""Dashboard Streamlit - Flight Delay Prediction v2 (fusion Brice + Gaël)"""
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime as dt
from datetime import datetime
import sys

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Flight Delay Predictor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def to_minutes_delay(actual, scheduled):
    try:
        a = dt.fromisoformat(actual.replace("Z", "+00:00"))
        s = dt.fromisoformat(scheduled.replace("Z", "+00:00"))
        return max((a - s).total_seconds() / 60, 0)
    except:
        return 0.0

@st.cache_data(ttl=60)
def load_flights_raw():
    try:
        r = requests.get(f"{API_URL}/flights/raw", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def build_flight_options(flights):
    options = []
    for f in flights:
        dep = f.get("departure", {})
        arr = f.get("arrival", {})
        airline = f.get("airline", {})
        flight = f.get("flight", {})
        dep_iata = dep.get("iata", "?")
        arr_iata = arr.get("iata", "?")
        airline_name = airline.get("name", "?")
        flight_iata = flight.get("iata", "?")
        scheduled = dep.get("scheduled", "")
        scheduled_str = scheduled[:16].replace("T", " ") if scheduled else ""
        label = f"{flight_iata} | {airline_name} | {dep_iata} -> {arr_iata} | {scheduled_str}"
        options.append({"label": label, "flight": f})
    return options

if page == "Prédiction":
    st.title("Prédiction de Retard de Vol")
    st.markdown("Sélectionnez un vol réel en base pour estimer son retard en minutes.")

    flights_raw = load_flights_raw()

    if not flights_raw:
        st.warning("Aucun vol disponible en base. Vérifiez que l'API est opérationnelle.")
        st.stop()

    flight_options = build_flight_options(flights_raw)
    labels = [o["label"] for o in flight_options]

    selected_label = st.selectbox(f"Vols disponibles ({len(labels)})", labels)
    selected_flight = next(o["flight"] for o in flight_options if o["label"] == selected_label)

    dep = selected_flight.get("departure", {})
    arr = selected_flight.get("arrival", {})
    airline_info = selected_flight.get("airline", {})

    dep_iata = dep.get("iata", "")
    arr_iata = arr.get("iata", "")
    airline_name = airline_info.get("name", "")
    scheduled_str = dep.get("scheduled", "")
    actual_str = dep.get("actual", "")
    estimated_str = dep.get("estimated", "")
    arr_scheduled = arr.get("scheduled", "")
    arr_estimated = arr.get("estimated", "")

    try:
        sched_dt = dt.fromisoformat(scheduled_str.replace("Z", "+00:00"))
        hour = sched_dt.hour
        day_of_week = sched_dt.isoweekday()
        month = sched_dt.month
    except:
        hour, day_of_week, month = 12, 1, 1

    departure_delay_actual = to_minutes_delay(actual_str, scheduled_str) if actual_str else 0.0
    departure_delay_estimated = to_minutes_delay(estimated_str, scheduled_str) if estimated_str else 0.0
    arrival_delay_estimated = to_minutes_delay(arr_estimated, arr_scheduled) if arr_estimated and arr_scheduled else 0.0

    try:
        dep_sched_dt = dt.fromisoformat(scheduled_str.replace("Z", "+00:00"))
        arr_sched_dt = dt.fromisoformat(arr_scheduled.replace("Z", "+00:00"))
        duration = max((arr_sched_dt - dep_sched_dt).total_seconds() / 60, 0)
    except:
        duration = 120.0

    is_weekend = 1 if day_of_week >= 6 else 0
    day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Compagnie", airline_name)
    col2.metric("Route", f"{dep_iata} -> {arr_iata}")
    col3.metric("Départ prévu", scheduled_str[:16].replace("T", " ") if scheduled_str else "-")
    col4.metric("Retard départ actuel", f"{departure_delay_actual:.0f} min")

    st.markdown("---")
    st.subheader("Météo (optionnel)")
    mc1, mc2 = st.columns(2)
    with mc1:
        dep_temp = st.number_input("Température départ (°C)", value=15.0)
        dep_wind = st.number_input("Vent départ (m/s)", value=5.0)
    with mc2:
        arr_temp = st.number_input("Température arrivée (°C)", value=15.0)
        arr_wind = st.number_input("Vent arrivée (m/s)", value=5.0)

    st.markdown("---")

    if st.button("Prédire le Retard", type="primary"):
        payload = {
            "flights": [{
                "airline_name": airline_name,
                "departure_iata": dep_iata,
                "arrival_iata": arr_iata,
                "scheduled_hour": hour,
                "day_of_week": day_of_week,
                "month": month,
                "is_weekend": is_weekend,
                "departure_delay_actual": departure_delay_actual,
                "departure_delay_estimated": departure_delay_estimated,
                "arrival_delay_estimated": arrival_delay_estimated,
                "flight_duration_scheduled": float(duration),
                "dep_temperature": dep_temp,
                "dep_wind_speed": dep_wind,
                "dep_visibility": 10000.0,
                "dep_precipitation": 0.0,
                "dep_weather_bad": 0,
                "arr_temperature": arr_temp,
                "arr_wind_speed": arr_wind,
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
                            st.metric("Prédiction", "A L'HEURE", delta="Ponctuel")
                    with col_m2:
                        st.metric("Retard estimé", f"{delay:.1f} min")
                    with col_m3:
                        if delay > 60:
                            niveau = "🔴 ELEVÉ"
                        elif delay > 15:
                            niveau = "🟡 MODÉRÉ"
                        else:
                            niveau = "🟢 FAIBLE"
                        st.metric("Niveau de risque", niveau)

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
Route: {dep_iata} -> {arr_iata} | Compagnie: {airline_name} | Heure: {hour:02d}:00 | Jour: {day_names[day_of_week - 1]} | Durée prévue: {duration:.0f} min
                    """)
                else:
                    st.error(f"Erreur API: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")

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
                    rows = []
                    for f in data:
                        dep = f.get("departure", {})
                        arr = f.get("arrival", {})
                        airline = f.get("airline", {})
                        flight = f.get("flight", {})
                        rows.append({
                            "Vol": flight.get("iata", ""),
                            "Compagnie": airline.get("name", ""),
                            "Départ": dep.get("iata", ""),
                            "Arrivée": arr.get("iata", ""),
                            "Statut": f.get("flight_status", ""),
                            "Programmé": dep.get("scheduled", "")[:16].replace("T", " ") if dep.get("scheduled") else "",
                            "Retard départ": dep.get("delay", "")
                        })
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)
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

elif page == "A Propos":
    st.title("A Propos du Projet")

    st.markdown("""
## Flight Delay Prediction System

### Le projet
On s'est posé une question simple : peut-on savoir à l'avance qu'un vol va être en retard ?
Pour y répondre, on a tout construit de zéro - la collecte des données, le stockage, l'entraînement du modèle, et la mise en production via une API déployée sur AWS.

### Ce qu'on a construit
- Collecte automatique de vols en temps réel via AviationStack et Air France-KLM
- Données météo intégrées (départ + arrivée) avec correspondance IATA réelle
- Pipeline ML complet : features engineering -> ElasticNet -> prédiction en minutes
- Prédiction temps réel sur vols actifs
- API REST FastAPI v2.0 déployée sur AWS EC2
- Dashboard Streamlit pour visualiser et interagir avec les résultats

### Stack technique
FastAPI - MongoDB - Scikit-learn (ElasticNet) - Streamlit - Plotly - AviationStack - OpenWeatherMap - Air France-KLM API

### Modèle ML
- Type : Régression (ElasticNet) - prédit les minutes de retard
- Features : 21 features (temporelles + météo départ/arrivée + retards estimés + durée)
- Cible : arrival_delay_actual - retard réel à l'arrivée en minutes

### Projet Datascientest 2026
Brice AKLE & Gaël Faralahimanana
    """)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Python: {sys.version.split()[0]}")
    with col2:
        try:
            r = requests.get(f"{API_URL}/")
            if r.status_code == 200:
                st.success("API v2.0 opérationnelle")
        except:
            st.error("API non accessible")

st.markdown("---")
st.markdown(
    "<div style='text-align: center'>Flight Delay Prediction System v2.0 - Datascientest 2026</div>",
    unsafe_allow_html=True
)

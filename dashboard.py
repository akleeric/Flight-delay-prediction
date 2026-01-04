"""Dashboard Streamlit - Flight Delay Prediction"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le path pour imports
sys.path.insert(0, str(Path(__file__).parent))

# Configuration de la page
st.set_page_config(
    page_title="Flight Delay Predictor",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de l'API
API_URL = "http://localhost:8000"

# ==========================================
# SIDEBAR - Configuration
# ==========================================

st.sidebar.title("Flight Delay Predictor")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation",
    ["Prédiction", "Statistiques", "Données Collectées", "A propos"]
)

st.sidebar.markdown("---")

# API Status
try:
    response = requests.get(f"{API_URL}/health", timeout=2)
    if response.status_code == 200:
        health = response.json()
        if health['status'] == 'healthy':
            st.sidebar.success("API Opérationnelle")
        else:
            st.sidebar.warning("API Dégradée")
    else:
        st.sidebar.error("API Inaccessible")
except:
    st.sidebar.error("API Hors ligne")

# ==========================================
# PAGE 1 : PRÉDICTION
# ==========================================

if page == "Prédiction":
    st.title("Prédiction de Retard de Vol")
    st.markdown("Prédisez si votre vol sera retardé en fonction des paramètres de départ.")

    # Formulaire de prédiction
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Informations du Vol")
        airline = st.selectbox(
            "Compagnie Aérienne",
            ["AF", "KL", "DL", "BA", "LH", "UA", "AA"],
            help="Code IATA de la compagnie"
        )
        dep_airport = st.selectbox(
            "Aéroport de Départ",
            ["CDG", "ORY", "AMS", "LHR", "JFK", "LAX", "FRA"],
            help="Code IATA de l'aéroport de départ"
        )
        arr_airport = st.selectbox(
            "Aéroport d'Arrivée",
            ["JFK", "LAX", "LHR", "CDG", "AMS", "FRA", "ORY"],
            help="Code IATA de l'aéroport d'arrivée"
        )
    with col2:
        st.subheader("Horaires")
        hour = st.slider(
            "Heure de Départ",
            0, 23, 14,
            help="Heure de départ prévue (0-23)"
        )
        day_names = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        day_of_week = st.select_slider(
            "Jour de la Semaine",
            options=list(range(7)),
            format_func=lambda x: day_names[x],
            value=2
        )
        month = st.slider(
            "Mois",
            1, 12, 1,
            help="Mois de l'année"
        )
    # Bouton de prédiction
    st.markdown("---")
    col_button, col_result = st.columns([1, 3])
    with col_button:
        predict_button = st.button("Prédire le Retard", type="primary", use_container_width=True)
    if predict_button:
        # Préparer la requête
        payload = {
            "airline_iata": airline,
            "departure_airport": dep_airport,
            "arrival_airport": arr_airport,
            "scheduled_hour": hour,
            "day_of_week": day_of_week,
            "month": month
        }
        try:
            with st.spinner("Analyse en cours..."):
                response = requests.post(f"{API_URL}/predict", json=payload)
                if response.status_code == 200:
                    result = response.json()
                    # Affichage du résultat
                    st.markdown("### Résultat de la Prédiction")
                    # Métriques principales
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        if result['is_delayed']:
                            st.metric("Prédiction", "RETARD", delta="Retard prévu")
                        else:
                            st.metric("Prédiction", "À L'HEURE", delta="Vol ponctuel")
                    with col_m2:
                        prob_pct = result['delay_probability'] * 100
                        st.metric("Probabilité de Retard", f"{prob_pct:.1f}%")
                    with col_m3:
                        confidence_color = {
                            "HIGH": "🟢",
                            "MEDIUM": "🟡",
                            "LOW": "🔴"
                        }
                        st.metric("Confiance", f"{confidence_color.get(result['confidence'], '⚪')} {result['confidence']}")
                    # Graphique de probabilité
                    st.markdown("### Distribution des Probabilités")
                    prob_data = result['flight_info']['probabilities']
                    fig = go.Figure(data=[
                        go.Bar(
                            x=['À l\'heure', 'Retardé'],
                            y=[prob_data['on_time'], prob_data['delayed']],
                            marker_color=['green', 'red'],
                            text=[f"{prob_data['on_time']:.1%}", f"{prob_data['delayed']:.1%}"],
                            textposition='auto',
                        )
                    ])
                    fig.update_layout(
                        title="Probabilités de Retard",
                        yaxis_title="Probabilité",
                        showlegend=False,
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    # Détails du vol
                    st.markdown("### Détails du Vol")
                    info = result['flight_info']
                    st.info(f"""
                    **Route**: {info['route']}
                    **Compagnie**: {info['airline']}
                    **Heure de Départ**: {info['departure_time']}
                    **Weekend**: {'Oui' if info['is_weekend'] else 'Non'}
                    """)
                else:
                    st.error(f"Erreur API: {response.status_code}")
        except Exception as e:
            st.error(f"Erreur de connexion: {e}")
            st.info("Assurez-vous que l'API est lancée sur le port 8000")

# ==========================================
# PAGE 2 : STATISTIQUES
# ==========================================

elif page == "Statistiques":
    st.title("Statistiques de l'API")
    try:
        # Récupérer les stats
        stats_response = requests.get(f"{API_URL}/stats")
        if stats_response.status_code == 200:
            stats = stats_response.json()
            # Métriques principales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Vols Collectés",
                    f"{stats['total_flights']:,}",
                    help="Nombre total de vols dans la base"
                )
            with col2:
                st.metric(
                    "Données Météo",
                    f"{stats['total_weather']:,}",
                    help="Nombre de relevés météo"
                )
            with col3:
                if stats['last_update']:
                    st.metric(
                        "Dernière Mise à Jour",
                        stats['last_update'][:10] if len(stats['last_update']) > 10 else stats['last_update']
                    )
                else:
                    st.metric("Dernière Mise à Jour", "N/A")
            # Graphique de progression
            st.markdown("### Progression de la Collecte")
            # Simulation de progression (vous pouvez améliorer avec vraies données)
            progress_data = pd.DataFrame({
                'Catégorie': ['Vols', 'Météo'],
                'Nombre': [stats['total_flights'], stats['total_weather']]
            })

            fig = px.bar(
                progress_data,
                x='Catégorie',
                y='Nombre',
                color='Catégorie',
                title='Données Collectées par Type'
            )
            st.plotly_chart(fig, use_container_width=True) 
        else:
            st.error("Impossible de récupérer les statistiques")
    except Exception as e:
        st.error(f"Erreur: {e}")

# ==========================================
# PAGE 3 : DONNÉES COLLECTÉES
# ==========================================

elif page == "Données Collectées":
    st.title("Analyse des Données Collectées")
    # Charger les données du CSV
    try:
        df = pd.read_csv('data/processed/flights_features.csv')
        st.success(f"Dataset chargé: {len(df)} vols")
        # Onglets
        tab1, tab2, tab3 = st.tabs(["Vue d'Ensemble", "Par Aéroport", "Par Compagnie"])
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vols", f"{len(df):,}")
            with col2:
                delayed = df[df['is_delayed'] == 1]
                st.metric("Vols Retardés", f"{len(delayed):,}", f"{len(delayed)/len(df)*100:.1f}%")
            with col3:
                st.metric("Retard Moyen", f"{df['delay_minutes'].mean():.1f} min")
            # Distribution des statuts
            st.markdown("### Distribution des Statuts")
            status_counts = df['status'].value_counts()
            fig = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Répartition des Statuts de Vol"
            )
            st.plotly_chart(fig, use_container_width=True)
            # Distribution par jour de semaine
            st.markdown("### Vols par Jour de la Semaine")
            day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            dow_counts = df['day_of_week'].value_counts().sort_index()

            fig = px.bar(
                x=[day_names[i] for i in dow_counts.index],
                y=dow_counts.values,
                labels={'x': 'Jour', 'y': 'Nombre de vols'},
                title="Distribution par Jour de Semaine"
            )
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown("### Top Aéroports de Départ")
            airport_stats = df['departure_airport'].value_counts().head(10)
            fig = px.bar(
                x=airport_stats.values,
                y=airport_stats.index,
                orientation='h',
                labels={'x': 'Nombre de vols', 'y': 'Aéroport'},
                title="Top 10 Aéroports"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tableau détaillé
            st.markdown("### Détails par Aéroport")
            airport_df = df.groupby('departure_airport').agg({
                'flight_iata': 'count',
                'is_delayed': 'sum',
                'delay_minutes': 'mean'
            }).rename(columns={
                'flight_iata': 'Nombre de vols',
                'is_delayed': 'Vols retardés',
                'delay_minutes': 'Retard moyen (min)'
            }).round(2)

            st.dataframe(airport_df.sort_values('Nombre de vols', ascending=False))

        with tab3:
            st.markdown("### Top Compagnies Aériennes")

            airline_stats = df['airline_name'].value_counts().head(10)

            fig = px.bar(
                x=airline_stats.values,
                y=airline_stats.index,
                orientation='h',
                labels={'x': 'Nombre de vols', 'y': 'Compagnie'},
                title="Top 10 Compagnies"
            )
            st.plotly_chart(fig, use_container_width=True)

    except FileNotFoundError:
        st.warning("Aucune donnée disponible. Lancez d'abord la collecte de données.")
    except Exception as e:
        st.error(f"Erreur: {e}")

# ==========================================
# PAGE 4 : A PROPOS
# ==========================================

elif page == "A propos":
    st.title("A Propos du Projet")

    st.markdown("""
    ## Flight Delay Prediction System
    ### Description
    Système complet de prédiction de retards de vols utilisant le Machine Learning.

    ### Technologies Utilisées
    - **Backend**: FastAPI
    - **Base de données**: MongoDB
    - **Machine Learning**: Scikit-learn (Random Forest)
    - **Dashboard**: Streamlit
    - **Visualisation**: Plotly
    - **APIs**: AviationStack, OpenWeatherMap, Air France-KLM

    ### Fonctionnalités
    - Collecte de données en temps réel
    - Prédiction de retards avec ML
    - API REST complète
    - Dashboard interactif
    - Statistiques en temps réel

    ### Projet Datascientest 2026
    Développé par: **Akle & Gaël**

    ### Performances du Modèle
    - **Accuracy**: 98%
    - **Feature la plus importante**: Jour de la semaine (31%)
    - **Dataset**: 1,500+ vols collectés

    ### Architecture
```
    Data Collection → MongoDB → ML Model → FastAPI → Streamlit
```
    """)

    # Informations système
    st.markdown("---")
    st.markdown("### Informations Système")

    col1, col2 = st.columns(2)

    with col1:
        st.info(f"""
        **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        **Python Version**: {sys.version.split()[0]}
        **Streamlit Version**: {st.__version__}
        """)

    with col2:
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                health = response.json()
                st.success(f"""
                **API Status**: {health['status']}
                **Model Loaded**: {'✅' if health['model_loaded'] else '❌'}  
                **DB Connected**: {'✅' if health['database_connected'] else '❌'}
                """)
        except:
            st.error("API non accessible")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center'>Flight Delay Prediction System - Datascientest 2026</div>",
    unsafe_allow_html=True
)

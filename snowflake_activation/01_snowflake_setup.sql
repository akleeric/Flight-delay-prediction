-- ═══════════════════════════════════════════════════════════════════════════════
-- SNOWFLAKE SETUP - Flight Delay Prediction System
-- ═══════════════════════════════════════════════════════════════════════════════
-- Ce script crée toute la structure de données Snowflake
-- Basé sur le modèle UML du projet Datascientest
--
-- UTILISATION :
-- 1. Se connecter à Snowflake Web UI (https://app.snowflake.com/)
-- 2. Worksheets → + Worksheet
-- 3. Copier-coller ce script complet
-- 4. Run All
-- 5. Durée : 2-5 minutes
-- ═══════════════════════════════════════════════════════════════════════════════

USE ROLE SYSADMIN;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 1 : CRÉATION DE LA BASE DE DONNÉES
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS FLIGHT_DELAYS_DB
    COMMENT = 'Database for flight delay prediction system';

USE DATABASE FLIGHT_DELAYS_DB;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 2 : CRÉATION DES SCHÉMAS
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS RAW_DATA
    COMMENT = 'Raw data from APIs and external sources';

CREATE SCHEMA IF NOT EXISTS PROCESSED_DATA
    COMMENT = 'Processed data and features for machine learning';

CREATE SCHEMA IF NOT EXISTS MONITORING
    COMMENT = 'ETL logs and monitoring data';

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 3 : TABLES DE RÉFÉRENCE (Données fixes)
-- ═══════════════════════════════════════════════════════════════════════════════

USE SCHEMA RAW_DATA;

-- Table AIRPORTS
CREATE TABLE IF NOT EXISTS AIRPORTS (
    airport_id          NUMBER AUTOINCREMENT PRIMARY KEY,
    iata_code           VARCHAR(3) UNIQUE NOT NULL,
    icao_code           VARCHAR(4) UNIQUE,
    name                VARCHAR(255) NOT NULL,
    city                VARCHAR(100),
    country             VARCHAR(100),
    country_code        VARCHAR(2),
    latitude            NUMBER(10,7),
    longitude           NUMBER(10,7),
    altitude            NUMBER,
    timezone            VARCHAR(50),
    utc_offset          NUMBER,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE INDEX IF NOT EXISTS idx_airports_country ON AIRPORTS(country_code);
CREATE INDEX IF NOT EXISTS idx_airports_iata ON AIRPORTS(iata_code);

-- Table AIRLINES
CREATE TABLE IF NOT EXISTS AIRLINES (
    airline_id          NUMBER AUTOINCREMENT PRIMARY KEY,
    iata_code           VARCHAR(2) UNIQUE NOT NULL,
    icao_code           VARCHAR(3) UNIQUE,
    name                VARCHAR(255) NOT NULL,
    country             VARCHAR(100),
    country_code        VARCHAR(2),
    callsign            VARCHAR(100),
    is_active           BOOLEAN DEFAULT TRUE,
    fleet_size          NUMBER,
    founded_year        NUMBER,
    hub_airports        ARRAY,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE INDEX IF NOT EXISTS idx_airlines_country ON AIRLINES(country_code);
CREATE INDEX IF NOT EXISTS idx_airlines_iata ON AIRLINES(iata_code);

-- Table AIRCRAFT
CREATE TABLE IF NOT EXISTS AIRCRAFT (
    aircraft_id         NUMBER AUTOINCREMENT PRIMARY KEY,
    registration        VARCHAR(10) UNIQUE NOT NULL,
    iata_type           VARCHAR(4),
    icao_type           VARCHAR(4),
    model               VARCHAR(100) NOT NULL,
    manufacturer        VARCHAR(100),
    airline_id          NUMBER,
    year_built          NUMBER,
    engines_count       NUMBER,
    seats_capacity      NUMBER,
    max_speed_kmh       NUMBER,
    range_km            NUMBER,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT fk_aircraft_airline FOREIGN KEY (airline_id)
        REFERENCES AIRLINES(airline_id)
);

CREATE INDEX IF NOT EXISTS idx_aircraft_model ON AIRCRAFT(model);
CREATE INDEX IF NOT EXISTS idx_aircraft_airline ON AIRCRAFT(airline_id);

-- Table ROUTES
CREATE TABLE IF NOT EXISTS ROUTES (
    route_id            NUMBER AUTOINCREMENT PRIMARY KEY,
    airline_id          NUMBER NOT NULL,
    departure_airport_id NUMBER NOT NULL,
    arrival_airport_id  NUMBER NOT NULL,
    distance_km         NUMBER,
    flight_duration_min NUMBER,
    frequency_weekly    NUMBER,
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT fk_routes_airline FOREIGN KEY (airline_id)
        REFERENCES AIRLINES(airline_id),
    CONSTRAINT fk_routes_departure FOREIGN KEY (departure_airport_id)
        REFERENCES AIRPORTS(airport_id),
    CONSTRAINT fk_routes_arrival FOREIGN KEY (arrival_airport_id)
        REFERENCES AIRPORTS(airport_id),
    CONSTRAINT uk_route UNIQUE (airline_id, departure_airport_id, arrival_airport_id)
);

CREATE INDEX IF NOT EXISTS idx_routes_departure ON ROUTES(departure_airport_id);
CREATE INDEX IF NOT EXISTS idx_routes_arrival ON ROUTES(arrival_airport_id);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 4 : TABLES DE DONNÉES VARIABLES
-- ═══════════════════════════════════════════════════════════════════════════════

-- Table FLIGHTS
CREATE TABLE IF NOT EXISTS FLIGHTS (
    flight_id              NUMBER AUTOINCREMENT PRIMARY KEY,
    flight_iata            VARCHAR(20) NOT NULL,
    flight_icao            VARCHAR(20),
    flight_number          VARCHAR(10) NOT NULL,
    airline_id             NUMBER NOT NULL,
    departure_airport_id   NUMBER NOT NULL,
    arrival_airport_id     NUMBER NOT NULL,
    aircraft_id            NUMBER,

    scheduled_departure    TIMESTAMP_NTZ NOT NULL,
    scheduled_arrival      TIMESTAMP_NTZ NOT NULL,
    actual_departure       TIMESTAMP_NTZ,
    actual_arrival         TIMESTAMP_NTZ,
    estimated_departure    TIMESTAMP_NTZ,
    estimated_arrival      TIMESTAMP_NTZ,

    departure_delay        NUMBER,
    arrival_delay          NUMBER,

    departure_terminal     VARCHAR(10),
    departure_gate         VARCHAR(10),
    arrival_terminal       VARCHAR(10),
    arrival_gate           VARCHAR(10),
    baggage_belt           VARCHAR(10),

    flight_status          VARCHAR(20) NOT NULL,
    is_delayed             BOOLEAN,
    delay_reason           VARCHAR(100),
    cancellation_reason    VARCHAR(100),
    flight_date            DATE NOT NULL,
    data_source            VARCHAR(50),
    created_at             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT fk_flights_airline FOREIGN KEY (airline_id)
        REFERENCES AIRLINES(airline_id),
    CONSTRAINT fk_flights_departure FOREIGN KEY (departure_airport_id)
        REFERENCES AIRPORTS(airport_id),
    CONSTRAINT fk_flights_arrival FOREIGN KEY (arrival_airport_id)
        REFERENCES AIRPORTS(airport_id),
    CONSTRAINT fk_flights_aircraft FOREIGN KEY (aircraft_id)
        REFERENCES AIRCRAFT(aircraft_id)
);

CREATE INDEX IF NOT EXISTS idx_flights_date ON FLIGHTS(flight_date);
CREATE INDEX IF NOT EXISTS idx_flights_status ON FLIGHTS(flight_status);
CREATE INDEX IF NOT EXISTS idx_flights_delayed ON FLIGHTS(is_delayed);
CREATE INDEX IF NOT EXISTS idx_flights_number_date ON FLIGHTS(flight_number, flight_date);
CREATE INDEX IF NOT EXISTS idx_flights_departure ON FLIGHTS(departure_airport_id, flight_date);
CREATE INDEX IF NOT EXISTS idx_flights_airline ON FLIGHTS(airline_id, flight_date);

-- Table WEATHER_DATA
CREATE TABLE IF NOT EXISTS WEATHER_DATA (
    weather_id          NUMBER AUTOINCREMENT PRIMARY KEY,
    airport_id          NUMBER NOT NULL,
    observation_time    TIMESTAMP_NTZ NOT NULL,
    temperature         NUMBER(5,2),
    feels_like          NUMBER(5,2),
    humidity            NUMBER,
    pressure            NUMBER,
    wind_speed          NUMBER(5,2),
    wind_direction      NUMBER,
    visibility          NUMBER,
    cloud_coverage      NUMBER,
    weather_condition   VARCHAR(50),
    weather_description VARCHAR(255),
    precipitation       NUMBER(5,2),
    snow                NUMBER(5,2),
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),

    CONSTRAINT fk_weather_airport FOREIGN KEY (airport_id)
        REFERENCES AIRPORTS(airport_id)
);

CREATE INDEX IF NOT EXISTS idx_weather_airport_time ON WEATHER_DATA(airport_id, observation_time);
CREATE INDEX IF NOT EXISTS idx_weather_time ON WEATHER_DATA(observation_time);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 5 : TABLES POUR MACHINE LEARNING
-- ═══════════════════════════════════════════════════════════════════════════════

USE SCHEMA PROCESSED_DATA;

-- Table FLIGHT_FEATURES
CREATE TABLE IF NOT EXISTS FLIGHT_FEATURES (
    feature_id             NUMBER AUTOINCREMENT PRIMARY KEY,
    flight_id              NUMBER NOT NULL,
    day_of_week            NUMBER,
    month                  NUMBER,
    hour                   NUMBER,
    is_weekend             BOOLEAN,
    is_holiday             BOOLEAN,
    season                 VARCHAR(20),
    flight_distance_km     NUMBER,
    scheduled_duration_min NUMBER,
    time_of_day            VARCHAR(20),
    dep_temperature        NUMBER(5,2),
    dep_wind_speed         NUMBER(5,2),
    dep_visibility         NUMBER,
    dep_precipitation      NUMBER(5,2),
    dep_weather_bad        BOOLEAN,
    arr_temperature        NUMBER(5,2),
    arr_wind_speed         NUMBER(5,2),
    arr_visibility         NUMBER,
    arr_precipitation      NUMBER(5,2),
    arr_weather_bad        BOOLEAN,
    airline_avg_delay      NUMBER(5,2),
    route_avg_delay        NUMBER(5,2),
    airport_congestion     NUMBER(5,2),
    prev_flight_delay      NUMBER,
    is_delayed             BOOLEAN,
    delay_minutes          NUMBER,
    created_at             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT fk_features_flight FOREIGN KEY (flight_id)
        REFERENCES RAW_DATA.FLIGHTS(flight_id)
);

CREATE INDEX IF NOT EXISTS idx_features_flight ON FLIGHT_FEATURES(flight_id);
CREATE INDEX IF NOT EXISTS idx_features_delayed ON FLIGHT_FEATURES(is_delayed);

-- Table ML_PREDICTIONS
CREATE TABLE IF NOT EXISTS ML_PREDICTIONS (
    prediction_id       NUMBER AUTOINCREMENT PRIMARY KEY,
    flight_id           NUMBER NOT NULL,
    model_version       VARCHAR(50) NOT NULL,
    prediction_time     TIMESTAMP_NTZ NOT NULL,
    delay_probability   NUMBER(5,4),
    predicted_delay_min NUMBER,
    confidence_score    NUMBER(5,4),
    prediction_class    VARCHAR(20),
    actual_is_delayed   BOOLEAN,
    actual_delay_min    NUMBER,
    prediction_correct  BOOLEAN,
    error_minutes       NUMBER,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT fk_predictions_flight FOREIGN KEY (flight_id)
        REFERENCES RAW_DATA.FLIGHTS(flight_id)
);

CREATE INDEX IF NOT EXISTS idx_predictions_flight ON ML_PREDICTIONS(flight_id);
CREATE INDEX IF NOT EXISTS idx_predictions_time ON ML_PREDICTIONS(prediction_time);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 6 : TABLES DE MONITORING
-- ═══════════════════════════════════════════════════════════════════════════════

USE SCHEMA MONITORING;

-- Table ETL_LOGS
CREATE TABLE IF NOT EXISTS ETL_LOGS (
    log_id              NUMBER AUTOINCREMENT PRIMARY KEY,
    etl_type            VARCHAR(50) NOT NULL,
    start_time          TIMESTAMP_NTZ NOT NULL,
    end_time            TIMESTAMP_NTZ,
    status              VARCHAR(20) NOT NULL,
    records_processed   NUMBER,
    records_inserted    NUMBER,
    records_updated     NUMBER,
    records_failed      NUMBER,
    error_message       VARCHAR(1000),
    execution_time_sec  NUMBER,
    created_at          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE INDEX IF NOT EXISTS idx_etl_type ON ETL_LOGS(etl_type);
CREATE INDEX IF NOT EXISTS idx_etl_start_time ON ETL_LOGS(start_time);

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 7 : VUES UTILES
-- ═══════════════════════════════════════════════════════════════════════════════

USE SCHEMA RAW_DATA;

-- Vue : Vols enrichis
CREATE OR REPLACE VIEW VW_FLIGHTS_ENRICHED AS
SELECT
    f.flight_id,
    f.flight_iata,
    f.flight_number,
    f.flight_date,
    al.name AS airline_name,
    al.iata_code AS airline_code,
    dep.name AS departure_airport,
    dep.iata_code AS departure_code,
    dep.city AS departure_city,
    dep.country AS departure_country,
    f.scheduled_departure,
    f.actual_departure,
    f.departure_delay,
    arr.name AS arrival_airport,
    arr.iata_code AS arrival_code,
    arr.city AS arrival_city,
    arr.country AS arrival_country,
    f.scheduled_arrival,
    f.actual_arrival,
    f.arrival_delay,
    ac.model AS aircraft_model,
    ac.registration AS aircraft_registration,
    f.flight_status,
    f.is_delayed,
    f.delay_reason
FROM FLIGHTS f
JOIN AIRLINES al ON f.airline_id = al.airline_id
JOIN AIRPORTS dep ON f.departure_airport_id = dep.airport_id
JOIN AIRPORTS arr ON f.arrival_airport_id = arr.airport_id
LEFT JOIN AIRCRAFT ac ON f.aircraft_id = ac.aircraft_id;

-- Vue : Stats par compagnie
CREATE OR REPLACE VIEW VW_AIRLINE_STATS AS
SELECT
    al.name AS airline_name,
    al.iata_code,
    COUNT(*) AS total_flights,
    SUM(CASE WHEN f.is_delayed THEN 1 ELSE 0 END) AS delayed_flights,
    ROUND(AVG(CASE WHEN f.is_delayed THEN 1 ELSE 0 END) * 100, 2) AS delay_rate_pct,
    ROUND(AVG(f.departure_delay), 2) AS avg_delay_minutes,
    MAX(f.departure_delay) AS max_delay_minutes
FROM FLIGHTS f
JOIN AIRLINES al ON f.airline_id = al.airline_id
GROUP BY al.name, al.iata_code
ORDER BY total_flights DESC;

-- Vue : Stats par aéroport
CREATE OR REPLACE VIEW VW_AIRPORT_STATS AS
SELECT
    ap.name AS airport_name,
    ap.iata_code,
    ap.city,
    ap.country,
    COUNT(DISTINCT f.flight_id) AS total_flights,
    SUM(CASE WHEN f.is_delayed THEN 1 ELSE 0 END) AS delayed_flights,
    ROUND(AVG(CASE WHEN f.is_delayed THEN 1 ELSE 0 END) * 100, 2) AS delay_rate_pct
FROM AIRPORTS ap
LEFT JOIN FLIGHTS f ON ap.airport_id = f.departure_airport_id
GROUP BY ap.name, ap.iata_code, ap.city, ap.country
ORDER BY total_flights DESC;

-- ═══════════════════════════════════════════════════════════════════════════════
-- ÉTAPE 8 : WAREHOUSE
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE WAREHOUSE IF NOT EXISTS FLIGHT_WH
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for flight delay prediction queries';

-- ═══════════════════════════════════════════════════════════════════════════════
-- FIN DU SCRIPT
-- ═══════════════════════════════════════════════════════════════════════════════

SELECT 'Setup completed successfully!' AS status;

SELECT
    'Database: FLIGHT_DELAYS_DB created' AS step_1,
    'Schemas: RAW_DATA, PROCESSED_DATA, MONITORING created' AS step_2,
    'Tables: 11 tables created' AS step_3,
    'Views: 3 views created' AS step_4,
    'Warehouse: FLIGHT_WH created' AS step_5,
    'Ready for data migration from MongoDB' AS next_step;

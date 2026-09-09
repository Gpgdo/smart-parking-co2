-- Schema do banco do projeto Smart Parking CO2
-- Executado automaticamente pelo container Postgres na primeira inicialização
-- (docker-entrypoint-initdb.d) e também pelo script src/load_to_db.py.

CREATE TABLE IF NOT EXISTS parking_readings (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP NOT NULL,
    weekday VARCHAR(20) NOT NULL,
    vehicle_flow INTEGER NOT NULL,
    co2_ideal DOUBLE PRECISION NOT NULL,
    co2_sensor DOUBLE PRECISION NOT NULL,
    co2_filtered DOUBLE PRECISION NOT NULL,
    co2_activity DOUBLE PRECISION NOT NULL,
    UNIQUE ("timestamp")
);

CREATE INDEX IF NOT EXISTS idx_parking_readings_timestamp
    ON parking_readings ("timestamp");

CREATE TABLE IF NOT EXISTS co2_peaks (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP NOT NULL,
    weekday VARCHAR(20) NOT NULL,
    co2_filtered DOUBLE PRECISION NOT NULL,
    prominence DOUBLE PRECISION NOT NULL,
    UNIQUE ("timestamp")
);

CREATE INDEX IF NOT EXISTS idx_co2_peaks_timestamp
    ON co2_peaks ("timestamp");

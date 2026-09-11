-- Schema do banco do projeto Smart Parking CO2
-- Executado automaticamente pelo container Postgres na primeira inicialização
-- (docker-entrypoint-initdb.d) e também pelo script src/load_to_db.py.
--
-- A partir da troca para o dataset público real (UCI "Occupancy Detection",
-- Candanedo & Feldheim, 2016), "occupancy" (0/1, ocupação real medida por
-- foto) substitui o antigo "vehicle_flow" simulado, e "co2_ideal" (que só
-- existia porque o CO2 era gerado por nós) deixou de existir.

CREATE TABLE IF NOT EXISTS parking_readings (
    id SERIAL PRIMARY KEY,
    "timestamp" TIMESTAMP NOT NULL,
    weekday VARCHAR(20) NOT NULL,
    occupancy INTEGER NOT NULL,
    co2_sensor DOUBLE PRECISION NOT NULL,
    co2_filtered DOUBLE PRECISION NOT NULL,
    co2_activity DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    light DOUBLE PRECISION,
    humidity_ratio DOUBLE PRECISION,
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

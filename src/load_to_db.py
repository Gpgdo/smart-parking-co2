"""
Carrega os resultados do processamento de sinais (data/processed_simulation.csv
e data/co2_peaks.csv) para o PostgreSQL.

Uso:
    python src/load_to_db.py

Pré-requisitos:
    1. Postgres rodando (docker compose up -d)
    2. src/simulation.py e src/signal_processing.py já executados,
       gerando os arquivos CSV em data/
"""

from pathlib import Path

import pandas as pd

from db import get_connection

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
schema_file = base_dir / "db" / "schema.sql"


def criar_schema(conn):
    sql = schema_file.read_text(encoding="utf-8")

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()

    print("Schema garantido (tabelas criadas caso não existissem).")


def carregar_leituras(conn):
    arquivo = data_dir / "processed_simulation.csv"

    if not arquivo.exists():
        raise FileNotFoundError(
            f"{arquivo} não encontrado. Rode src/simulation.py e "
            "src/signal_processing.py antes de carregar o banco."
        )

    df = pd.read_csv(arquivo, parse_dates=["timestamp"])

    colunas = [
        "timestamp",
        "weekday",
        "vehicle_flow",
        "co2_ideal",
        "co2_sensor",
        "co2_filtered",
        "co2_activity",
    ]

    registros = list(df[colunas].itertuples(index=False, name=None))

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE parking_readings RESTART IDENTITY;")

        with cur.copy(
            "COPY parking_readings "
            "(timestamp, weekday, vehicle_flow, co2_ideal, "
            "co2_sensor, co2_filtered, co2_activity) FROM STDIN"
        ) as copy:
            for registro in registros:
                copy.write_row(registro)

    conn.commit()

    print(f"{len(registros)} leituras carregadas em parking_readings.")


def carregar_picos(conn):
    arquivo = data_dir / "co2_peaks.csv"

    if not arquivo.exists():
        print("Nenhum arquivo de picos encontrado (data/co2_peaks.csv), pulando.")
        return

    df = pd.read_csv(arquivo, parse_dates=["timestamp"])

    colunas = ["timestamp", "weekday", "co2_filtered", "prominence"]

    registros = list(df[colunas].itertuples(index=False, name=None))

    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE co2_peaks RESTART IDENTITY;")

        with cur.copy(
            "COPY co2_peaks (timestamp, weekday, co2_filtered, prominence) "
            "FROM STDIN"
        ) as copy:
            for registro in registros:
                copy.write_row(registro)

    conn.commit()

    print(f"{len(registros)} picos carregados em co2_peaks.")


def main():
    conn = get_connection()

    try:
        criar_schema(conn)
        carregar_leituras(conn)
        carregar_picos(conn)
    finally:
        conn.close()

    print()
    print("Carga no PostgreSQL concluída com sucesso.")


if __name__ == "__main__":
    main()

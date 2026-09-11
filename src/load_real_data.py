"""
Carrega o dataset público real de CO2 x ocupação (substitui o antigo
simulador em src/simulation.py como fonte de dados do pipeline).

Fonte: UCI Machine Learning Repository - "Occupancy Detection Data Set"
CANDANEDO, L. M.; FELDHEIM, V. Accurate occupancy detection of an office
room from light, temperature, humidity and CO2 measurements using
statistical learning models. Energy and Buildings, v. 112, p. 28-39, 2016.

O dataset traz leituras reais de CO2 (ppm), a cada ~1 minuto, de uma sala
de escritório, junto com a ocupação real (0/1) obtida por fotos com
timestamp. Não é um estacionamento real (não existe dataset público de
CO2 em estacionamento), mas é o mesmo princípio físico usado no projeto:
CO2 como indicador indireto de ocupação/movimentação em um ambiente
fechado - só que agora com sensor e ocupação reais, não simulados.

Uso:
    python src/load_real_data.py

Os arquivos brutos ficam em data/raw/ (baixados uma vez; o script baixa
sozinho se não encontrar os arquivos).
"""

import sys
import urllib.request
from pathlib import Path

import pandas as pd

# Evita UnicodeEncodeError ao imprimir "CO₂" em consoles Windows (cp1252)
sys.stdout.reconfigure(encoding="utf-8")

base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
raw_dir = data_dir / "raw"

BASE_URL = (
    "https://raw.githubusercontent.com/LuisM78/Occupancy-detection-data/master/"
)
ARQUIVOS_BRUTOS = ["datatraining.txt", "datatest.txt", "datatest2.txt"]


def garantir_arquivos_brutos():
    raw_dir.mkdir(exist_ok=True)

    for nome in ARQUIVOS_BRUTOS:
        destino = raw_dir / nome

        if destino.exists():
            continue

        print(f"Baixando {nome}...")
        urllib.request.urlretrieve(BASE_URL + nome, destino)


def main():
    garantir_arquivos_brutos()

    partes = [
        pd.read_csv(raw_dir / nome, index_col=0)
        for nome in ARQUIVOS_BRUTOS
    ]

    df = pd.concat(partes, ignore_index=True)

    df["timestamp"] = pd.to_datetime(df["date"])

    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp")

    df = df.rename(
        columns={
            "CO2": "co2_sensor",
            "Occupancy": "occupancy",
            "Temperature": "temperature",
            "Humidity": "humidity",
            "Light": "light",
            "HumidityRatio": "humidity_ratio",
        }
    )

    df["weekday"] = df["timestamp"].dt.day_name()

    colunas = [
        "timestamp",
        "occupancy",
        "co2_sensor",
        "temperature",
        "humidity",
        "light",
        "humidity_ratio",
        "weekday",
    ]

    df = df[colunas].reset_index(drop=True)

    print(df.head(10))

    print()
    print("Quantidade de amostras (dataset real):", len(df))
    print(
        "Período coberto:",
        df["timestamp"].min(),
        "a",
        df["timestamp"].max(),
    )

    data_dir.mkdir(exist_ok=True)

    arquivo = data_dir / "co2_real_dataset.csv"

    df.to_csv(arquivo, index=False)

    print()
    print("Dataset real salvo em:")
    print(arquivo)


if __name__ == "__main__":
    main()

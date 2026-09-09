import sys
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt

# Evita UnicodeEncodeError ao imprimir "CO₂" em consoles Windows (cp1252)
sys.stdout.reconfigure(encoding="utf-8")

np.random.seed(42)


inicio = pd.Timestamp("2026-08-03 00:00:00")

datas = pd.date_range(
    start=inicio,
    periods=7 * 24 * 60,
    freq="1min"
)


def calcular_movimento(hora):

    if 7 <= hora < 9:
        return 6

    if 11 <= hora < 14:
        return 4

    if 17 <= hora < 20:
        return 7

    if 0 <= hora < 6:
        return 0.2

    return 1

# Fator de movimento para cada dia da semana
fator_dia = {
    0: 1.00,   # segunda
    1: 0.95,   # terça
    2: 1.10,   # quarta
    3: 1.05,   # quinta
    4: 1.35,   # sexta
    5: 0.60,   # sábado
    6: 0.40,   # domingo
}


fluxos = []

for data in datas:
    movimento = calcular_movimento(data.hour)

    movimento *= fator_dia[data.weekday()]

    carros = np.random.poisson(movimento)

    fluxos.append(carros)




CO2_EXTERNO = 450

co2_ideal = []

co2_atual = CO2_EXTERNO

for carros in fluxos:

    emissao = carros * 2.2

    ventilacao = 0.015 * (
        co2_atual - CO2_EXTERNO
    )

    co2_atual = (
        co2_atual
        + emissao
        - ventilacao
    )

    co2_ideal.append(co2_atual)


# -----------------------------
# SENSOR COM RUÍDO
# -----------------------------

ruido = np.random.normal(
    loc=0,
    scale=12,
    size=len(co2_ideal)
)

co2_sensor = np.array(co2_ideal) + ruido


# -----------------------------
# DATAFRAME
# -----------------------------

df = pd.DataFrame({
    "timestamp": datas,
    "vehicle_flow": fluxos,
    "co2_ideal": co2_ideal,
    "co2_sensor": co2_sensor
})

print(df.head(20))





df["weekday"] = df["timestamp"].dt.day_name()

movimento_por_dia = (
    df.groupby("weekday")["vehicle_flow"]
    .sum()
    .sort_values(ascending=False)
)

print()
print("MOVIMENTAÇÃO POR DIA")
print("--------------------------")

print(movimento_por_dia)

print()

print(
    "Dia com maior movimentação:",
    movimento_por_dia.index[0]
)





base_dir = Path(__file__).resolve().parent.parent

data_dir = base_dir / "data"

data_dir.mkdir(exist_ok=True)

arquivo = data_dir / "simulation.csv"

df.to_csv(
    arquivo,
    index=False
)

print()
print("Arquivo salvo em:")
print(arquivo)




charts_dir = base_dir / "charts"

charts_dir.mkdir(exist_ok=True)


plt.figure(figsize=(14, 6))

plt.plot(
    df["timestamp"],
    df["co2_sensor"],
    label="CO₂ sensor",
    alpha=0.5
)

plt.plot(
    df["timestamp"],
    df["co2_ideal"],
    label="CO₂ ideal"
)

plt.xlabel("Tempo")

plt.ylabel("CO₂ (ppm)")

plt.title(
    "Concentração simulada de CO₂"
)

plt.legend()

plt.tight_layout()


arquivo_grafico = (
    charts_dir / "co2_week.png"
)

plt.savefig(arquivo_grafico)

print()
print("Gráfico salvo em:")
print(arquivo_grafico)
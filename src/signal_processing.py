import sys
from pathlib import Path
from scipy.signal import find_peaks

import pandas as pd
import matplotlib.pyplot as plt

# Evita UnicodeEncodeError ao imprimir "CO₂" em consoles Windows (cp1252)
sys.stdout.reconfigure(encoding="utf-8")


# Caminho principal do projeto
base_dir = Path(__file__).resolve().parent.parent

data_dir = base_dir / "data"
charts_dir = base_dir / "charts"

arquivo = data_dir / "simulation.csv"


# Ler arquivo
df = pd.read_csv(
    arquivo,
    parse_dates=["timestamp"]
)


# -----------------------------
# FILTRO DE MÉDIA MÓVEL
# -----------------------------

JANELA = 15

df["co2_filtered"] = (
    df["co2_sensor"]
    .rolling(
        window=JANELA,
        center=True,
        min_periods=1
    )
    .mean()
)


# MOSTRAR RESULTADO
print(df.head(20))

print()
print("Quantidade de amostras:", len(df))


# -----------------------------
# COMPARAÇÃO VISUAL
# -----------------------------

primeiro_dia = df[
    df["timestamp"].dt.date
    == df["timestamp"].dt.date.min()
].copy()


plt.figure(figsize=(14, 6))

plt.plot(
    primeiro_dia["timestamp"],
    primeiro_dia["co2_sensor"],
    label="Sinal bruto",
    alpha=0.45
)

plt.plot(
    primeiro_dia["timestamp"],
    primeiro_dia["co2_filtered"],
    label="Sinal filtrado",
    linewidth=2
)

plt.xlabel("Horário")
plt.ylabel("CO₂ (ppm)")

plt.title(
    "CO₂ bruto x CO₂ filtrado"
)

plt.legend()

plt.tight_layout()


arquivo_grafico = (
    charts_dir
    / "raw_vs_filtered.png"
)

plt.savefig(arquivo_grafico)

plt.close()

print()
print("Gráfico criado em:")
print(arquivo_grafico)



# -----------------------------
# ATIVIDADE DO SINAL
# -----------------------------

CO2_BASELINE = 450

df["co2_activity"] = (
    df["co2_filtered"] - CO2_BASELINE
).clip(lower=0)



df["date"] = df["timestamp"].dt.date

df["weekday_number"] = (
    df["timestamp"].dt.weekday
)



dias_pt = {
    0: "Segunda-feira",
    1: "Terça-feira",
    2: "Quarta-feira",
    3: "Quinta-feira",
    4: "Sexta-feira",
    5: "Sábado",
    6: "Domingo",
}

df["weekday"] = (
    df["weekday_number"]
    .map(dias_pt)
)


# -----------------------------
# SALVAR RESULTADO PROCESSADO
# -----------------------------
# (feito aqui, depois de calcular co2_activity e o weekday em
# português, para que o CSV carregado no banco já saia completo)

arquivo_processado = (
    data_dir / "processed_simulation.csv"
)

df.to_csv(
    arquivo_processado,
    index=False
)

print()
print("Arquivo processado salvo em:")
print(arquivo_processado)


# -----------------------------
# ÍNDICE DE ATIVIDADE POR DIA
# -----------------------------

atividade_por_dia = (
    df.groupby("weekday")
    ["co2_activity"]
    .sum()
    .sort_values(ascending=False)
)


print()
print("ATIVIDADE ESTIMADA PELO CO₂")
print("--------------------------------")

print(atividade_por_dia)

print()

print(
    "Dia de maior atividade pelo CO₂:",
    atividade_por_dia.index[0]
)


# -----------------------------
# MOVIMENTAÇÃO REAL
# -----------------------------

movimento_real = (
    df.groupby("weekday")
    ["vehicle_flow"]
    .sum()
    .sort_values(ascending=False)
)


print()
print("MOVIMENTAÇÃO REAL")
print("-----------------------------")

print(movimento_real)

print()


dia_real = movimento_real.index[0]

dia_co2 = atividade_por_dia.index[0]


print("RESULTADO DA ANÁLISE")
print("-----------------------------")

print(
    "Maior movimentação real:",
    dia_real
)

print(
    "Maior movimentação estimada pelo CO₂:",
    dia_co2
)


if dia_real == dia_co2:

    print()
    print(
        "RESULTADO: o processamento identificou corretamente."
    )

else:

    print()
    print(
        "RESULTADO: a estimativa não correspondeu à simulação."
    )


    plt.figure(figsize=(10, 6))

atividade_por_dia.plot(
    kind="bar"
)

plt.xlabel("Dia da semana")

plt.ylabel(
    "Índice de atividade baseado em CO₂"
)

plt.title(
    "Movimentação estimada por dia"
)

plt.xticks(
    rotation=45,
    ha="right"
)

plt.tight_layout()


arquivo_ranking = (
    charts_dir
    / "activity_by_day.png"
)

plt.savefig(arquivo_ranking)

plt.close()


# -----------------------------
# DETECÇÃO DE PICOS
# -----------------------------

picos, propriedades = find_peaks(
    df["co2_filtered"],
    prominence=35,
    distance=120
)

df_picos = df.iloc[picos].copy()

df_picos["prominence"] = propriedades["prominences"]

print()
print("PICOS DE CO₂ IDENTIFICADOS")
print("--------------------------------")

print(
    df_picos[
        [
            "timestamp",
            "weekday",
            "co2_filtered",
            "prominence"
        ]
    ]
)

arquivo_picos_csv = data_dir / "co2_peaks.csv"

df_picos[
    [
        "timestamp",
        "weekday",
        "co2_filtered",
        "prominence"
    ]
].to_csv(arquivo_picos_csv, index=False)

print()
print("CSV de picos salvo em:")
print(arquivo_picos_csv)

if not df_picos.empty:

    maior_pico = df_picos.loc[
        df_picos["co2_filtered"].idxmax()
    ]

    print()
    print("MAIOR PICO DA SEMANA")
    print("--------------------------------")

    print(
        "Dia:",
        maior_pico["weekday"]
    )

    print(
        "Data e horário:",
        maior_pico["timestamp"]
    )

    print(
        "CO₂:",
        round(
            maior_pico["co2_filtered"],
            2
        ),
        "ppm"
    )
    plt.figure(figsize=(14, 6))

plt.plot(
    df["timestamp"],
    df["co2_filtered"],
    label="CO₂ filtrado"
)

plt.scatter(
    df_picos["timestamp"],
    df_picos["co2_filtered"],
    label="Picos detectados"
)

plt.xlabel("Tempo")
plt.ylabel("CO₂ (ppm)")

plt.title(
    "Detecção de picos de concentração de CO₂"
)

plt.legend()

plt.tight_layout()

arquivo_picos = (
    charts_dir / "co2_peaks.png"
)

plt.savefig(arquivo_picos)

plt.close()

print()
print(
    "Gráfico de picos criado em:",
    arquivo_picos
)
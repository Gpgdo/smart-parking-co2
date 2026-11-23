"""
Agrupamento K-means das janelas de 1 hora do sinal de CO2.

Cada janela de 1 hora vira um ponto com três atributos (média, mediana e
desvio padrão do CO2 do sensor). O K-means junta as janelas parecidas em
"grupos" - por exemplo: CO2 baixo e estável, CO2 médio, CO2 muito alto.

Os atributos são padronizados (StandardScaler) antes do K-means, porque a
média/mediana estão em centenas de ppm e o desvio padrão em dezenas: sem isso
a média dominaria a distância e o desvio quase não influenciaria os grupos.
"""

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

ATRIBUTOS = ["media", "mediana", "desvio_padrao"]

# Janelas com poucas amostras (bordas do dataset) deixam média/desvio instáveis
MIN_AMOSTRAS = 10


def agrupar_janelas(janelas: pd.DataFrame, k: int, semente: int = 42):
    """
    Aplica K-means com k grupos.

    Recebe um DataFrame com as colunas de ATRIBUTOS (uma linha por janela) e
    devolve (janelas_com_grupo, silhouette). Os grupos são numerados do menor
    para o maior CO2 médio (grupo 0 = CO2 mais baixo), para que o número tenha
    sempre o mesmo significado, independente da inicialização do K-means.
    """

    dados = janelas.copy()

    X = StandardScaler().fit_transform(dados[ATRIBUTOS])

    modelo = KMeans(n_clusters=k, n_init=20, random_state=semente)
    rotulos = modelo.fit_predict(X)

    dados["grupo"] = rotulos

    # renumera: 0 = menor média de CO2 ... k-1 = maior
    ordem = dados.groupby("grupo")["media"].mean().sort_values().index
    renumerar = {antigo: novo for novo, antigo in enumerate(ordem)}
    dados["grupo"] = dados["grupo"].map(renumerar)

    return dados, float(silhouette_score(X, rotulos))


def resumir_grupos(dados: pd.DataFrame) -> pd.DataFrame:
    """
    Uma linha por grupo: quantas janelas, CO2 médio, desvio médio e a
    porcentagem de janelas em que a sala esteve ocupada na maior parte da hora
    (ocupação real >= 50%), para comparar o grupo com a verdade de campo.
    """

    dados = dados.assign(ocupada=(dados["ocupacao_pct"] >= 50).astype(int))

    resumo = dados.groupby("grupo").agg(
        janelas=("media", "size"),
        media_co2=("media", "mean"),
        desvio_medio=("desvio_padrao", "mean"),
        pct_ocupada=("ocupada", "mean"),
    )

    resumo["pct_ocupada"] = resumo["pct_ocupada"] * 100

    return resumo.round(1).reset_index()

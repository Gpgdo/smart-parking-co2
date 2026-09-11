"""
API do Smart Parking CO2 - Analisador de Ocupação por Sinais de CO2.

Expõe os dados gerados pelo pipeline (dataset real de CO2/ocupação ->
processamento de sinais -> PostgreSQL) para o dashboard web. Os dados são
do dataset público "Occupancy Detection" (Candanedo; Feldheim, 2016),
com CO2 e ocupação reais medidos em uma sala fechada.

Rodar com:
    uvicorn api.main:app --reload
"""

import subprocess
import sys
import threading
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

# Permite importar src/db.py mesmo com api/ e src/ como pastas irmãs
sys.path.append(str(BASE_DIR / "src"))

from db import get_connection  # noqa: E402

app = FastAPI(
    title="Smart Parking CO2 API",
    description=(
        "API do Analisador de Ocupação por Sinais de CO2, com Processamento "
        "Digital de Sinais aplicado a um dataset público real de CO2 e "
        "ocupação (Candanedo; Feldheim, 2016)"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def conectar():
    return get_connection(row_factory=dict_row)


# Evita que dois cliques em "Reprocessar dataset" rodem o pipeline ao mesmo
# tempo (é um app de uso local/didático, então um lock simples já basta).
_lock_simulacao = threading.Lock()

# Ordem de execução do pipeline: carregar dataset real -> processar sinal -> carregar no banco
SCRIPTS_PIPELINE = ["load_real_data.py", "signal_processing.py", "load_to_db.py"]


def _executar_script(nome_script: str) -> dict:
    resultado = subprocess.run(
        [sys.executable, str(BASE_DIR / "src" / nome_script)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return {
        "script": nome_script,
        "ok": resultado.returncode == 0,
        "saida": resultado.stdout[-2000:],
        "erro": resultado.stderr[-2000:],
    }


COLUNAS_LEITURA = """
    "timestamp", weekday, occupancy,
    co2_sensor, co2_filtered, co2_activity,
    temperature, humidity, light, humidity_ratio
"""


@app.get("/api/health")
def health():
    try:
        with conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Banco de dados indisponível: {exc}"
        )


@app.get("/api/readings")
def listar_leituras(
    dia: Optional[date] = Query(
        None, description="Filtra por um dia específico (YYYY-MM-DD)"
    ),
    limite: int = Query(2000, ge=1, le=20000),
):
    with conectar() as conn:
        with conn.cursor() as cur:
            if dia is not None:
                cur.execute(
                    f"""
                    SELECT {COLUNAS_LEITURA}
                    FROM parking_readings
                    WHERE "timestamp"::date = %s
                    ORDER BY "timestamp"
                    """,
                    (dia,),
                )
            else:
                cur.execute(
                    f"""
                    SELECT {COLUNAS_LEITURA}
                    FROM parking_readings
                    ORDER BY "timestamp"
                    LIMIT %s
                    """,
                    (limite,),
                )

            return cur.fetchall()


@app.get("/api/readings/latest")
def ultima_leitura():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT {COLUNAS_LEITURA}
                FROM parking_readings
                ORDER BY "timestamp" DESC
                LIMIT 1
                """
            )

            resultado = cur.fetchone()

            if resultado is None:
                raise HTTPException(
                    status_code=404, detail="Nenhuma leitura encontrada no banco."
                )

            return resultado


@app.get("/api/readings/days")
def listar_dias_disponiveis():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT "timestamp"::date AS dia
                FROM parking_readings
                ORDER BY dia
                """
            )
            return [linha["dia"] for linha in cur.fetchall()]


@app.get("/api/peaks")
def listar_picos():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT "timestamp", weekday, co2_filtered, prominence
                FROM co2_peaks
                ORDER BY "timestamp"
                """
            )
            return cur.fetchall()


@app.get("/api/stats/daily")
def estatisticas_por_dia():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    weekday,
                    SUM(occupancy) AS ocupacao_real,
                    ROUND(SUM(co2_activity)::numeric, 2) AS atividade_co2,
                    ROUND(AVG(co2_filtered)::numeric, 2) AS co2_medio,
                    ROUND(MAX(co2_filtered)::numeric, 2) AS co2_maximo
                FROM parking_readings
                GROUP BY weekday
                ORDER BY atividade_co2 DESC
                """
            )
            return cur.fetchall()


@app.get("/api/stats/summary")
def resumo_geral():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_leituras,
                    MIN("timestamp") AS inicio,
                    MAX("timestamp") AS fim,
                    ROUND(AVG(co2_filtered)::numeric, 2) AS co2_medio,
                    ROUND(MAX(co2_filtered)::numeric, 2) AS co2_maximo,
                    SUM(occupancy) AS total_minutos_ocupados
                FROM parking_readings
                """
            )
            resumo = cur.fetchone()

            if resumo is None or resumo["total_leituras"] == 0:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Banco sem dados ainda. Rode src/load_real_data.py, "
                        "src/signal_processing.py e src/load_to_db.py."
                    ),
                )

            cur.execute("SELECT COUNT(*) AS total_picos FROM co2_peaks;")
            resumo["total_picos"] = cur.fetchone()["total_picos"]

            cur.execute(
                """
                SELECT weekday
                FROM parking_readings
                GROUP BY weekday
                ORDER BY SUM(occupancy) DESC
                LIMIT 1
                """
            )
            linha = cur.fetchone()
            resumo["dia_maior_ocupacao_real"] = linha["weekday"] if linha else None

            cur.execute(
                """
                SELECT weekday
                FROM parking_readings
                GROUP BY weekday
                ORDER BY SUM(co2_activity) DESC
                LIMIT 1
                """
            )
            linha = cur.fetchone()
            resumo["dia_maior_atividade_co2"] = linha["weekday"] if linha else None

            return resumo


@app.post("/api/simulate")
def executar_simulacao():
    """
    Roda o pipeline completo (carga do dataset real -> processamento de
    sinais -> carga no banco). Como o dataset é real e fixo (não é mais
    gerado aleatoriamente), o resultado é sempre o mesmo - o endpoint serve
    para reprocessar/recarregar tudo do zero, ao vivo, sem terminal.
    """

    if not _lock_simulacao.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="Já existe um processamento em andamento. Aguarde ele terminar.",
        )

    try:
        etapas = []

        for script in SCRIPTS_PIPELINE:
            etapa = _executar_script(script)
            etapas.append(etapa)

            if not etapa["ok"]:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "mensagem": f"Falha ao executar {script}.",
                        "etapas": etapas,
                    },
                )

        return {
            "status": "ok",
            "mensagem": "Dataset real reprocessado e recarregado no banco de dados.",
            "etapas": etapas,
        }
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Tempo esgotado executando {exc.cmd}.",
        )
    finally:
        _lock_simulacao.release()


# Serve o dashboard estático (web/index.html, app.js, style.css).
# Precisa ser o último "app.get"/mount registrado para não sobrepor a API.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

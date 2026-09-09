"""
Conexão com o PostgreSQL, compartilhada pelo loader e pela API.
"""

import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection(row_factory=None):
    """
    Abre uma nova conexão com o Postgres usando as
    variáveis de ambiente (arquivo .env).
    """

    kwargs = dict(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "smart_parking"),
        user=os.getenv("POSTGRES_USER", "parking"),
        password=os.getenv("POSTGRES_PASSWORD", "parking123"),
        # Sem isso, tentar conectar com o Postgres fora do ar pode travar
        # por muito tempo (dezenas de segundos) antes de falhar.
        connect_timeout=int(os.getenv("POSTGRES_CONNECT_TIMEOUT", "3")),
    )

    if row_factory is not None:
        kwargs["row_factory"] = row_factory

    return psycopg.connect(**kwargs)

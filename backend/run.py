"""Entrypoint de desenvolvimento (Windows-safe).

psycopg async exige SelectorEventLoop, mas o uvicorn cria um Proactor antes de
importar o app no Windows. Aqui o servidor roda dentro de um loop Selector.

Uso: python run.py   (sem --reload; para hot-reload use SQLite ou docker compose)
"""

import uvicorn

from app.core.aio import run
from app.core.config import settings


async def _serve() -> None:
    config = uvicorn.Config("app.main:app", host=settings.api_host, port=settings.api_port)
    await uvicorn.Server(config).serve()


if __name__ == "__main__":
    run(_serve())

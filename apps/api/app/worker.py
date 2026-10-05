"""Processo do worker: `python -m app.worker`.

Consome a fila de jobs (processamento de documentos). Pode rodar em quantas instâncias
for preciso: a reserva de jobs usa SKIP LOCKED.
"""

import asyncio
import contextlib

from app.ai.embeddings import build_embedding_provider
from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.core.logging import configure_logging
from app.ingestion.pipeline import IngestionContext, job_handlers
from app.jobs.worker import Worker
from app.storage import LocalStorage


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings.database_url.get_secret_value())
    sessionmaker = create_sessionmaker(engine)
    embedder = build_embedding_provider(settings)
    context = IngestionContext(
        sessionmaker, LocalStorage(settings.storage_local_path), embedder, settings
    )
    stop = asyncio.Event()
    try:
        await Worker(sessionmaker, job_handlers(context), settings).run_forever(stop)
    finally:
        await embedder.aclose()
        await engine.dispose()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())

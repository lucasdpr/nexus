"""Migrações rodam com a role dona do banco (sem trocar de role), por isso podem criar
tabelas, políticas de RLS e a role `nexus_app` usada pela aplicação."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.core.db import create_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_engine(get_settings().database_url.get_secret_value(), pooled=False)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Modo offline não é suportado: as migrações usam SQL específico do Postgres.")

asyncio.run(_run_async())

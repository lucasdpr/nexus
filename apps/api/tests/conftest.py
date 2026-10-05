import asyncio
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path

import pytest
from pydantic_settings import BaseSettings, SettingsConfigDict

API_DIR = Path(__file__).resolve().parents[1]


class _TestEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=API_DIR / ".env", extra="ignore")

    test_database_url: str | None = None


TEST_DATABASE_URL = _TestEnv().test_database_url

# Precisa acontecer antes de qualquer import de `app`, que lê a configuração.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "postgresql://sem-banco@localhost/sem-banco"
os.environ["LOGIN_MAX_FAILURES_PER_IP"] = "1000"

from fastapi import FastAPI  # noqa: E402
from httpx2 import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.db import create_engine  # noqa: E402
from app.main import create_app  # noqa: E402

ClientFactory = Callable[[], AsyncClient]


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


async def _truncate_all(database_url: str) -> None:
    engine = create_engine(database_url, pooled=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE organizations, users, sessions, login_attempts, collections, "
                "collection_members, audit_events CASCADE"
            )
        )
    await engine.dispose()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Banco de teste migrado e vazio. Os testes de integração são pulados sem ele."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL não configurada")

    from alembic import command
    from alembic.config import Config

    command.upgrade(Config(str(API_DIR / "alembic.ini")), "head")
    asyncio.run(_truncate_all(TEST_DATABASE_URL))
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
async def app(database_url: str) -> AsyncIterator[FastAPI]:
    """Uma instância da API para toda a sessão: evita reabrir conexões a cada teste."""
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def make_client(app: FastAPI) -> AsyncIterator[ClientFactory]:
    clients: list[AsyncClient] = []

    def factory() -> AsyncClient:
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        clients.append(client)
        return client

    yield factory
    for client in clients:
        await client.aclose()

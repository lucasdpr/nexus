"""Acesso ao banco com isolamento por organização.

Toda transação aberta pela aplicação assume a role `nexus_app` (sem BYPASSRLS) e grava a
organização corrente em `app.org_id`. As políticas de Row-Level Security usam esse valor,
então mesmo uma consulta sem filtro por organização só enxerga dados do próprio tenant.
É a segunda barreira: a primeira são os filtros explícitos nos repositórios.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

import asyncpg
from sqlalchemy import event, pool, text
from sqlalchemy.engine import URL, Connection, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, SessionTransaction

logger = logging.getLogger(__name__)

APP_ROLE = "nexus_app"

# Uma única ida ao banco por transação: troca a role (equivale a SET LOCAL ROLE) e o contexto.
_SET_CONTEXT = text(
    f"select set_config('role', '{APP_ROLE}', true), "
    "set_config('app.org_id', :org_id, true), set_config('app.user_id', :user_id, true)"
)

CONNECT_ATTEMPTS = 3
CONNECT_TIMEOUT_SECONDS = 15
# Quedas de rede e o Postgres serverless acordando da hibernação.
_TRANSIENT_CONNECT_ERRORS = (
    OSError,
    TimeoutError,
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.CannotConnectNowError,
)


def to_async_url(database_url: str) -> tuple[URL, dict[str, Any]]:
    """Converte uma URL no formato libpq (Neon, Docker) para o dialeto asyncpg."""
    url = make_url(database_url)
    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    connect_args: dict[str, Any] = {}
    if sslmode is not None:
        connect_args["ssl"] = sslmode
    return url.set(drivername="postgresql+asyncpg", query=query), connect_args


def create_engine(database_url: str, *, pooled: bool = True) -> AsyncEngine:
    url, connect_args = to_async_url(database_url)
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)

    async def connect() -> asyncpg.Connection:
        for attempt in range(1, CONNECT_ATTEMPTS + 1):
            try:
                return await asyncpg.connect(dsn, timeout=CONNECT_TIMEOUT_SECONDS, **connect_args)
            except _TRANSIENT_CONNECT_ERRORS:
                if attempt == CONNECT_ATTEMPTS:
                    raise
                logger.warning("Falha transitória ao conectar ao banco", extra={"attempt": attempt})
                await asyncio.sleep(0.5 * attempt)
        raise RuntimeError("inalcançável")

    pool_options: dict[str, Any] = (
        {"pool_size": 5, "max_overflow": 5} if pooled else {"poolclass": pool.NullPool}
    )
    return create_async_engine(
        "postgresql+asyncpg://", async_creator=connect, pool_pre_ping=True, **pool_options
    )


class TenantSession(Session):
    """Sessão que aplica role e contexto de organização a cada transação."""


def _context_params(session: Session) -> dict[str, str]:
    org_id = session.info.get("org_id")
    user_id = session.info.get("user_id")
    return {"org_id": str(org_id or ""), "user_id": str(user_id or "")}


@event.listens_for(TenantSession, "after_begin")
def _apply_tenant_context(
    session: Session, transaction: SessionTransaction, connection: Connection
) -> None:
    connection.execute(_SET_CONTEXT, _context_params(session))


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, sync_session_class=TenantSession, expire_on_commit=False)


async def set_tenant(session: AsyncSession, org_id: UUID, user_id: UUID | None = None) -> None:
    """Define a organização corrente da sessão, inclusive na transação já aberta."""
    session.info["org_id"] = org_id
    session.info["user_id"] = user_id
    if session.in_transaction():
        await session.execute(_SET_CONTEXT, _context_params(session.sync_session))

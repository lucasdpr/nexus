from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import create_engine, create_sessionmaker
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.core.origin import origin_guard
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.collections.router import router as collections_router
from app.modules.users.router import router as users_router


class HealthResponse(BaseModel):
    status: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(get_settings().database_url.get_secret_value())
    app.state.sessionmaker = create_sessionmaker(engine)
    yield
    await engine.dispose()


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101 - registrado apenas para DomainError
    return JSONResponse({"detail": exc.message}, status_code=exc.status_code)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="NEXUS API",
        version=version("nexus-api"),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.middleware("http")(origin_guard({settings.web_origin}))
    app.add_exception_handler(DomainError, _domain_error_handler)

    @app.get("/api/health", tags=["ops"])
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=app.version)

    for router in (auth_router, users_router, collections_router, audit_router):
        app.include_router(router)

    return app


app = create_app()

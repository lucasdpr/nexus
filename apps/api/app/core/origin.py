from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

Middleware = Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]


def origin_guard(allowed_origins: set[str]) -> Middleware:
    """Proteção contra CSRF, somada ao cookie SameSite=Lax.

    Navegadores sempre enviam `Origin` em requisições que alteram dados; se ela vier de
    outro site, a requisição é recusada. Clientes sem navegador (CLI, testes) não enviam
    `Origin` e não carregam cookies de terceiros, então não são afetados.
    """

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        cross_site = origin is not None and origin not in allowed_origins
        if request.method in UNSAFE_METHODS and cross_site:
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        return await call_next(request)

    return middleware

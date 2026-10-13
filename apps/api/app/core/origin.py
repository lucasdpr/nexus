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


DIRECT_UPLOAD_PATH = "/api/v1/documents/direct"


def direct_upload_cors(web_origin: str) -> Middleware:
    """CORS só para o envio direto de arquivos, e só para o front-end configurado.

    A rota autentica por token no formulário, não por cookie, então liberar essa origem não
    expõe a sessão de ninguém. O navegador faz uma consulta OPTIONS antes porque o envio
    acompanha o progresso; ela é respondida aqui, sem passar pelos demais middlewares.
    """
    headers = {
        "Access-Control-Allow-Origin": web_origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path != DIRECT_UPLOAD_PATH or request.headers.get("origin") != web_origin:
            return await call_next(request)
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=headers)
        response = await call_next(request)
        response.headers.update(headers)
        return response

    return middleware

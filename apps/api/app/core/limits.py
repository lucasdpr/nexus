"""Limite de tamanho do corpo das requisições, aplicado antes de qualquer leitura.

Sem isso, um upload gigante seria gravado inteiro em arquivo temporário pelo parser de
multipart antes de o endpoint ter chance de recusá-lo.
"""

from collections.abc import Mapping

from fastapi import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

TOO_LARGE = "A requisição é grande demais."


class RequestTooLarge(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=413, detail=TOO_LARGE)


class BodySizeLimitMiddleware:
    def __init__(
        self, app: ASGIApp, *, default_bytes: int, by_path: Mapping[str, int] | None = None
    ) -> None:
        self.app = app
        self.default_bytes = default_bytes
        self.by_path = dict(by_path or {})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return

        limit = self.by_path.get(scope["path"], self.default_bytes)
        headers = dict(scope["headers"])
        declared = headers.get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await _reject(send)
            return

        await self.app(scope, _counting(receive, limit), send)


def _counting(receive: Receive, limit: int) -> Receive:
    """Também conta os bytes de corpos sem Content-Length (transferência em partes)."""
    received = 0

    async def wrapped() -> Message:
        nonlocal received
        message = await receive()
        if message["type"] == "http.request":
            received += len(message.get("body", b""))
            if received > limit:
                # HTTPException atravessa o parser do FastAPI e vira resposta 413.
                raise RequestTooLarge()
        return message

    return wrapped


async def _reject(send: Send) -> None:
    body = b'{"detail":"' + TOO_LARGE.encode() + b'"}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})

"""Armazenamento dos arquivos enviados, atrás de uma interface mínima."""

import asyncio
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class LocalStorage:
    """Disco local. As chaves são geradas pela aplicação (`<org>/<documento>`), nunca pelo
    usuário; mesmo assim, qualquer caminho que escape da raiz é recusado."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("Chave de armazenamento inválida.")
        return path

    async def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)

    async def get(self, key: str) -> bytes:
        return await asyncio.to_thread(self._path(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)


def build_storage(settings: Settings) -> Storage:
    """Escolhe o armazenamento pela configuração; falta de dado do S3 falha na partida."""
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_local_path)

    from app.storage.s3 import S3Storage

    secret = (
        settings.s3_secret_access_key.get_secret_value() if settings.s3_secret_access_key else ""
    )
    missing = [
        name
        for name, value in (
            ("S3_ENDPOINT_URL", settings.s3_endpoint_url),
            ("S3_BUCKET", settings.s3_bucket),
            ("S3_ACCESS_KEY_ID", settings.s3_access_key_id),
            ("S3_SECRET_ACCESS_KEY", secret),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"STORAGE_BACKEND=s3 exige: {', '.join(missing)}.")
    return S3Storage(
        endpoint_url=settings.s3_endpoint_url,
        bucket=settings.s3_bucket,
        access_key_id=settings.s3_access_key_id,
        secret_access_key=secret,
        region=settings.s3_region,
    )

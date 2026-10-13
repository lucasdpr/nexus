"""Armazenamento dos arquivos no próprio Postgres (tabela `stored_files`).

Durável sem depender de outro serviço: o arquivo vive no mesmo banco que os documentos, então
sobrevive a reinícios de hospedagens de disco efêmero. Cabe bem em arquivos de até alguns MB
(o limite de upload é 25 MB); para volume grande, use o armazenamento S3.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseStorage:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @staticmethod
    def _check(key: str) -> None:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("Chave de armazenamento inválida.")

    async def put(self, key: str, data: bytes) -> None:
        self._check(key)
        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO stored_files (key, data, size_bytes) VALUES (:key, :data, :size) "
                    "ON CONFLICT (key) DO UPDATE SET data = EXCLUDED.data, "
                    "size_bytes = EXCLUDED.size_bytes"
                ),
                {"key": key, "data": data, "size": len(data)},
            )

    async def get(self, key: str) -> bytes:
        self._check(key)
        async with self._engine.connect() as connection:
            data = await connection.scalar(
                text("SELECT data FROM stored_files WHERE key = :key"), {"key": key}
            )
        if data is None:
            raise FileNotFoundError(key)
        return bytes(data)

    async def delete(self, key: str) -> None:
        self._check(key)
        async with self._engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM stored_files WHERE key = :key"), {"key": key}
            )

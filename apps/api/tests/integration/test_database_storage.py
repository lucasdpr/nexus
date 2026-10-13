from collections.abc import AsyncIterator

import pytest

from app.core.db import create_engine
from app.storage.database import DatabaseStorage

pytestmark = pytest.mark.anyio


@pytest.fixture
async def storage(database_url: str) -> AsyncIterator[DatabaseStorage]:
    engine = create_engine(database_url, pooled=False)
    yield DatabaseStorage(engine)
    await engine.dispose()


async def test_round_trip_overwrite_and_idempotent_delete(storage: DatabaseStorage) -> None:
    await storage.put("org/doc", b"primeiro")
    await storage.put("org/doc", b"segundo\x00com bytes nulos")

    assert await storage.get("org/doc") == b"segundo\x00com bytes nulos"

    await storage.delete("org/doc")
    await storage.delete("org/doc")
    with pytest.raises(FileNotFoundError):
        await storage.get("org/doc")


async def test_keys_cannot_escape(storage: DatabaseStorage) -> None:
    with pytest.raises(ValueError, match="inválida"):
        await storage.put("../fora", b"x")

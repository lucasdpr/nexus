from pathlib import Path

import pytest

from app.storage import LocalStorage

pytestmark = pytest.mark.anyio


async def test_round_trip_and_idempotent_delete(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path)

    await storage.put("org/doc", b"conteudo")
    assert await storage.get("org/doc") == b"conteudo"

    await storage.delete("org/doc")
    await storage.delete("org/doc")
    assert not (tmp_path / "org" / "doc").exists()


async def test_keys_cannot_escape_the_storage_root(tmp_path: Path) -> None:
    storage = LocalStorage(tmp_path / "raiz")

    with pytest.raises(ValueError, match="inválida"):
        await storage.put("../fora", b"x")

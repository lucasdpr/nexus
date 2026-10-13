import hashlib

import httpx2
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.db import create_engine
from app.storage import build_storage
from app.storage.s3 import S3Storage, StorageError, sign_v4

pytestmark = pytest.mark.anyio


def test_signature_matches_the_aws_documentation_example() -> None:
    # Exemplo "GET Object" da documentação da AWS (Signature Version 4, cabeçalho Authorization).
    authorization = sign_v4(
        method="GET",
        path="/test.txt",
        headers={
            "host": "examplebucket.s3.amazonaws.com",
            "range": "bytes=0-9",
            "x-amz-content-sha256": hashlib.sha256(b"").hexdigest(),
            "x-amz-date": "20130524T000000Z",
        },
        payload_sha256=hashlib.sha256(b"").hexdigest(),
        access_key="AKIAIOSFODNN7EXAMPLE",
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        region="us-east-1",
        amz_date="20130524T000000Z",
    )

    assert authorization == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )


class _FakeBucket:
    """Faz o papel do serviço S3: guarda objetos e registra o que recebeu."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "PUT":
            self.objects[path] = request.content
            return httpx2.Response(200)
        if request.method == "GET":
            data = self.objects.get(path)
            return httpx2.Response(200, content=data) if data is not None else httpx2.Response(404)
        self.objects.pop(path, None)
        return httpx2.Response(204)


def _storage(bucket: _FakeBucket) -> S3Storage:
    return S3Storage(
        endpoint_url="https://conta.r2.cloudflarestorage.com",
        bucket="nexus",
        access_key_id="chave",
        secret_access_key="segredo",
        client=httpx2.AsyncClient(transport=httpx2.MockTransport(bucket)),
    )


async def test_round_trip_and_idempotent_delete() -> None:
    bucket = _FakeBucket()
    storage = _storage(bucket)

    await storage.put("org/doc", b"conteudo")
    assert await storage.get("org/doc") == b"conteudo"
    await storage.delete("org/doc")
    await storage.delete("org/doc")

    with pytest.raises(FileNotFoundError):
        await storage.get("org/doc")


async def test_requests_are_signed_and_use_path_style_urls() -> None:
    bucket = _FakeBucket()

    await _storage(bucket).put("org/doc", b"abc")

    request = bucket.requests[0]
    assert request.url.host == "conta.r2.cloudflarestorage.com"
    assert request.url.path == "/nexus/org/doc"
    assert request.headers["authorization"].startswith("AWS4-HMAC-SHA256 Credential=chave/")
    assert request.headers["x-amz-content-sha256"] == hashlib.sha256(b"abc").hexdigest()


async def test_keys_cannot_escape_the_bucket() -> None:
    storage = _storage(_FakeBucket())

    for key in ("../fora", "/absoluta", ""):
        with pytest.raises(ValueError, match="inválida"):
            await storage.put(key, b"x")


async def test_storage_errors_are_not_confused_with_missing_files() -> None:
    storage = S3Storage(
        endpoint_url="https://s3.exemplo.com",
        bucket="b",
        access_key_id="a",
        secret_access_key="s",
        client=httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(403))),
    )

    with pytest.raises(StorageError, match="403"):
        await storage.get("org/doc")


def test_s3_backend_fails_at_startup_when_settings_are_missing() -> None:
    settings = Settings(database_url=SecretStr("postgresql://x@y/z"), storage_backend="s3")

    with pytest.raises(RuntimeError, match="S3_BUCKET"):
        build_storage(settings, create_engine("postgresql://x@y/z"))


def test_s3_endpoint_must_be_a_full_url() -> None:
    with pytest.raises(ValueError, match="URL completa"):
        S3Storage(endpoint_url="conta.r2", bucket="b", access_key_id="a", secret_access_key="s")


def test_storage_defaults_to_the_database_in_production_and_to_disk_otherwise() -> None:
    url = SecretStr("postgresql://x@y/z")

    assert Settings(database_url=url, environment="production").effective_storage_backend == "db"
    assert (
        Settings(database_url=url, environment="development").effective_storage_backend == "local"
    )
    assert (
        Settings(
            database_url=url, environment="production", storage_backend="local"
        ).effective_storage_backend
        == "local"
    )

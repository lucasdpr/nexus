"""Armazenamento em serviço compatível com S3 (Cloudflare R2, AWS S3, MinIO...).

Fala a API S3 direto com httpx2 e a assinatura AWS Signature V4, sem adicionar o SDK da AWS.
Usa endereçamento por caminho (`endpoint/bucket/chave`), aceito por todos esses serviços.
"""

import hashlib
import hmac
from datetime import UTC, datetime
from urllib.parse import quote, urlsplit

import httpx2

_ALGORITHM = "AWS4-HMAC-SHA256"
_SERVICE = "s3"
_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class StorageError(Exception):
    """Falha ao falar com o serviço de armazenamento."""


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def sign_v4(
    *,
    method: str,
    path: str,
    headers: dict[str, str],
    payload_sha256: str,
    access_key: str,
    secret_key: str,
    region: str,
    amz_date: str,
    query: str = "",
) -> str:
    """Valor do cabeçalho `Authorization`. `headers` traz `host` e `x-amz-*` (minúsculos)."""
    day = amz_date[:8]
    names = sorted(headers)
    canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in names)
    signed_headers = ";".join(names)
    canonical_request = "\n".join(
        [method, path, query, canonical_headers, signed_headers, payload_sha256]
    )
    scope = f"{day}/{region}/{_SERVICE}/aws4_request"
    to_sign = "\n".join(
        [_ALGORITHM, amz_date, scope, hashlib.sha256(canonical_request.encode()).hexdigest()]
    )
    key = _hmac(
        _hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), _SERVICE), "aws4_request"
    )
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    return (
        f"{_ALGORITHM} Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


class S3Storage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key_id: str,
        secret_access_key: str,
        region: str = "auto",
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        parts = urlsplit(endpoint_url)
        if not parts.scheme or not parts.netloc:
            raise ValueError("S3_ENDPOINT_URL precisa ser uma URL completa, como https://...")
        self._base = f"{parts.scheme}://{parts.netloc}"
        self._host = parts.netloc
        self._prefix = parts.path.rstrip("/")
        self._bucket = bucket
        self._access_key = access_key_id
        self._secret_key = secret_access_key
        self._region = region
        self._client = client or httpx2.AsyncClient(timeout=httpx2.Timeout(60, connect=10))

    def _path(self, key: str) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("Chave de armazenamento inválida.")
        return f"{self._prefix}/{quote(self._bucket)}/{quote(key, safe='/')}"

    async def _request(self, method: str, key: str, data: bytes = b"") -> httpx2.Response:
        path = self._path(key)
        payload_sha256 = hashlib.sha256(data).hexdigest() if data else _EMPTY_SHA256
        amz_date = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        signed = {
            "host": self._host,
            "x-amz-content-sha256": payload_sha256,
            "x-amz-date": amz_date,
        }
        authorization = sign_v4(
            method=method,
            path=path,
            headers=signed,
            payload_sha256=payload_sha256,
            access_key=self._access_key,
            secret_key=self._secret_key,
            region=self._region,
            amz_date=amz_date,
        )
        try:
            return await self._client.request(
                method,
                f"{self._base}{path}",
                content=data or None,
                headers={
                    "x-amz-content-sha256": payload_sha256,
                    "x-amz-date": amz_date,
                    "authorization": authorization,
                },
            )
        except httpx2.TransportError as exc:
            raise StorageError("Não foi possível falar com o armazenamento de arquivos.") from exc

    async def put(self, key: str, data: bytes) -> None:
        response = await self._request("PUT", key, data)
        if response.status_code not in (200, 201, 204):
            raise StorageError(f"O armazenamento recusou o envio ({response.status_code}).")

    async def get(self, key: str) -> bytes:
        response = await self._request("GET", key)
        if response.status_code == 404:
            raise FileNotFoundError(key)
        if response.status_code != 200:
            raise StorageError(f"O armazenamento recusou a leitura ({response.status_code}).")
        return response.content

    async def delete(self, key: str) -> None:
        response = await self._request("DELETE", key)
        if response.status_code not in (200, 204, 404):
            raise StorageError(f"O armazenamento recusou a exclusão ({response.status_code}).")

    async def aclose(self) -> None:
        await self._client.aclose()

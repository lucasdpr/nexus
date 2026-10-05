"""Embeddings atrás de uma interface: trocar de provedor é configuração, não arquitetura.

A dimensão é fixa porque a coluna `chunks.embedding` também é. Mudar de modelo exige
reprocessar os documentos, por isso cada trecho guarda o nome do modelo que o gerou.
"""

import asyncio
import hashlib
import math
import re
import unicodedata
from collections.abc import Sequence
from itertools import batched
from typing import Literal, Protocol

import httpx2

from app.core.config import Settings

EMBEDDING_DIMENSIONS = 1024

InputType = Literal["document", "query"]


class EmbeddingError(Exception):
    """Falha ao gerar embeddings (rede, limite de taxa, provedor fora do ar)."""


class EmbeddingProvider(Protocol):
    @property
    def model(self) -> str: ...

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...

    async def aclose(self) -> None: ...


_WORD = re.compile(r"\w+")


class HashingEmbeddingProvider:
    """Embeddings lexicais locais (feature hashing): determinísticos e sem custo.

    Aproximam textos que compartilham palavras, mas não entendem sinônimos. Servem para
    testes e para desenvolver sem chave de API, não para produção.
    """

    model = "hashing-v1"

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIMENSIONS
        ascii_text = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore")
        for word in _WORD.findall(ascii_text.decode()):
            value = int.from_bytes(hashlib.blake2b(word.encode(), digest_size=8).digest())
            vector[value % EMBEDDING_DIMENSIONS] += 1.0 if value >> 63 else -1.0
        norm = math.sqrt(sum(component * component for component in vector)) or 1.0
        return [component / norm for component in vector]

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    async def aclose(self) -> None:
        return None


class VoyageEmbeddingProvider:
    URL = "https://api.voyageai.com/v1/embeddings"
    BATCH_SIZE = 64
    MAX_ATTEMPTS = 5

    def __init__(
        self,
        api_key: str,
        model: str,
        client: httpx2.AsyncClient | None = None,
        *,
        backoff_seconds: float = 1.0,
    ) -> None:
        self._backoff_seconds = backoff_seconds
        self._api_key = api_key
        self._model = model
        self._client = client or httpx2.AsyncClient(timeout=60)

    @property
    def model(self) -> str:
        return self._model

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in batched(texts, self.BATCH_SIZE, strict=False):
            vectors.extend(await self._request(list(batch), "document"))
        return vectors

    async def embed_query(self, text: str) -> list[float]:
        return (await self._request([text], "query"))[0]

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, texts: list[str], input_type: InputType) -> list[list[float]]:
        payload = {
            "input": texts,
            "model": self._model,
            "input_type": input_type,
            "output_dimension": EMBEDDING_DIMENSIONS,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            try:
                response = await self._client.post(self.URL, json=payload, headers=headers)
            except httpx2.TransportError as exc:
                if attempt == self.MAX_ATTEMPTS:
                    raise EmbeddingError("Não foi possível contatar a Voyage AI.") from exc
                await asyncio.sleep(self._backoff_seconds * 2**attempt)
                continue

            retryable = response.status_code == 429 or response.status_code >= 500
            if retryable and attempt < self.MAX_ATTEMPTS:
                retry_after = response.headers.get("retry-after", "")
                delay = float(retry_after) if retry_after.isdigit() else 2**attempt
                await asyncio.sleep(self._backoff_seconds * delay)
                continue
            if response.is_error:
                raise EmbeddingError(f"A Voyage AI respondeu com erro {response.status_code}.")

            data = sorted(response.json()["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in data]
        raise EmbeddingError("A Voyage AI não respondeu após várias tentativas.")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "voyage":
        if settings.voyage_api_key is None:
            raise RuntimeError("EMBEDDING_PROVIDER=voyage exige VOYAGE_API_KEY.")
        return VoyageEmbeddingProvider(
            settings.voyage_api_key.get_secret_value(), settings.voyage_model
        )
    return HashingEmbeddingProvider()

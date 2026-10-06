import json
import math

import httpx2
import pytest

from app.ai.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingError,
    HashingEmbeddingProvider,
    VoyageEmbeddingProvider,
)

pytestmark = pytest.mark.anyio


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_hashing_embeddings_are_deterministic_normalized_and_lexical() -> None:
    provider = HashingEmbeddingProvider()

    query = await provider.embed_query("prazo de garantia do compressor")
    related, unrelated = await provider.embed_documents(
        ["A garantia do compressor tem prazo de 24 meses.", "Política de férias dos funcionários."]
    )

    assert len(query) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(x * x for x in query)), 1.0)
    assert query == await provider.embed_query("prazo de garantia do compressor")
    assert _cosine(query, related) > _cosine(query, unrelated)


def _voyage(handler: httpx2.MockTransport) -> VoyageEmbeddingProvider:
    client = httpx2.AsyncClient(transport=handler)
    return VoyageEmbeddingProvider("chave-teste", "voyage-4", client, backoff_seconds=0)


async def test_voyage_sends_input_type_and_returns_vectors_in_input_order() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        requests.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer chave-teste"
        return httpx2.Response(
            200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]}
        )

    vectors = await _voyage(httpx2.MockTransport(handler)).embed_documents(["a", "b"])

    assert vectors == [[1.0], [2.0]]
    assert requests[0]["input_type"] == "document"
    assert requests[0]["output_dimension"] == EMBEDDING_DIMENSIONS


async def test_voyage_retries_rate_limits_and_server_errors() -> None:
    responses = iter(
        [
            httpx2.Response(429, headers={"retry-after": "1"}),
            httpx2.Response(503),
            httpx2.Response(200, json={"data": [{"index": 0, "embedding": [0.5]}]}),
        ]
    )

    vector = await _voyage(httpx2.MockTransport(lambda _: next(responses))).embed_query("x")

    assert vector == [0.5]


async def test_voyage_reports_permanent_errors() -> None:
    provider = _voyage(httpx2.MockTransport(lambda _: httpx2.Response(401)))

    with pytest.raises(EmbeddingError, match="401"):
        await provider.embed_query("x")


async def test_hashing_ignores_words_without_content() -> None:
    provider = HashingEmbeddingProvider()

    question = await provider.embed_query("Qual é a política de férias dos funcionários?")
    passage = await provider.embed_query("O prazo de garantia é de 24 meses a partir da data.")

    assert _cosine(question, passage) == 0.0

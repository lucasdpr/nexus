import json

import httpx2
import pytest
from pydantic import SecretStr

from app.ai.answers import (
    AnswerError,
    AnswerPrompt,
    ExtractiveAnswerProvider,
    FallbackAnswerProvider,
    GeminiAnswerProvider,
    build_answer_provider,
)
from app.core.config import Settings

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    async def instant(_: float) -> None:
        return None

    monkeypatch.setattr("app.ai.answers.asyncio.sleep", instant)


PROMPT = AnswerPrompt(
    system="regras", user="pergunta", sources=["Fonte um. Segunda frase. Terceira."]
)


async def _collect(
    provider: GeminiAnswerProvider | ExtractiveAnswerProvider | FallbackAnswerProvider,
) -> str:
    return "".join([delta async for delta in provider.stream(PROMPT)])


def _gemini(handler: httpx2.MockTransport) -> GeminiAnswerProvider:
    return GeminiAnswerProvider(
        "chave-teste", "gemini-teste", 512, httpx2.AsyncClient(transport=handler)
    )


def _sse(*events: dict[str, object]) -> bytes:
    return b"".join(b"data: " + json.dumps(event).encode() + b"\r\n\r\n" for event in events)


async def test_extractive_provider_cites_the_first_source() -> None:
    assert (await _collect(ExtractiveAnswerProvider())).strip() == "Fonte um. Segunda frase. [S1]"


async def test_gemini_streams_text_parts_and_skips_thoughts() -> None:
    sent: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        sent.append(request)
        body = _sse(
            {"candidates": [{"content": {"parts": [{"text": "pensando", "thought": True}]}}]},
            {"candidates": [{"content": {"parts": [{"text": "Garantia de "}]}}]},
            {
                "candidates": [
                    {"content": {"parts": [{"text": "24 meses [S1]."}]}, "finishReason": "STOP"}
                ]
            },
        )
        return httpx2.Response(200, content=body, headers={"content-type": "text/event-stream"})

    text = await _collect(_gemini(httpx2.MockTransport(handler)))

    assert text == "Garantia de 24 meses [S1]."
    request = sent[0]
    assert request.url.path.endswith("/models/gemini-teste:streamGenerateContent")
    assert request.url.params["alt"] == "sse"
    assert "key" not in request.url.params
    assert request.headers["x-goog-api-key"] == "chave-teste"
    body = json.loads(request.content)
    assert body["systemInstruction"]["parts"][0]["text"] == "regras"
    assert body["contents"][0]["parts"][0]["text"] == "pergunta"


@pytest.mark.parametrize(
    ("status", "message"), [(429, "limite"), (400, "erro 400"), (503, "erro 503")]
)
async def test_gemini_errors_become_user_facing_messages(status: int, message: str) -> None:
    provider = _gemini(httpx2.MockTransport(lambda _: httpx2.Response(status)))

    with pytest.raises(AnswerError, match=message):
        await _collect(provider)


def test_gemini_without_a_key_fails_at_startup_with_a_clear_message() -> None:
    settings = Settings(
        database_url=SecretStr("postgresql://x@y/z"),
        answer_provider="gemini",
        gemini_api_key=SecretStr(""),
    )

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        build_answer_provider(settings)


async def test_gemini_retries_transient_overload_then_succeeds() -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx2.Response(503)
        body = _sse({"candidates": [{"content": {"parts": [{"text": "ok [S1]"}]}}]})
        return httpx2.Response(200, content=body)

    assert await _collect(_gemini(httpx2.MockTransport(handler))) == "ok [S1]"
    assert calls == 3


async def test_fallback_answers_extractively_when_the_primary_is_down() -> None:
    primary = _gemini(httpx2.MockTransport(lambda _: httpx2.Response(503)))

    text = await _collect(FallbackAnswerProvider(primary, ExtractiveAnswerProvider()))

    assert text.strip() == "Fonte um. Segunda frase. [S1]"

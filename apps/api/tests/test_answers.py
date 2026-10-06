import json

import httpx2
import pytest
from pydantic import SecretStr

from app.ai.answers import (
    AnswerError,
    AnswerPrompt,
    ExtractiveAnswerProvider,
    GeminiAnswerProvider,
    build_answer_provider,
)
from app.core.config import Settings

pytestmark = pytest.mark.anyio

PROMPT = AnswerPrompt(
    system="regras", user="pergunta", sources=["Fonte um. Segunda frase. Terceira."]
)


async def _collect(provider: GeminiAnswerProvider | ExtractiveAnswerProvider) -> str:
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


@pytest.mark.parametrize(("status", "message"), [(429, "limite"), (500, "erro 500")])
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

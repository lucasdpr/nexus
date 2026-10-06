"""Geração de respostas atrás de uma interface, com saída em streaming.

O provedor recebe instruções e fontes já montadas (`app.rag.prompt`); a validação das
citações acontece depois, fora dele (`app.rag.citations`). Nenhum provedor é confiável para
decidir sozinho o que é uma fonte válida.
"""

import json
import re
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx2

from app.core.config import Settings


class AnswerError(Exception):
    """Falha do provedor de respostas. A mensagem é mostrada ao usuário."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True, slots=True)
class AnswerPrompt:
    system: str
    user: str
    # Conteúdo das fontes, na ordem dos marcadores [S1], [S2]...
    sources: Sequence[str]


class AnswerProvider(Protocol):
    @property
    def model(self) -> str: ...

    def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]: ...

    async def aclose(self) -> None: ...


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


class ExtractiveAnswerProvider:
    """Responde sem modelo de linguagem: devolve as primeiras frases da fonte mais relevante,
    citada. Não sintetiza nem raciocina; existe para desenvolver e testar sem chave de API."""

    model = "extractive-v1"

    async def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]:
        sentences = _SENTENCE_END.split(" ".join(prompt.sources[0].split()))
        answer = " ".join(sentences[:2]) + " [S1]"
        for word in answer.split(" "):
            yield word + " "

    async def aclose(self) -> None:
        return None


class GeminiAnswerProvider:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_output_tokens: int,
        client: httpx2.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._client = client or httpx2.AsyncClient(timeout=httpx2.Timeout(60, connect=10))

    @property
    def model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        await self._client.aclose()

    async def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]:
        body = {
            "systemInstruction": {"parts": [{"text": prompt.system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt.user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": self._max_output_tokens,
            },
        }
        url = f"{self.BASE_URL}/{self._model}:streamGenerateContent"
        # A chave vai no cabeçalho, não na URL, para não aparecer em logs de acesso.
        headers = {"x-goog-api-key": self._api_key}
        try:
            async with self._client.stream(
                "POST", url, params={"alt": "sse"}, json=body, headers=headers
            ) as response:
                if response.status_code == 429:
                    raise AnswerError(
                        "O limite de uso do provedor de IA foi atingido. Tente em alguns minutos."
                    )
                if response.is_error:
                    raise AnswerError(
                        f"O provedor de IA respondeu com erro {response.status_code}."
                    )
                async for line in response.aiter_lines():
                    for text in _texts_from_sse_line(line):
                        yield text
        except httpx2.TransportError as exc:
            raise AnswerError("Não foi possível contatar o provedor de IA.") from exc


def _texts_from_sse_line(line: str) -> list[str]:
    if not line.startswith("data:"):
        return []
    event: dict[str, Any] = json.loads(line.removeprefix("data:"))
    texts = []
    for candidate in event.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            # Partes de raciocínio ("thought") não fazem parte da resposta.
            if not part.get("thought") and part.get("text"):
                texts.append(part["text"])
    return texts


def build_answer_provider(settings: Settings) -> AnswerProvider:
    if settings.answer_provider == "gemini":
        api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
        if not api_key:
            raise RuntimeError("ANSWER_PROVIDER=gemini exige GEMINI_API_KEY.")
        return GeminiAnswerProvider(
            api_key,
            settings.gemini_model,
            settings.answer_max_output_tokens,
        )
    return ExtractiveAnswerProvider()

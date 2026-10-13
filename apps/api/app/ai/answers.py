"""Geração de respostas atrás de uma interface, com saída em streaming.

O provedor recebe instruções e fontes já montadas (`app.rag.prompt`); a validação das
citações acontece depois, fora dele (`app.rag.citations`). Nenhum provedor é confiável para
decidir sozinho o que é uma fonte válida.
"""

import asyncio
import json
import logging
import re
import unicodedata
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import httpx2

from app.core.config import Settings

logger = logging.getLogger(__name__)

# Erros do Google que costumam passar sozinhos (sobrecarga do modelo).
_RETRYABLE_STATUS = {500, 502, 503, 504}
_RETRY_DELAYS = (1.0, 3.0)


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


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD = re.compile(r"[a-z0-9]+")
# Códigos de equipamento como "cx-200" ou "ph-02": se a pergunta cita um, a fonte precisa tê-lo.
_CODE = re.compile(r"\b[a-z]{1,4}-?\d{1,4}\b")
_STOPWORDS = frozenset(
    [
        "qual",
        "quais",
        "quem",
        "quando",
        "onde",
        "como",
        "quanto",
        "quantos",
        "quantas",
        "para",
        "pelo",
        "pela",
        "pelos",
        "pelas",
        "uma",
        "uns",
        "umas",
        "que",
        "por",
        "com",
        "sem",
        "sobre",
        "entre",
        "ate",
        "dos",
        "das",
        "nos",
        "nas",
        "mais",
        "menos",
        "foi",
        "sao",
        "ser",
        "tem",
        "tinha",
        "deve",
        "devem",
        "essa",
        "esse",
        "isso",
        "esta",
        "este",
        "isto",
        "aos",
    ]
)
_MIN_COVERAGE = 0.6
# Fração mínima das palavras da pergunta que precisa existir nas fontes.
_MIN_PRESENT = 0.5


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _stems(text: str) -> set[str]:
    return {
        word[:5]
        for word in _WORD.findall(_CODE.sub(" ", _fold(text)))
        if len(word) >= 3 and word not in _STOPWORDS and not word.isdigit()
    }


def _question_of(prompt: AnswerPrompt) -> str:
    return prompt.user.rsplit("Pergunta:", 1)[-1].strip()


class ExtractiveAnswerProvider:
    """Responde sem modelo de linguagem: devolve a frase das fontes que mais cobre a pergunta,
    citada, ou recusa quando nenhuma cobre o bastante. Não sintetiza nem raciocina; serve para
    desenvolver sem chave de API e como reserva quando o modelo está indisponível."""

    model = "extractive-v2"

    async def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]:
        answer = self._best_sentence(_question_of(prompt), prompt.sources)
        if answer is None:
            from app.rag.prompt import NOT_FOUND_ANSWER

            answer = NOT_FOUND_ANSWER
        for word in answer.split(" "):
            yield word + " "

    @staticmethod
    def _best_sentence(question: str, sources: Sequence[str]) -> str | None:
        wanted = _stems(question)
        if not wanted:
            return None
        folded = " ".join(_fold(source) for source in sources)
        # Código citado na pergunta (CX-300): se nenhuma fonte o tem, o documento não é esse.
        if any(code not in folded for code in set(_CODE.findall(_fold(question)))):
            return None
        # Palavras da pergunta que não aparecem em fonte nenhuma (o nome da empresa, que está
        # em outro trecho, por exemplo) não contam contra a resposta; mas se quase nada da
        # pergunta existe nas fontes, ela é sobre outro assunto.
        present = {stem for stem in wanted if stem in folded}
        if len(present) / len(wanted) < _MIN_PRESENT:
            return None
        best: tuple[float, int, str] | None = None
        for marker, source in enumerate(sources, start=1):
            for sentence in _SENTENCE_END.split(source):
                covered = len(present & _stems(sentence))
                coverage = covered / len(present)
                if covered >= 2 and coverage >= _MIN_COVERAGE and (not best or coverage > best[0]):
                    best = (coverage, marker, sentence.strip())
        if best is None:
            return None
        _, marker, sentence = best
        return f"{sentence} [S{marker}]"

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
        for attempt, delay in enumerate((*_RETRY_DELAYS, None)):
            try:
                async with self._client.stream(
                    "POST", url, params={"alt": "sse"}, json=body, headers=headers
                ) as response:
                    if response.status_code == 429:
                        raise AnswerError(
                            "O limite de uso do provedor de IA foi atingido. "
                            "Tente em alguns minutos."
                        )
                    if response.status_code in _RETRYABLE_STATUS and delay is not None:
                        logger.warning(
                            "Gemini respondeu %s (tentativa %s)", response.status_code, attempt + 1
                        )
                        await asyncio.sleep(delay)
                        continue
                    if response.is_error:
                        raise AnswerError(
                            f"O provedor de IA respondeu com erro {response.status_code}."
                        )
                    async for line in response.aiter_lines():
                        for text in _texts_from_sse_line(line):
                            yield text
                    return
            except httpx2.TransportError as exc:
                raise AnswerError("Não foi possível contatar o provedor de IA.") from exc


class FallbackAnswerProvider:
    """Usa o provedor principal; se ele falhar antes de produzir qualquer texto, responde de
    forma extrativa com as mesmas fontes, em vez de deixar o usuário sem resposta."""

    def __init__(self, primary: AnswerProvider, fallback: AnswerProvider) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def model(self) -> str:
        return self._primary.model

    async def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]:
        started = False
        try:
            async for text in self._primary.stream(prompt):
                started = True
                yield text
        except AnswerError:
            if started:
                raise
            logger.warning("Provedor principal indisponível; usando resposta extrativa")
        else:
            return
        async for text in self._fallback.stream(prompt):
            yield text

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._fallback.aclose()


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
        # Cadeia: modelo principal, depois cada modelo reserva, por fim a resposta extrativa.
        models = [
            settings.gemini_model,
            *(m.strip() for m in settings.gemini_fallback_models.split(",") if m.strip()),
        ]
        provider: AnswerProvider = ExtractiveAnswerProvider()
        for model in reversed(models):
            gemini = GeminiAnswerProvider(api_key, model, settings.answer_max_output_tokens)
            provider = FallbackAnswerProvider(gemini, provider)
        return provider
    return ExtractiveAnswerProvider()

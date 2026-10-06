"""Validação das citações da resposta: nenhuma fonte inventada chega ao usuário."""

import re
from dataclasses import dataclass

from app.rag.prompt import NOT_FOUND_ANSWER

# [S1], [S2][S3] e também a variante agrupada [S1, S3].
_MARKER_GROUP = re.compile(r"\[\s*(S\d+(?:\s*,\s*S\d+)*)\s*\]")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([.,;:!?])")
_EXTRA_SPACES = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True, slots=True)
class FinalAnswer:
    text: str
    # Marcadores válidos, na ordem da primeira citação.
    markers: list[int]
    answered: bool


def _not_found() -> FinalAnswer:
    return FinalAnswer(NOT_FOUND_ANSWER, [], answered=False)


def finalize_answer(raw: str, source_count: int) -> FinalAnswer:
    """Mantém só citações de fontes que existem; uma resposta sem nenhuma vira "não encontrei".

    Uma afirmação sem fonte verificável não é apresentada como fato.
    """
    text = raw.strip()
    if not text or NOT_FOUND_ANSWER.rstrip(".").lower() in text.lower():
        return _not_found()

    markers: list[int] = []

    def keep_valid(match: re.Match[str]) -> str:
        valid = []
        for marker in (int(part.strip()[1:]) for part in match[1].split(",")):
            if 1 <= marker <= source_count:
                valid.append(marker)
                if marker not in markers:
                    markers.append(marker)
        return "".join(f"[S{marker}]" for marker in valid)

    text = _MARKER_GROUP.sub(keep_valid, text)
    text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", _EXTRA_SPACES.sub(" ", text)).strip()
    if not markers:
        return _not_found()
    return FinalAnswer(text, markers, answered=True)

"""Divide o texto em trechos para busca e citação.

Regras:
- Um trecho nunca atravessa páginas, para que a citação aponte a página exata.
- O corte respeita frases e parágrafos; só uma frase maior que o máximo é cortada no meio.
- Trechos vizinhos repetem as últimas frases do anterior (sobreposição), para que uma
  ideia dividida entre dois trechos continue recuperável.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.ingestion.extraction import PageText

_PARAGRAPH = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?;:])\s+")

# Uma unidade é uma frase e o índice do parágrafo a que pertence.
Unit = tuple[int, str]


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_chars: int
    max_chars: int
    overlap_chars: int


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    ordinal: int
    page: int | None
    content: str

    @property
    def token_estimate(self) -> int:
        return max(1, len(self.content) // 4)


def chunk_pages(pages: Sequence[PageText], config: ChunkingConfig) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    for page in pages:
        for content in _chunk_text(page.text, config):
            drafts.append(ChunkDraft(len(drafts), page.page, content))
    return drafts


def _chunk_text(text: str, config: ChunkingConfig) -> list[str]:
    chunks: list[list[Unit]] = []
    current: list[Unit] = []
    overlap_count = 0

    for unit in _units(text, config.max_chars):
        if current and _length([*current, unit]) > config.target_chars:
            chunks.append(current)
            current = _overlap(current, config.overlap_chars)
            if _length([*current, unit]) > config.max_chars:
                current = []
            overlap_count = len(current)
        current.append(unit)

    if current:
        fresh = current[overlap_count:]
        # Sobra pequena no fim da página: anexa ao trecho anterior se couber.
        if chunks and _length(fresh) < config.target_chars // 4:
            merged = [*chunks[-1], *fresh]
            if _length(merged) <= config.max_chars:
                chunks[-1] = merged
                return [_join(chunk) for chunk in chunks]
        chunks.append(current)
    return [_join(chunk) for chunk in chunks]


def _units(text: str, max_chars: int) -> list[Unit]:
    units: list[Unit] = []
    for index, paragraph in enumerate(_PARAGRAPH.split(text)):
        flat = " ".join(paragraph.split())
        for sentence in _SENTENCE_END.split(flat):
            units.extend((index, piece) for piece in _hard_split(sentence, max_chars) if piece)
    return units


def _hard_split(text: str, max_chars: int) -> list[str]:
    pieces: list[str] = []
    while len(text) > max_chars:
        cut = text.rfind(" ", 0, max_chars)
        if cut <= 0:
            cut = max_chars
        pieces.append(text[:cut].strip())
        text = text[cut:].strip()
    pieces.append(text)
    return pieces


def _overlap(units: list[Unit], overlap_chars: int) -> list[Unit]:
    tail: list[Unit] = []
    for unit in reversed(units):
        if _length([unit, *tail]) > overlap_chars:
            break
        tail.insert(0, unit)
    return tail


def _join(units: Sequence[Unit]) -> str:
    """Frases do mesmo parágrafo separadas por espaço; parágrafos, por quebra de linha."""
    parts: list[str] = []
    previous: int | None = None
    for paragraph, sentence in units:
        if previous is not None:
            parts.append(" " if paragraph == previous else "\n")
        parts.append(sentence)
        previous = paragraph
    return "".join(parts)


def _length(units: Sequence[Unit]) -> int:
    return sum(len(sentence) for _, sentence in units) + max(0, len(units) - 1)

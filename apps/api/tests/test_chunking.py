from itertools import pairwise

from app.ingestion.chunking import ChunkingConfig, chunk_pages
from app.ingestion.extraction import PageText

CONFIG = ChunkingConfig(target_chars=200, max_chars=260, overlap_chars=60)


def _sentences(prefix: str, count: int) -> str:
    return " ".join(
        f"{prefix} frase número {index} com algum conteúdo técnico." for index in range(count)
    )


def test_short_page_becomes_a_single_chunk_with_its_page() -> None:
    chunks = chunk_pages([PageText(7, "Garantia de 24 meses.")], CONFIG)

    assert [(chunk.page, chunk.content) for chunk in chunks] == [(7, "Garantia de 24 meses.")]


def test_chunks_never_cross_pages_and_ordinals_are_sequential() -> None:
    pages = [PageText(1, _sentences("Página um", 12)), PageText(2, _sentences("Página dois", 12))]

    chunks = chunk_pages(pages, CONFIG)

    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert all("Página dois" not in chunk.content for chunk in chunks if chunk.page == 1)
    assert all("Página um" not in chunk.content for chunk in chunks if chunk.page == 2)


def test_chunks_respect_the_size_limit_and_overlap_neighbours() -> None:
    chunks = chunk_pages([PageText(1, _sentences("Manual", 30))], CONFIG)

    assert len(chunks) > 3
    assert all(len(chunk.content) <= CONFIG.max_chars for chunk in chunks)
    for previous, current in pairwise(chunks):
        last_sentence = previous.content.rsplit(". ", 1)[-1]
        assert current.content.startswith(last_sentence.split(" com ")[0])


def test_sentence_longer_than_the_maximum_is_split_at_spaces() -> None:
    giant = " ".join(["palavra"] * 200)

    chunks = chunk_pages([PageText(1, giant)], CONFIG)

    assert all(len(chunk.content) <= CONFIG.max_chars for chunk in chunks)
    assert all(not chunk.content.startswith(" ") for chunk in chunks)


def test_paragraphs_are_kept_on_separate_lines() -> None:
    chunks = chunk_pages([PageText(None, "Título\n\nPrimeiro parágrafo.")], CONFIG)

    assert chunks[0].content == "Título\nPrimeiro parágrafo."


def test_small_remainder_is_merged_into_the_previous_chunk() -> None:
    text = _sentences("Corpo", 4) + " Fim."

    chunks = chunk_pages([PageText(1, text)], CONFIG)

    assert chunks[-1].content.endswith("Fim.")
    assert not any(chunk.content == "Fim." for chunk in chunks)

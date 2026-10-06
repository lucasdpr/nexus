"""Busca híbrida: vetorial (semântica) + textual em português, fundidas por RRF.

A permissão é aplicada dentro das consultas, nunca depois: organização (também pelo RLS),
coleções que o usuário acessa, documento pronto e não excluído. O que o usuário não pode
ler nunca chega ao ranking, ao contexto da IA nem à resposta.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ColumnElement,
    Float,
    Select,
    Text,
    bindparam,
    cast,
    func,
    literal_column,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import EMBEDDING_DIMENSIONS
from app.core.config import Settings
from app.modules.auth.identity import CurrentUser
from app.modules.collections.repository import collection_access
from app.modules.documents.models import Chunk, Document, DocumentKind, DocumentStatus
from app.retrieval.fusion import reciprocal_rank_fusion


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_kind: DocumentKind
    page: int | None
    content: str
    # Similaridade de cosseno com a pergunta (None se só a busca textual encontrou).
    similarity: float | None
    text_match: bool
    score: float


@dataclass(frozen=True, slots=True)
class SearchFilters:
    collection_id: UUID | None = None


def _candidates(
    current: CurrentUser, filters: SearchFilters
) -> Select[UUID, UUID, int | None, str, str, DocumentKind]:
    query = (
        select(
            Chunk.id,
            Chunk.document_id,
            Chunk.page,
            Chunk.content,
            Document.title,
            Document.kind,
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.org_id == current.org_id,
            Document.org_id == current.org_id,
            Document.status == DocumentStatus.READY,
            Document.deleted_at.is_(None),
            collection_access(Chunk.collection_id, current),
        )
    )
    if filters.collection_id is not None:
        query = query.where(Chunk.collection_id == filters.collection_id)
    return query


def _any_word_query(question: str) -> ColumnElement[Any]:
    """tsquery que aceita qualquer palavra relevante da pergunta (OU), sem acentos.

    `plainto_tsquery` exige todas as palavras (E), o que em perguntas em linguagem natural
    quase nunca acontece num único trecho. Os lexemas já normalizados são recombinados com
    OU sob a configuração `simple`, para não serem reprocessados.
    """
    every_word = func.plainto_tsquery(
        literal_column("'portuguese'"), func.immutable_unaccent(question)
    )
    return func.to_tsquery(
        literal_column("'simple'"), func.replace(cast(every_word, Text), "&", "|")
    )


async def hybrid_search(
    db: AsyncSession,
    current: CurrentUser,
    question: str,
    question_vector: Sequence[float],
    settings: Settings,
    filters: SearchFilters | None = None,
) -> list[RetrievedChunk]:
    filters = filters or SearchFilters()
    base = _candidates(current, filters)

    # pgvector >= 0.8: com filtros, o índice HNSW continua buscando até completar o limite.
    await db.execute(text("select set_config('hnsw.iterative_scan', 'relaxed_order', true)"))
    vector = bindparam("question_vector", list(question_vector), type_=Vector(EMBEDDING_DIMENSIONS))
    distance = Chunk.embedding.op("<=>", return_type=Float)(vector)
    vector_rows = (
        await db.execute(
            base.add_columns(distance.label("distance"))
            .order_by(distance)
            .limit(settings.retrieval_vector_candidates)
        )
    ).all()

    tsquery = _any_word_query(question)
    rank = func.ts_rank_cd(Chunk.tsv, tsquery)
    text_rows = (
        await db.execute(
            base.add_columns(rank.label("rank"))
            .where(Chunk.tsv.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(settings.retrieval_text_candidates)
        )
    ).all()

    rows = {row.id: row for row in [*vector_rows, *text_rows]}
    similarity = {row.id: 1 - float(row.distance) for row in vector_rows}
    text_matches = {row.id for row in text_rows}
    scores = reciprocal_rank_fusion(
        [[row.id for row in vector_rows], [row.id for row in text_rows]], settings.retrieval_rrf_k
    )

    results = [
        RetrievedChunk(
            chunk_id=chunk_id,
            document_id=rows[chunk_id].document_id,
            document_title=rows[chunk_id].title,
            document_kind=rows[chunk_id].kind,
            page=rows[chunk_id].page,
            content=rows[chunk_id].content,
            similarity=similarity.get(chunk_id),
            text_match=chunk_id in text_matches,
            score=score,
        )
        for chunk_id, score in scores.items()
    ]
    return sorted(results, key=lambda chunk: chunk.score, reverse=True)


def relevant(chunks: Sequence[RetrievedChunk], min_similarity: float) -> list[RetrievedChunk]:
    """Descarta o que só entrou no ranking por falta de coisa melhor.

    Um trecho conta se tem palavras da pergunta ou similaridade semântica mínima. Sem nenhum,
    a resposta é "não encontrei" — sem chamar a IA.
    """
    return [
        chunk for chunk in chunks if chunk.text_match or (chunk.similarity or 0.0) >= min_similarity
    ]

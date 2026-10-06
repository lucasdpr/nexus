from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.core.errors import ServiceUnavailableError
from app.modules.auth.dependencies import CurrentUserDep, DbSession, SettingsDep
from app.modules.documents.models import DocumentKind
from app.retrieval.search import SearchFilters, hybrid_search, relevant

router = APIRouter(prefix="/api/v1/search", tags=["search"])

SNIPPET_CHARS = 300


class SearchHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    document_title: str
    document_kind: DocumentKind
    page: int | None
    snippet: str
    score: float


class SearchResults(BaseModel):
    query: str
    items: list[SearchHit]


@router.get("")
async def search(
    request: Request,
    db: DbSession,
    current: CurrentUserDep,
    settings: SettingsDep,
    q: Annotated[str, Query(min_length=2, max_length=300)],
    collection_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SearchResults:
    """Busca de trechos (textual + semântica) só nos documentos que o usuário pode ler."""
    embedder: EmbeddingProvider = request.app.state.embedder
    try:
        vector = await embedder.embed_query(q)
    except EmbeddingError as exc:
        raise ServiceUnavailableError("A busca está indisponível agora.") from exc
    chunks = await hybrid_search(
        db, current, q, vector, settings, SearchFilters(collection_id=collection_id)
    )
    hits = relevant(chunks, settings.retrieval_min_similarity)[:limit]
    return SearchResults(
        query=q,
        items=[
            SearchHit(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                document_kind=chunk.document_kind,
                page=chunk.page,
                snippet=chunk.content[:SNIPPET_CHARS],
                score=chunk.score,
            )
            for chunk in hits
        ],
    )

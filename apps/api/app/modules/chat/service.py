"""Assistente: pergunta → busca com permissão → resposta em streaming → citações validadas.

PERGUNTA ─► embedding ─► busca vetorial + textual (só o que o usuário pode ler) ─► RRF
        ─► limiar de relevância ─► (nada relevante? "não encontrei", sem chamar a IA)
        ─► contexto numerado [S1..Sn] ─► IA em streaming ─► citações validadas ─► registro
"""

import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.answers import AnswerError, AnswerProvider
from app.ai.embeddings import EmbeddingError, EmbeddingProvider
from app.core.config import Settings
from app.core.db import set_tenant
from app.core.errors import DomainError, NotFoundError, RateLimitedError
from app.modules.audit import service as audit
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.chat import repository
from app.modules.chat.models import Citation, Conversation, Message, MessageRole, MessageStatus
from app.modules.chat.schemas import (
    CitationOut,
    ConversationDetail,
    ConversationOut,
    MessageOut,
    SourceOut,
    sse,
)
from app.modules.organizations.models import Organization
from app.rag.citations import FinalAnswer, finalize_answer
from app.rag.prompt import NOT_FOUND_ANSWER, Source, Turn, build_prompt, select_sources
from app.retrieval.search import hybrid_search, relevant

logger = logging.getLogger(__name__)

NOT_FOUND = "Conversa não encontrada."
HISTORY_MESSAGES = 4
SNIPPET_CHARS = 280


@dataclass(frozen=True, slots=True)
class ChatContext:
    sessionmaker: async_sessionmaker[AsyncSession]
    embedder: EmbeddingProvider
    answerer: AnswerProvider
    settings: Settings


def _now() -> datetime:
    return datetime.now(UTC)


async def create_conversation(db: AsyncSession, current: CurrentUser) -> ConversationOut:
    conversation = Conversation(org_id=current.org_id, user_id=current.user_id)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationOut.model_validate(conversation, from_attributes=True)


async def _owned(db: AsyncSession, current: CurrentUser, conversation_id: UUID) -> Conversation:
    conversation = await repository.get_owned(db, current, conversation_id)
    if conversation is None:
        raise NotFoundError(NOT_FOUND)
    return conversation


async def delete_conversation(
    db: AsyncSession, current: CurrentUser, conversation_id: UUID
) -> None:
    conversation = await _owned(db, current, conversation_id)
    await db.execute(
        delete(Conversation).where(
            Conversation.org_id == current.org_id, Conversation.id == conversation.id
        )
    )
    await db.commit()


async def get_detail(
    db: AsyncSession, current: CurrentUser, conversation_id: UUID
) -> ConversationDetail:
    conversation = await _owned(db, current, conversation_id)
    messages = await repository.list_messages(db, current.org_id, conversation.id)
    citations = await repository.list_citations(db, current.org_id, [m.id for m in messages])
    # Citações antigas não reabrem acesso: documento excluído ou de coleção que o usuário
    # deixou de acessar aparece como indisponível, sem o trecho.
    titles = await repository.accessible_documents(
        db, current, list({citation.document_id for citation in citations})
    )
    by_message: dict[UUID, list[CitationOut]] = {}
    for citation in citations:
        by_message.setdefault(citation.message_id, []).append(_citation_out(citation, titles))
    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[_message_out(message, by_message.get(message.id, [])) for message in messages],
    )


def _citation_out(citation: Citation, accessible: dict[UUID, str]) -> CitationOut:
    title = accessible.get(citation.document_id)
    return CitationOut(
        marker=citation.marker,
        document_id=citation.document_id,
        document_title=title,
        page=citation.page if title else None,
        quote=citation.quote if title else None,
        available=title is not None,
    )


def _message_out(message: Message, citations: list[CitationOut]) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        status=message.status,
        answered=message.answered,
        created_at=message.created_at,
        citations=citations,
    )


async def ensure_can_ask(
    db: AsyncSession,
    current: CurrentUser,
    conversation_id: UUID,
    question: str,
    settings: Settings,
) -> None:
    """Validações feitas antes de abrir o streaming, para virarem respostas HTTP normais."""
    await _owned(db, current, conversation_id)
    if len(question) > settings.chat_max_question_chars:
        raise DomainError(
            f"A pergunta passa do limite de {settings.chat_max_question_chars} caracteres."
        )
    is_demo = await db.scalar(select(Organization.is_demo).where(Organization.id == current.org_id))
    limit = settings.chat_demo_questions_per_hour if is_demo else settings.chat_questions_per_hour
    asked = await repository.count_recent_questions(db, current, _now() - timedelta(hours=1))
    if asked >= limit:
        raise RateLimitedError("Você atingiu o limite de perguntas por hora. Tente mais tarde.")


def _source_out(source: Source) -> dict[str, Any]:
    chunk = source.chunk
    return SourceOut(
        marker=source.marker,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        page=chunk.page,
        snippet=chunk.content[:SNIPPET_CHARS],
    ).model_dump(mode="json")


async def stream_answer(
    ctx: ChatContext,
    current: CurrentUser,
    conversation_id: UUID,
    question: str,
    client: ClientInfo,
) -> AsyncIterator[str]:
    """Eventos SSE: `sources` (fontes recuperadas), `token` (texto da resposta conforme é
    gerado), `done` (mensagem final, com citações validadas) ou `error`."""
    started = time.perf_counter()
    async with ctx.sessionmaker() as db:
        await set_tenant(db, current.org_id, current.user_id)
        conversation = await _owned(db, current, conversation_id)
        history = [
            Turn("Usuário" if message.role == MessageRole.USER else "Assistente", message.content)
            for message in (await repository.list_messages(db, current.org_id, conversation.id))[
                -HISTORY_MESSAGES:
            ]
            if message.status == MessageStatus.COMPLETE
        ]

        db.add(
            Message(
                org_id=current.org_id,
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=question,
            )
        )
        conversation.title = conversation.title or question[:120]
        conversation.updated_at = _now()
        audit.record(
            db,
            org_id=current.org_id,
            actor_id=current.user_id,
            action="chat.question",
            resource_type="conversation",
            resource_id=conversation.id,
            ip=client.ip,
            details={"chars": len(question)},
        )
        await db.commit()

        try:
            question_vector = await ctx.embedder.embed_query(question)
            candidates = await hybrid_search(db, current, question, question_vector, ctx.settings)
        except EmbeddingError:
            logger.exception("Falha ao gerar o embedding da pergunta")
            async for event in _fail(db, current, conversation, "A busca está indisponível agora."):
                yield event
            return

        found = relevant(candidates, ctx.settings.retrieval_min_similarity)
        sources = select_sources(
            found, ctx.settings.retrieval_max_sources, ctx.settings.retrieval_max_context_chars
        )
        yield sse("sources", [_source_out(source) for source in sources])

        model: str | None = None
        if not sources:
            final = FinalAnswer(NOT_FOUND_ANSWER, [], answered=False)
            yield sse("token", {"text": NOT_FOUND_ANSWER})
        else:
            model = ctx.answerer.model
            raw: list[str] = []
            try:
                async for delta in ctx.answerer.stream(build_prompt(question, sources, history)):
                    raw.append(delta)
                    yield sse("token", {"text": delta})
            except AnswerError as exc:
                logger.warning("Falha do provedor de respostas", extra={"error": exc.message})
                async for event in _fail(db, current, conversation, exc.message):
                    yield event
                return
            final = finalize_answer("".join(raw), len(sources))

        message = Message(
            org_id=current.org_id,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=final.text,
            answered=final.answered,
            model=model,
            latency_ms=round((time.perf_counter() - started) * 1000),
            details={
                "candidates": len(candidates),
                "relevant": len(found),
                "sources": len(sources),
                "top_similarity": max((c.similarity or 0.0 for c in candidates), default=None),
            },
        )
        db.add(message)
        await db.flush()
        by_marker = {source.marker: source for source in sources}
        citations = [
            Citation(
                org_id=current.org_id,
                message_id=message.id,
                marker=marker,
                chunk_id=by_marker[marker].chunk.chunk_id,
                document_id=by_marker[marker].chunk.document_id,
                page=by_marker[marker].chunk.page,
                quote=by_marker[marker].chunk.content,
                score=by_marker[marker].chunk.score,
            )
            for marker in final.markers
        ]
        db.add_all(citations)
        await db.commit()

        titles = {source.chunk.document_id: source.chunk.document_title for source in sources}
        done = _message_out(message, [_citation_out(citation, titles) for citation in citations])
        yield sse("done", done.model_dump(mode="json"))


async def _fail(
    db: AsyncSession, current: CurrentUser, conversation: Conversation, detail: str
) -> AsyncIterator[str]:
    db.add(
        Message(
            org_id=current.org_id,
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=detail,
            status=MessageStatus.FAILED,
        )
    )
    await db.commit()
    yield sse("error", {"detail": detail})

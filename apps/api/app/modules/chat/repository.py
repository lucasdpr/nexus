"""Consultas de conversas. Cada conversa só é visível para quem a criou."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.identity import CurrentUser
from app.modules.chat.models import Citation, Conversation, Message, MessageRole
from app.modules.collections.repository import collection_access
from app.modules.documents.models import Document


async def list_owned(db: AsyncSession, current: CurrentUser, limit: int) -> Sequence[Conversation]:
    query = (
        select(Conversation)
        .where(Conversation.org_id == current.org_id, Conversation.user_id == current.user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return (await db.scalars(query)).all()


async def get_owned(
    db: AsyncSession, current: CurrentUser, conversation_id: UUID
) -> Conversation | None:
    return await db.scalar(
        select(Conversation).where(
            Conversation.org_id == current.org_id,
            Conversation.user_id == current.user_id,
            Conversation.id == conversation_id,
        )
    )


async def list_messages(db: AsyncSession, org_id: UUID, conversation_id: UUID) -> Sequence[Message]:
    query = (
        select(Message)
        .where(Message.org_id == org_id, Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
    )
    return (await db.scalars(query)).all()


async def list_citations(
    db: AsyncSession, org_id: UUID, message_ids: Sequence[UUID]
) -> Sequence[Citation]:
    if not message_ids:
        return []
    query = (
        select(Citation)
        .where(Citation.org_id == org_id, Citation.message_id.in_(message_ids))
        .order_by(Citation.marker)
    )
    return (await db.scalars(query)).all()


async def accessible_documents(
    db: AsyncSession, current: CurrentUser, document_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """Títulos dos documentos que o usuário ainda pode ler, para filtrar citações antigas."""
    if not document_ids:
        return {}
    rows = await db.execute(
        select(Document.id, Document.title).where(
            Document.org_id == current.org_id,
            Document.id.in_(document_ids),
            Document.deleted_at.is_(None),
            collection_access(Document.collection_id, current),
        )
    )
    return {row.id: row.title for row in rows}


async def count_recent_questions(db: AsyncSession, current: CurrentUser, since: datetime) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.org_id == current.org_id,
            Conversation.user_id == current.user_id,
            Message.role == MessageRole.USER,
            Message.created_at >= since,
        )
    )
    return count or 0

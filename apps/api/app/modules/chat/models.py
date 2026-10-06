from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, CreatedAtMixin, IdMixin, str_enum


class MessageRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class MessageStatus(StrEnum):
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class Conversation(IdMixin, CreatedAtMixin, Base):
    """Conversa com o assistente. Visível só para quem a criou."""

    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_owner_updated", "org_id", "user_id", "updated_at"),)

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(120))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Message(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    role: Mapped[MessageRole] = mapped_column(str_enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(
        str_enum(MessageStatus), default=MessageStatus.COMPLETE
    )
    # Só em respostas: se houve resposta fundamentada em fontes (alimenta "perguntas sem resposta").
    answered: Mapped[bool | None]
    model: Mapped[str | None] = mapped_column(String(64))
    latency_ms: Mapped[int | None]
    # Métricas da recuperação (candidatos, fontes usadas, melhor similaridade).
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Citation(IdMixin, Base):
    """Fonte citada numa resposta, com o trecho guardado como estava no momento da resposta."""

    __tablename__ = "citations"
    __table_args__ = (Index("ix_citations_message", "message_id"),)

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    message_id: Mapped[UUID] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"))
    marker: Mapped[int]
    # O trecho some se o documento for reprocessado; a citação continua apontando o documento.
    chunk_id: Mapped[UUID | None] = mapped_column(ForeignKey("chunks.id", ondelete="SET NULL"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"))
    page: Mapped[int | None]
    quote: Mapped[str] = mapped_column(Text)
    score: Mapped[float]

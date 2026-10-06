import json
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.modules.chat.models import MessageRole, MessageStatus


class AskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]


class CitationOut(BaseModel):
    marker: int
    document_id: UUID
    # Trecho citado, para o visualizador grifá-lo; None se o documento foi reprocessado.
    chunk_id: UUID | None
    # None quando o usuário não tem mais acesso ao documento ou ele foi excluído.
    document_title: str | None
    page: int | None
    quote: str | None
    available: bool


class MessageOut(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    status: MessageStatus
    answered: bool | None
    created_at: datetime
    citations: list[CitationOut]


class ConversationOut(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class SourceOut(BaseModel):
    """Fonte recuperada antes da resposta, enviada no evento `sources` do streaming."""

    marker: int
    document_id: UUID
    chunk_id: UUID
    document_title: str
    page: int | None
    snippet: str


def sse(event: str, data: Any) -> str:
    """Formata um evento Server-Sent Events."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

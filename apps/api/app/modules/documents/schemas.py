from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.modules.documents.models import DocumentKind, DocumentStatus, StepName, StepStatus


class Ref(BaseModel):
    id: UUID
    name: str


class DocumentOut(BaseModel):
    id: UUID
    title: str
    filename: str
    kind: DocumentKind
    size_bytes: int
    status: DocumentStatus
    error: str | None
    page_count: int | None
    chunk_count: int
    collection: Ref
    uploaded_by: Ref
    created_at: datetime
    processed_at: datetime | None


class StepOut(BaseModel):
    step: StepName
    status: StepStatus
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    details: dict[str, Any]


class DocumentDetail(DocumentOut):
    mime_type: str
    sha256: str
    version: int
    steps: list[StepOut]


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ordinal: int
    page: int | None
    content: str


class DocumentPage(BaseModel):
    items: list[DocumentOut]
    total: int
    limit: int
    offset: int


SortField = Literal["created_at", "title", "size"]
SortOrder = Literal["asc", "desc"]

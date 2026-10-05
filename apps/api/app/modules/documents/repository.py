"""Consultas de documentos. Todas filtram por organização e pela regra de acesso por coleção."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import Row, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.identity import CurrentUser
from app.modules.collections.models import Collection
from app.modules.collections.repository import collection_access
from app.modules.documents.models import (
    Document,
    DocumentKind,
    DocumentStatus,
    ProcessingStep,
    StepName,
)
from app.modules.documents.schemas import SortField, SortOrder
from app.modules.users.models import User

DocumentRow = Row[Document, str, str]

_STEP_ORDER = {step: index for index, step in enumerate(StepName)}

_SORT_COLUMNS: dict[SortField, Any] = {
    "created_at": Document.created_at,
    "title": Document.title,
    "size": Document.size_bytes,
}


@dataclass(frozen=True, slots=True)
class DocumentFilters:
    collection_id: UUID | None = None
    status: DocumentStatus | None = None
    kind: DocumentKind | None = None
    q: str | None = None


def _visible(current: CurrentUser) -> Select[Document]:
    return select(Document).where(
        Document.org_id == current.org_id,
        Document.deleted_at.is_(None),
        collection_access(Document.collection_id, current),
    )


def _with_names(query: Select[Document]) -> Select[Document, str, str]:
    return (
        query.add_columns(Collection.name, User.name)
        .join(Collection, Collection.id == Document.collection_id)
        .join(User, User.id == Document.uploaded_by)
    )


async def list_documents(
    db: AsyncSession,
    current: CurrentUser,
    filters: DocumentFilters,
    *,
    sort: SortField,
    order: SortOrder,
    limit: int,
    offset: int,
) -> tuple[Sequence[DocumentRow], int]:
    query = _visible(current)
    if filters.collection_id:
        query = query.where(Document.collection_id == filters.collection_id)
    if filters.status:
        query = query.where(Document.status == filters.status)
    if filters.kind:
        query = query.where(Document.kind == filters.kind)
    if filters.q:
        query = query.where(Document.title.icontains(filters.q, autoescape=True))

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    column = _SORT_COLUMNS[sort]
    ordered = _with_names(query).order_by(
        column.asc() if order == "asc" else column.desc(), Document.id
    )
    rows = (await db.execute(ordered.limit(limit).offset(offset))).all()
    return rows, total


async def get_visible(
    db: AsyncSession, current: CurrentUser, document_id: UUID
) -> DocumentRow | None:
    query = _with_names(_visible(current).where(Document.id == document_id))
    return (await db.execute(query)).one_or_none()


async def find_active_by_hash(db: AsyncSession, org_id: UUID, sha256: str) -> Document | None:
    return await db.scalar(
        select(Document).where(
            Document.org_id == org_id, Document.sha256 == sha256, Document.deleted_at.is_(None)
        )
    )


async def list_steps(db: AsyncSession, org_id: UUID, document_id: UUID) -> Sequence[ProcessingStep]:
    query = select(ProcessingStep).where(
        ProcessingStep.org_id == org_id, ProcessingStep.document_id == document_id
    )
    steps = (await db.scalars(query)).all()
    return sorted(steps, key=lambda step: _STEP_ORDER[step.step])

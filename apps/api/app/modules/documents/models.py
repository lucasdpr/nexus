from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Computed, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.ai.embeddings import EMBEDDING_DIMENSIONS
from app.core.models import Base, CreatedAtMixin, IdMixin, str_enum


class DocumentKind(StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MD = "MD"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class StepName(StrEnum):
    UPLOAD = "UPLOAD"
    EXTRACT = "EXTRACT"
    CHUNK = "CHUNK"
    EMBED = "EMBED"
    INDEX = "INDEX"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class Document(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        # O mesmo arquivo não entra duas vezes na organização (excluídos não contam).
        Index(
            "uq_documents_org_sha256_active",
            "org_id",
            "sha256",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_documents_org_collection_created", "org_id", "collection_id", "created_at"),
    )

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id"))
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[DocumentKind] = mapped_column(str_enum(DocumentKind))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(255))
    status: Mapped[DocumentStatus] = mapped_column(
        str_enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )
    error: Mapped[str | None] = mapped_column(String(500))
    page_count: Mapped[int | None]
    chunk_count: Mapped[int] = mapped_column(default=0)
    version: Mapped[int] = mapped_column(default=1)
    details: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProcessingStep(IdMixin, Base):
    """Uma linha por etapa do pipeline: é o que a interface mostra durante o processamento."""

    __tablename__ = "processing_steps"
    __table_args__ = (
        Index("uq_processing_steps_document_step", "document_id", "step", unique=True),
    )

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    step: Mapped[StepName] = mapped_column(str_enum(StepName))
    status: Mapped[StepStatus] = mapped_column(str_enum(StepStatus), default=StepStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(500))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Chunk(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("uq_chunks_document_ordinal", "document_id", "ordinal", unique=True),
        Index("ix_chunks_org_collection", "org_id", "collection_id"),
    )

    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    # Copiado do documento: a busca filtra por coleção sem precisar de join.
    collection_id: Mapped[UUID] = mapped_column(ForeignKey("collections.id"))
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    ordinal: Mapped[int]
    page: Mapped[int | None]
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    embedding_model: Mapped[str] = mapped_column(String(64))
    tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('portuguese', immutable_unaccent(content))", persisted=True),
        deferred=True,
    )

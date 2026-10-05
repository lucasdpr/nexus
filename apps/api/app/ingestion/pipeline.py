"""Pipeline de ingestão: EXTRAÇÃO → DIVISÃO → EMBEDDINGS → INDEXAÇÃO.

Cada etapa grava o próprio estado em `processing_steps`, que é o que a interface mostra.
Falhas definitivas (`PipelineError`: arquivo corrompido, sem texto...) encerram o documento
como FAILED. As demais (rede, provedor de embeddings) sobem para o worker, que tenta de novo.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embeddings import EmbeddingProvider
from app.core.config import Settings
from app.core.db import set_tenant
from app.ingestion.chunking import ChunkingConfig, chunk_pages
from app.ingestion.errors import PipelineError
from app.ingestion.extraction import extract_text
from app.jobs.worker import JobHandler, Payload
from app.modules.documents.models import (
    Chunk,
    Document,
    DocumentStatus,
    ProcessingStep,
    StepName,
    StepStatus,
)
from app.storage import Storage

logger = logging.getLogger(__name__)

JOB_PROCESS_DOCUMENT = "document.process"
PIPELINE_STEPS = (StepName.EXTRACT, StepName.CHUNK, StepName.EMBED, StepName.INDEX)
UNEXPECTED_STEP_ERROR = "Erro inesperado nesta etapa."
GAVE_UP_ERROR = "Falha temporária ao processar o documento. Tente reprocessar mais tarde."


@dataclass(frozen=True, slots=True)
class IngestionContext:
    sessionmaker: async_sessionmaker[AsyncSession]
    storage: Storage
    embedder: EmbeddingProvider
    settings: Settings


def chunking_config(settings: Settings) -> ChunkingConfig:
    return ChunkingConfig(
        target_chars=settings.chunk_target_chars,
        max_chars=settings.chunk_max_chars,
        overlap_chars=settings.chunk_overlap_chars,
    )


def job_handlers(ctx: IngestionContext) -> dict[str, JobHandler]:
    async def run(payload: Payload) -> None:
        await process_document(ctx, UUID(payload["org_id"]), UUID(payload["document_id"]))

    async def give_up(payload: Payload) -> None:
        await mark_failed(ctx, UUID(payload["org_id"]), UUID(payload["document_id"]), GAVE_UP_ERROR)

    return {JOB_PROCESS_DOCUMENT: JobHandler(run=run, on_give_up=give_up)}


def _now() -> datetime:
    return datetime.now(UTC)


async def process_document(ctx: IngestionContext, org_id: UUID, document_id: UUID) -> None:
    async with ctx.sessionmaker() as db:
        await set_tenant(db, org_id)
        document = await db.scalar(
            select(Document).where(
                Document.org_id == org_id,
                Document.id == document_id,
                Document.deleted_at.is_(None),
            )
        )
        if document is None:
            logger.info("Documento excluído antes do processamento", extra={"id": str(document_id)})
            return

        await _begin(db, document)
        try:
            await _run_steps(db, ctx, document)
        except PipelineError as exc:
            await db.refresh(document)
            document.status = DocumentStatus.FAILED
            document.error = exc.message
            await db.commit()


async def _begin(db: AsyncSession, document: Document) -> None:
    document.status = DocumentStatus.PROCESSING
    document.error = None
    await db.execute(
        update(ProcessingStep)
        .where(
            ProcessingStep.org_id == document.org_id,
            ProcessingStep.document_id == document.id,
            ProcessingStep.step.in_(PIPELINE_STEPS),
        )
        .values(status=StepStatus.PENDING, started_at=None, finished_at=None, error=None)
    )
    await db.commit()


async def _run_steps(db: AsyncSession, ctx: IngestionContext, document: Document) -> None:
    data = await ctx.storage.get(document.storage_key)

    async with _step(db, document, StepName.EXTRACT) as details:
        extraction = await asyncio.to_thread(
            extract_text, document.kind, data, ctx.settings.max_pdf_pages
        )
        details["pages_with_text"] = len(extraction.pages)

    async with _step(db, document, StepName.CHUNK) as details:
        drafts = await asyncio.to_thread(
            chunk_pages, extraction.pages, chunking_config(ctx.settings)
        )
        details["chunks"] = len(drafts)

    async with _step(db, document, StepName.EMBED) as details:
        vectors = await ctx.embedder.embed_documents([draft.content for draft in drafts])
        details["model"] = ctx.embedder.model

    async with _step(db, document, StepName.INDEX):
        # O documento pode ter sido excluído durante a extração ou os embeddings. A trava na
        # linha (a mesma da exclusão) torna a checagem e a gravação atômicas.
        await db.refresh(document, with_for_update=True)
        if document.deleted_at is not None:
            logger.info(
                "Documento excluído durante o processamento", extra={"id": str(document.id)}
            )
            return

        # Reprocessamento: os trechos antigos saem na mesma transação em que os novos entram.
        await db.execute(
            delete(Chunk).where(Chunk.org_id == document.org_id, Chunk.document_id == document.id)
        )
        db.add_all(
            Chunk(
                org_id=document.org_id,
                collection_id=document.collection_id,
                document_id=document.id,
                ordinal=draft.ordinal,
                page=draft.page,
                content=draft.content,
                token_count=draft.token_estimate,
                embedding=vector,
                embedding_model=ctx.embedder.model,
            )
            for draft, vector in zip(drafts, vectors, strict=True)
        )
        document.status = DocumentStatus.READY
        document.page_count = extraction.page_count
        document.chunk_count = len(drafts)
        document.processed_at = _now()


@asynccontextmanager
async def _step(
    db: AsyncSession, document: Document, name: StepName
) -> AsyncIterator[dict[str, Any]]:
    record = await db.scalar(
        select(ProcessingStep).where(
            ProcessingStep.org_id == document.org_id,
            ProcessingStep.document_id == document.id,
            ProcessingStep.step == name,
        )
    )
    if record is None:
        raise RuntimeError(f"Etapa {name} não encontrada para o documento {document.id}.")
    record.status = StepStatus.RUNNING
    record.started_at = _now()
    await db.commit()

    details: dict[str, Any] = {}
    try:
        yield details
    except Exception as exc:
        await db.rollback()
        await db.refresh(record)
        record.status = StepStatus.FAILED
        record.finished_at = _now()
        record.error = exc.message if isinstance(exc, PipelineError) else UNEXPECTED_STEP_ERROR
        await db.commit()
        raise

    record.status = StepStatus.DONE
    record.finished_at = _now()
    record.details = details
    await db.commit()


async def mark_failed(ctx: IngestionContext, org_id: UUID, document_id: UUID, error: str) -> None:
    async with ctx.sessionmaker() as db:
        await set_tenant(db, org_id)
        await db.execute(
            update(Document)
            .where(Document.org_id == org_id, Document.id == document_id)
            .values(status=DocumentStatus.FAILED, error=error)
        )
        await db.commit()

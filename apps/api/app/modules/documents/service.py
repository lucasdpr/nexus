import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import PurePath
from uuid import UUID, uuid7

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.ingestion.detection import MIME_TYPES, detect_kind
from app.ingestion.pipeline import JOB_PROCESS_DOCUMENT, PIPELINE_STEPS
from app.jobs import queue
from app.modules.audit import service as audit
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.collections import repository as collections
from app.modules.documents import repository
from app.modules.documents.models import (
    Chunk,
    Document,
    DocumentStatus,
    ProcessingStep,
    StepName,
    StepStatus,
)
from app.modules.documents.repository import DocumentRow
from app.modules.documents.schemas import DocumentDetail, DocumentOut, Ref, StepOut
from app.modules.users.models import Role
from app.storage import Storage

logger = logging.getLogger(__name__)

NOT_FOUND = "Documento não encontrado."
DUPLICATE = "Este arquivo já foi enviado para esta coleção."
CANNOT_MANAGE = "Você não tem permissão para gerenciar documentos desta coleção."
_UNSAFE_FILENAME_CHARS = re.compile(r'[\x00-\x1f\x7f"\\/]')


def _safe_filename(filename: str) -> str:
    name = _UNSAFE_FILENAME_CHARS.sub("", PurePath(filename.replace("\\", "/")).name).strip()
    return name[:255] or "documento"


def _ensure_can_manage(current: CurrentUser) -> None:
    """Gerenciar documentos exige ADMIN, ou MANAGER que integra a coleção (a visibilidade da
    coleção já garante a participação)."""
    if current.role == Role.MEMBER:
        raise ForbiddenError(CANNOT_MANAGE)


def _enqueue_processing(db: AsyncSession, document: Document, settings: Settings) -> None:
    queue.enqueue(
        db,
        JOB_PROCESS_DOCUMENT,
        {"org_id": str(document.org_id), "document_id": str(document.id)},
        max_attempts=settings.job_max_attempts,
    )


async def upload(
    db: AsyncSession,
    storage: Storage,
    current: CurrentUser,
    *,
    collection_id: UUID,
    filename: str,
    data: bytes,
    title: str | None,
    client: ClientInfo,
    settings: Settings,
) -> Document:
    if await collections.get_visible(db, current, collection_id) is None:
        raise NotFoundError("Coleção não encontrada.")
    _ensure_can_manage(current)

    kind = detect_kind(filename, data)
    sha256 = hashlib.sha256(data).hexdigest()
    if await repository.find_active_by_hash(db, current.org_id, collection_id, sha256):
        raise ConflictError(DUPLICATE)

    safe_name = _safe_filename(filename)
    document_id = uuid7()
    document = Document(
        id=document_id,
        org_id=current.org_id,
        collection_id=collection_id,
        uploaded_by=current.user_id,
        title=(title or "").strip()[:200] or PurePath(safe_name).stem[:200] or safe_name,
        filename=safe_name,
        kind=kind,
        mime_type=MIME_TYPES[kind],
        size_bytes=len(data),
        sha256=sha256,
        # Chave gerada pela aplicação: o nome enviado pelo usuário nunca vira caminho.
        storage_key=f"{current.org_id}/{document_id}",
    )
    await storage.put(document.storage_key, data)

    db.add(document)
    now = datetime.now(UTC)
    db.add(
        ProcessingStep(
            org_id=current.org_id,
            document_id=document_id,
            step=StepName.UPLOAD,
            status=StepStatus.DONE,
            started_at=now,
            finished_at=now,
            details={"size_bytes": len(data), "kind": kind.value},
        )
    )
    db.add_all(
        ProcessingStep(org_id=current.org_id, document_id=document_id, step=step)
        for step in PIPELINE_STEPS
    )
    _enqueue_processing(db, document, settings)
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=document_id,
        ip=client.ip,
        details={
            "filename": safe_name,
            "size_bytes": len(data),
            "collection_id": str(collection_id),
        },
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        # Envio simultâneo do mesmo arquivo: o índice único decide, e o arquivo órfão sai.
        await db.rollback()
        await storage.delete(document.storage_key)
        raise ConflictError(DUPLICATE) from exc
    except Exception:
        await storage.delete(document.storage_key)
        raise
    return document


async def _get_row(db: AsyncSession, current: CurrentUser, document_id: UUID) -> DocumentRow:
    row = await repository.get_visible(db, current, document_id)
    if row is None:
        raise NotFoundError(NOT_FOUND)
    return row


def to_out(row: DocumentRow) -> DocumentOut:
    document, collection_name, uploader_name = row
    return DocumentOut(
        id=document.id,
        title=document.title,
        filename=document.filename,
        kind=document.kind,
        size_bytes=document.size_bytes,
        status=document.status,
        error=document.error,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        collection=Ref(id=document.collection_id, name=collection_name),
        uploaded_by=Ref(id=document.uploaded_by, name=uploader_name),
        created_at=document.created_at,
        processed_at=document.processed_at,
    )


async def get_detail(db: AsyncSession, current: CurrentUser, document_id: UUID) -> DocumentDetail:
    row = await _get_row(db, current, document_id)
    document = row[0]
    steps = await repository.list_steps(db, current.org_id, document.id)
    return DocumentDetail(
        **to_out(row).model_dump(),
        mime_type=document.mime_type,
        sha256=document.sha256,
        version=document.version,
        steps=[
            StepOut(
                step=step.step,
                status=step.status,
                started_at=step.started_at,
                finished_at=step.finished_at,
                error=step.error,
                details=step.details,
            )
            for step in steps
        ],
    )


async def download(
    db: AsyncSession,
    storage: Storage,
    current: CurrentUser,
    document_id: UUID,
    client: ClientInfo,
) -> tuple[Document, bytes]:
    document = (await _get_row(db, current, document_id))[0]
    data = await storage.get(document.storage_key)
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="document.downloaded",
        resource_type="document",
        resource_id=document.id,
        ip=client.ip,
    )
    await db.commit()
    return document, data


async def delete_document(
    db: AsyncSession,
    storage: Storage,
    current: CurrentUser,
    document_id: UUID,
    client: ClientInfo,
) -> None:
    document = (await _get_row(db, current, document_id))[0]
    _ensure_can_manage(current)

    # Mesma trava da indexação: ou o worker termina antes e seus trechos são apagados aqui,
    # ou ele vê o documento já excluído e não grava nada.
    await db.refresh(document, with_for_update=True)
    if document.deleted_at is not None:
        raise NotFoundError(NOT_FOUND)

    # A linha fica como registro (auditoria); trechos e arquivo saem de verdade.
    document.deleted_at = datetime.now(UTC)
    await db.execute(
        delete(Chunk).where(Chunk.org_id == current.org_id, Chunk.document_id == document.id)
    )
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="document.deleted",
        resource_type="document",
        resource_id=document.id,
        ip=client.ip,
        details={"title": document.title},
    )
    await db.commit()
    try:
        await storage.delete(document.storage_key)
    except OSError:
        logger.exception("Falha ao apagar arquivo", extra={"document_id": str(document.id)})


async def reprocess(
    db: AsyncSession,
    current: CurrentUser,
    document_id: UUID,
    client: ClientInfo,
    settings: Settings,
) -> None:
    document = (await _get_row(db, current, document_id))[0]
    _ensure_can_manage(current)
    if document.status not in {DocumentStatus.READY, DocumentStatus.FAILED}:
        raise ConflictError("O documento já está na fila de processamento.")

    await db.execute(
        update(Document)
        .where(Document.org_id == current.org_id, Document.id == document.id)
        .values(status=DocumentStatus.UPLOADED, error=None)
    )
    _enqueue_processing(db, document, settings)
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="document.reprocessed",
        resource_type="document",
        resource_id=document.id,
        ip=client.ip,
    )
    await db.commit()

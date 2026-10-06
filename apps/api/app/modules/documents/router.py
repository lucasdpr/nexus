from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile, status

from app.core.errors import PayloadTooLargeError
from app.modules.auth.dependencies import Client, CurrentUserDep, DbSession, SettingsDep
from app.modules.documents import repository, service
from app.modules.documents.models import DocumentKind, DocumentStatus
from app.modules.documents.repository import DocumentFilters
from app.modules.documents.schemas import (
    ChunkOut,
    DocumentDetail,
    DocumentPage,
    SortField,
    SortOrder,
)
from app.storage import Storage

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def get_storage(request: Request) -> Storage:
    storage: Storage = request.app.state.storage
    return storage


StorageDep = Annotated[Storage, Depends(get_storage)]


def _content_disposition(filename: str) -> str:
    ascii_name = filename.encode("ascii", "replace").decode().replace("?", "_")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    current: CurrentUserDep,
    client: Client,
    settings: SettingsDep,
    storage: StorageDep,
    file: Annotated[UploadFile, File()],
    collection_id: Annotated[UUID, Form()],
    title: Annotated[str | None, Form(max_length=200)] = None,
) -> DocumentDetail:
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise PayloadTooLargeError(f"O arquivo passa do limite de {settings.max_upload_mb} MB.")
    document = await service.upload(
        db,
        storage,
        current,
        collection_id=collection_id,
        filename=file.filename or "documento",
        data=data,
        title=title,
        client=client,
        settings=settings,
    )
    return await service.get_detail(db, current, document.id)


@router.get("")
async def list_documents(
    db: DbSession,
    current: CurrentUserDep,
    collection_id: UUID | None = None,
    status_filter: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    kind: DocumentKind | None = None,
    q: Annotated[str | None, Query(max_length=200)] = None,
    sort: SortField = "created_at",
    order: SortOrder = "desc",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentPage:
    filters = DocumentFilters(collection_id=collection_id, status=status_filter, kind=kind, q=q)
    rows, total = await repository.list_documents(
        db, current, filters, sort=sort, order=order, limit=limit, offset=offset
    )
    return DocumentPage(
        items=[service.to_out(row) for row in rows], total=total, limit=limit, offset=offset
    )


@router.get("/{document_id}")
async def get_document(document_id: UUID, db: DbSession, current: CurrentUserDep) -> DocumentDetail:
    return await service.get_detail(db, current, document_id)


@router.get("/{document_id}/chunks")
async def list_document_chunks(
    document_id: UUID, db: DbSession, current: CurrentUserDep
) -> list[ChunkOut]:
    """Texto indexado, na ordem: usado pelo visualizador de formatos sem páginas."""
    chunks = await service.get_chunks(db, current, document_id)
    return [ChunkOut.model_validate(chunk) for chunk in chunks]


@router.get("/{document_id}/chunks/{chunk_id}")
async def get_document_chunk(
    document_id: UUID, chunk_id: UUID, db: DbSession, current: CurrentUserDep
) -> ChunkOut:
    """Um trecho citado: o visualizador o grifa na página certa."""
    chunks = await service.get_chunks(db, current, document_id, chunk_id)
    return ChunkOut.model_validate(chunks[0])


@router.get("/{document_id}/file")
async def download_document(
    document_id: UUID, db: DbSession, current: CurrentUserDep, client: Client, storage: StorageDep
) -> Response:
    document, data = await service.download(db, storage, current, document_id, client)
    return Response(
        content=data,
        media_type=document.mime_type,
        headers={
            "Content-Disposition": _content_disposition(document.filename),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID, db: DbSession, current: CurrentUserDep, client: Client, storage: StorageDep
) -> None:
    await service.delete_document(db, storage, current, document_id, client)


@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: UUID,
    db: DbSession,
    current: CurrentUserDep,
    client: Client,
    settings: SettingsDep,
) -> DocumentDetail:
    await service.reprocess(db, current, document_id, client, settings)
    return await service.get_detail(db, current, document_id)

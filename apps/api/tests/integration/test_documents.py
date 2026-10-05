"""Upload, pipeline de ingestão e acesso a documentos, de ponta a ponta com banco real."""

from collections.abc import Sequence
from dataclasses import replace
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx2 import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embeddings import EmbeddingError
from app.core.config import get_settings
from app.core.db import set_tenant
from app.ingestion.pipeline import GAVE_UP_ERROR, IngestionContext, job_handlers
from app.jobs.worker import Worker
from app.modules.documents.models import Chunk
from tests.conftest import ClientFactory
from tests.files import make_docx, make_pdf
from tests.integration.support import Account, add_user, signup

pytestmark = pytest.mark.anyio

MANUAL = make_pdf(
    [
        "Manual do Compressor CX-200\nInstale o equipamento em área ventilada.",
        "Garantia\nO prazo de garantia é de 24 meses a partir da data de instalação.",
    ]
)


async def _collection(admin: Account, name: str = "Engenharia") -> str:
    response = await admin.client.post("/api/v1/collections", json={"name": name})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _upload(
    client: AsyncClient, collection_id: str, filename: str, data: bytes, title: str | None = None
) -> Response:
    form = {"collection_id": collection_id} | ({"title": title} if title else {})
    return await client.post(
        "/api/v1/documents", data=form, files={"file": (filename, data, "application/octet-stream")}
    )


async def _chunks(app: FastAPI, org_id: str, document_id: str) -> Sequence[Chunk]:
    sessionmaker: async_sessionmaker[AsyncSession] = app.state.sessionmaker
    async with sessionmaker() as db:
        await set_tenant(db, UUID(org_id))
        query = select(Chunk).where(Chunk.document_id == UUID(document_id)).order_by(Chunk.ordinal)
        return (await db.scalars(query)).all()


def _steps(document: dict[str, Any]) -> dict[str, str]:
    return {step["step"]: step["status"] for step in document["steps"]}


async def test_pdf_is_processed_into_chunks_that_keep_their_page(
    app: FastAPI, make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    collection_id = await _collection(admin)

    uploaded = await _upload(admin.client, collection_id, "manual-cx200.pdf", MANUAL)
    assert uploaded.status_code == 201, uploaded.text
    document = uploaded.json()
    assert document["status"] == "UPLOADED"
    assert document["title"] == "manual-cx200"
    assert _steps(document) == {
        "UPLOAD": "DONE",
        "EXTRACT": "PENDING",
        "CHUNK": "PENDING",
        "EMBED": "PENDING",
        "INDEX": "PENDING",
    }

    await worker.run_until_empty()

    processed = (await admin.client.get(f"/api/v1/documents/{document['id']}")).json()
    assert processed["status"] == "READY"
    assert processed["page_count"] == 2
    assert set(_steps(processed).values()) == {"DONE"}
    chunks = await _chunks(app, admin.org_id, document["id"])
    warranty = [chunk for chunk in chunks if "24 meses" in chunk.content]
    assert [chunk.page for chunk in warranty] == [2]
    assert all(chunk.embedding_model == "hashing-v1" for chunk in chunks)


async def test_docx_and_markdown_are_indexed_without_pages(
    app: FastAPI, make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    policy = make_docx(
        ["Política de Segurança", "O uso de capacete é obrigatório na área de produção."],
        table=[["EPI", "Troca"], ["Luva de vaqueta", "30 dias"]],
    )

    docx_doc = (await _upload(admin.client, collection_id, "politica.docx", policy)).json()
    md_doc = (
        await _upload(admin.client, collection_id, "procedimento.md", b"# Bloqueio\nTrave a chave.")
    ).json()
    await worker.run_until_empty()

    for document_id in (docx_doc["id"], md_doc["id"]):
        processed = (await admin.client.get(f"/api/v1/documents/{document_id}")).json()
        assert processed["status"] == "READY", processed
        assert processed["page_count"] is None
    docx_chunks = await _chunks(app, admin.org_id, docx_doc["id"])
    assert "Luva de vaqueta | 30 dias" in docx_chunks[0].content
    assert all(chunk.page is None for chunk in docx_chunks)


async def test_same_file_twice_conflicts_until_the_first_is_deleted(
    app: FastAPI, make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    first = (await _upload(admin.client, collection_id, "manual.pdf", MANUAL)).json()
    await worker.run_until_empty()

    duplicate = await _upload(admin.client, collection_id, "copia.pdf", MANUAL)
    deleted = await admin.client.delete(f"/api/v1/documents/{first['id']}")
    listed = await admin.client.get("/api/v1/documents")
    resent = await _upload(admin.client, collection_id, "manual.pdf", MANUAL)

    assert duplicate.status_code == 409
    assert deleted.status_code == 204
    assert first["id"] not in {item["id"] for item in listed.json()["items"]}
    assert await _chunks(app, admin.org_id, first["id"]) == []
    assert resent.status_code == 201


async def test_only_admins_and_member_managers_can_upload(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    member = await add_user(admin, make_client, "MEMBER")
    outsider_manager = await add_user(admin, make_client, "MANAGER")
    await admin.client.post(
        f"/api/v1/collections/{collection_id}/members", json={"user_id": member.user_id}
    )

    by_member = await _upload(member.client, collection_id, "m.pdf", make_pdf(["Membro"]))
    by_outsider = await _upload(outsider_manager.client, collection_id, "g.pdf", make_pdf(["Fora"]))

    assert by_member.status_code == 403
    assert by_outsider.status_code == 404


async def test_disguised_and_oversized_files_are_rejected(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    oversized = b"%PDF-" + b"0" * (get_settings().max_upload_bytes + 2 * 1024 * 1024)

    disguised = await _upload(admin.client, collection_id, "nota.pdf", b"MZ\x90\x00programa")
    too_large = await _upload(admin.client, collection_id, "grande.pdf", oversized)

    assert disguised.status_code == 415
    assert too_large.status_code == 413


async def test_pdf_without_text_fails_once_with_a_clear_message(
    make_client: ClientFactory, worker: Worker
) -> None:
    await worker.run_until_empty()
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    scanned = (
        await _upload(admin.client, collection_id, "digitalizado.pdf", make_pdf([""]))
    ).json()

    processed_jobs = await worker.run_until_empty()

    document = (await admin.client.get(f"/api/v1/documents/{scanned['id']}")).json()
    assert processed_jobs == 1
    assert document["status"] == "FAILED"
    assert "OCR" in document["error"]
    assert _steps(document)["EXTRACT"] == "FAILED"


class _UnavailableEmbedder:
    model = "indisponivel"

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        raise EmbeddingError("Provedor fora do ar.")

    async def embed_query(self, text: str) -> list[float]:
        raise EmbeddingError("Provedor fora do ar.")

    async def aclose(self) -> None:
        return None


async def test_transient_failures_are_retried_and_then_reported(
    app: FastAPI, make_client: ClientFactory, worker: Worker, ingestion: IngestionContext
) -> None:
    await worker.run_until_empty()
    admin = await signup(make_client)
    collection_id = await _collection(admin)
    uploaded = (await _upload(admin.client, collection_id, "manual.pdf", MANUAL)).json()
    failing = replace(ingestion, embedder=_UnavailableEmbedder())

    attempts = await Worker(
        app.state.sessionmaker, job_handlers(failing), get_settings()
    ).run_until_empty()

    document = (await admin.client.get(f"/api/v1/documents/{uploaded['id']}")).json()
    assert attempts == get_settings().job_max_attempts
    assert document["status"] == "FAILED"
    assert document["error"] == GAVE_UP_ERROR
    assert _steps(document)["EMBED"] == "FAILED"


async def test_documents_are_isolated_between_organizations(
    app: FastAPI, make_client: ClientFactory, worker: Worker
) -> None:
    org_a = await signup(make_client, "Organização A")
    org_b = await signup(make_client, "Organização B")
    document = (await _upload(org_a.client, await _collection(org_a), "manual.pdf", MANUAL)).json()
    await worker.run_until_empty()
    path = f"/api/v1/documents/{document['id']}"

    listed = await org_b.client.get("/api/v1/documents")

    assert document["id"] not in {item["id"] for item in listed.json()["items"]}
    assert (await org_b.client.get(path)).status_code == 404
    assert (await org_b.client.get(f"{path}/file")).status_code == 404
    assert (await org_b.client.delete(path)).status_code == 404
    async with app.state.sessionmaker() as db:
        await set_tenant(db, UUID(org_b.org_id))
        visible_to_b = await db.scalar(
            select(func.count()).select_from(Chunk).where(Chunk.document_id == UUID(document["id"]))
        )
    assert visible_to_b == 0


async def test_members_only_see_documents_of_their_collections(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    engineering = await _collection(admin, "Engenharia")
    legal = await _collection(admin, "Jurídico")
    member = await add_user(admin, make_client, "MEMBER")
    await admin.client.post(
        f"/api/v1/collections/{engineering}/members", json={"user_id": member.user_id}
    )
    visible = (await _upload(admin.client, engineering, "manual.pdf", MANUAL)).json()
    hidden = (await _upload(admin.client, legal, "contrato.pdf", make_pdf(["Contrato"]))).json()

    listed = (await member.client.get("/api/v1/documents")).json()

    assert [item["id"] for item in listed["items"]] == [visible["id"]]
    assert (await member.client.get(f"/api/v1/documents/{hidden['id']}")).status_code == 404
    assert (await member.client.delete(f"/api/v1/documents/{visible['id']}")).status_code == 403


async def test_download_returns_the_original_bytes_as_an_attachment(
    make_client: ClientFactory,
) -> None:
    admin = await signup(make_client)
    document = (
        await _upload(admin.client, await _collection(admin), "Relatório Técnico.pdf", MANUAL)
    ).json()

    response = await admin.client.get(f"/api/v1/documents/{document['id']}/file")

    assert response.content == MANUAL
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["x-content-type-options"] == "nosniff"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "Relat%C3%B3rio%20T%C3%A9cnico.pdf" in disposition


async def test_ready_document_can_be_reprocessed(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    document = (await _upload(admin.client, await _collection(admin), "manual.pdf", MANUAL)).json()
    await worker.run_until_empty()

    queued = await admin.client.post(f"/api/v1/documents/{document['id']}/reprocess")
    queued_again = await admin.client.post(f"/api/v1/documents/{document['id']}/reprocess")
    await worker.run_until_empty()

    assert queued.status_code == 202
    assert queued_again.status_code == 409
    final = (await admin.client.get(f"/api/v1/documents/{document['id']}")).json()
    assert final["status"] == "READY"

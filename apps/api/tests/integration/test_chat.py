"""Assistente de ponta a ponta: busca com permissão, respostas com fontes e conversas."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import FastAPI
from httpx2 import AsyncClient

from app.ai.answers import AnswerPrompt
from app.core.config import get_settings
from app.jobs.worker import Worker
from app.rag.prompt import NOT_FOUND_ANSWER
from tests.conftest import ClientFactory
from tests.files import make_pdf
from tests.integration.support import Account, add_user, signup

pytestmark = pytest.mark.anyio

MANUAL = make_pdf(
    [
        "Manual do Compressor CX-200\nInstale o equipamento em área ventilada.",
        "Garantia\nO prazo de garantia é de 24 meses a partir da data de instalação.",
    ]
)
WARRANTY_QUESTION = "Qual é o prazo de garantia do compressor?"


@dataclass
class Reply:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""
    done: dict[str, Any] | None = None
    error: str | None = None


async def _ask(client: AsyncClient, conversation_id: str, question: str) -> Reply:
    response = await client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages", json={"question": question}
    )
    reply = Reply(response.status_code, dict(response.headers))
    if response.status_code != 200:
        return reply
    for block in response.text.strip().split("\n\n"):
        event_line, data_line = block.split("\n")
        event, data = (
            event_line.removeprefix("event: "),
            json.loads(data_line.removeprefix("data: ")),
        )
        if event == "sources":
            reply.sources = data
        elif event == "token":
            reply.text += data["text"]
        elif event == "done":
            reply.done = data
        elif event == "error":
            reply.error = data["detail"]
    return reply


async def _conversation(client: AsyncClient) -> str:
    response = await client.post("/api/v1/chat/conversations")
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _manual_in_new_collection(
    admin: Account, worker: Worker, name: str = "Engenharia"
) -> tuple[str, str]:
    collection = (await admin.client.post("/api/v1/collections", json={"name": name})).json()
    document = (
        await admin.client.post(
            "/api/v1/documents",
            data={"collection_id": collection["id"]},
            files={"file": ("manual-cx200.pdf", MANUAL, "application/pdf")},
        )
    ).json()
    await worker.run_until_empty()
    return str(collection["id"]), str(document["id"])


class _ScriptedAnswerer:
    """Provedor de respostas controlado pelo teste, que registra o que recebeu."""

    model = "roteiro"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[AnswerPrompt] = []

    async def stream(self, prompt: AnswerPrompt) -> AsyncIterator[str]:
        self.prompts.append(prompt)
        yield self.reply

    async def aclose(self) -> None:
        return None


async def test_answer_cites_the_page_where_the_fact_is(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    _, document_id = await _manual_in_new_collection(admin, worker)

    reply = await _ask(admin.client, await _conversation(admin.client), WARRANTY_QUESTION)

    assert reply.status == 200
    # Sem "no-transform", o proxy do Next comprime e acumula a resposta inteira.
    assert reply.headers["content-type"].startswith("text/event-stream")
    assert "no-transform" in reply.headers["cache-control"]
    assert reply.sources[0]["document_id"] == document_id
    assert reply.sources[0]["page"] == 2
    assert reply.done is not None
    assert reply.done["answered"] is True
    assert "24 meses" in reply.done["content"]
    citation = reply.done["citations"][0]
    assert (citation["marker"], citation["page"], citation["document_id"]) == (1, 2, document_id)
    assert "24 meses" in citation["quote"]


async def test_question_without_relevant_sources_skips_the_model(
    app: FastAPI, make_client: ClientFactory, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await signup(make_client)
    await _manual_in_new_collection(admin, worker)
    spy = _ScriptedAnswerer("não deveria ser chamado [S1]")
    monkeypatch.setattr(app.state, "answerer", spy)

    reply = await _ask(
        admin.client, await _conversation(admin.client), "Qual é a política de férias?"
    )

    assert reply.sources == []
    assert reply.done is not None
    assert reply.done["answered"] is False
    assert reply.done["content"] == NOT_FOUND_ANSWER
    assert spy.prompts == []


async def test_answers_citing_sources_that_do_not_exist_are_not_shown(
    app: FastAPI, make_client: ClientFactory, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await signup(make_client)
    await _manual_in_new_collection(admin, worker)
    monkeypatch.setattr(app.state, "answerer", _ScriptedAnswerer("A garantia é de 99 meses [S7]."))

    reply = await _ask(admin.client, await _conversation(admin.client), WARRANTY_QUESTION)

    assert reply.done is not None
    assert reply.done["answered"] is False
    assert reply.done["content"] == NOT_FOUND_ANSWER
    assert reply.done["citations"] == []


async def test_model_only_sees_documents_the_user_can_read(
    app: FastAPI, make_client: ClientFactory, worker: Worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await signup(make_client)
    collection_id, _ = await _manual_in_new_collection(admin, worker)
    member = await add_user(admin, make_client, "MEMBER")
    spy = _ScriptedAnswerer("Garantia de 24 meses [S1].")
    monkeypatch.setattr(app.state, "answerer", spy)
    conversation = await _conversation(member.client)

    without_access = await _ask(member.client, conversation, WARRANTY_QUESTION)
    await admin.client.post(
        f"/api/v1/collections/{collection_id}/members", json={"user_id": member.user_id}
    )
    with_access = await _ask(member.client, conversation, WARRANTY_QUESTION)

    assert without_access.done is not None and without_access.done["answered"] is False
    assert with_access.done is not None and with_access.done["answered"] is True
    assert len(spy.prompts) == 1


async def test_other_organizations_documents_are_never_retrieved(
    make_client: ClientFactory, worker: Worker
) -> None:
    org_a = await signup(make_client, "Organização A")
    await _manual_in_new_collection(org_a, worker)
    org_b = await signup(make_client, "Organização B")

    reply = await _ask(org_b.client, await _conversation(org_b.client), WARRANTY_QUESTION)
    search = await org_b.client.get("/api/v1/search", params={"q": "garantia compressor"})

    assert reply.sources == []
    assert search.json()["items"] == []


async def test_deleted_documents_are_no_longer_retrieved(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    _, document_id = await _manual_in_new_collection(admin, worker)
    conversation = await _conversation(admin.client)
    before = await _ask(admin.client, conversation, WARRANTY_QUESTION)

    await admin.client.delete(f"/api/v1/documents/{document_id}")
    after = await _ask(admin.client, conversation, WARRANTY_QUESTION)
    history = (await admin.client.get(f"/api/v1/chat/conversations/{conversation}")).json()

    assert before.done is not None and before.done["answered"] is True
    assert after.sources == []
    old_citation = history["messages"][1]["citations"][0]
    assert old_citation["available"] is False
    assert old_citation["quote"] is None


async def test_conversations_are_private_and_keep_their_history(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    await _manual_in_new_collection(admin, worker)
    colleague = await add_user(admin, make_client, "ADMIN")
    conversation = await _conversation(admin.client)
    await _ask(admin.client, conversation, WARRANTY_QUESTION)

    history = await admin.client.get(f"/api/v1/chat/conversations/{conversation}")
    listed = await admin.client.get("/api/v1/chat/conversations")
    by_colleague = await colleague.client.get(f"/api/v1/chat/conversations/{conversation}")
    colleague_asks = await _ask(colleague.client, conversation, "Outra pergunta?")

    messages = history.json()["messages"]
    assert [message["role"] for message in messages] == ["USER", "ASSISTANT"]
    assert messages[1]["citations"][0]["page"] == 2
    assert listed.json()[0]["title"] == WARRANTY_QUESTION
    assert by_colleague.status_code == 404
    assert colleague_asks.status == 404


async def test_questions_are_rate_limited_per_user(
    make_client: ClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "chat_questions_per_hour", 1)
    admin = await signup(make_client)
    conversation = await _conversation(admin.client)

    first = await _ask(admin.client, conversation, "Primeira pergunta?")
    second = await _ask(admin.client, conversation, "Segunda pergunta?")

    assert first.status == 200
    assert second.status == 429


async def test_search_returns_permitted_passages_with_their_page(
    make_client: ClientFactory, worker: Worker
) -> None:
    admin = await signup(make_client)
    _, document_id = await _manual_in_new_collection(admin, worker)

    response = await admin.client.get("/api/v1/search", params={"q": "prazo de garantia"})

    top = response.json()["items"][0]
    assert (top["document_id"], top["page"]) == (document_id, 2)
    assert "24 meses" in top["snippet"]

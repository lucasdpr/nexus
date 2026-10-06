from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.config import get_settings
from app.modules.auth.dependencies import Client, CurrentUserDep, DbSession, SettingsDep
from app.modules.chat import repository, service
from app.modules.chat.schemas import AskRequest, ConversationDetail, ConversationOut
from app.modules.chat.service import ChatContext

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


def get_chat_context(request: Request) -> ChatContext:
    state = request.app.state
    return ChatContext(state.sessionmaker, state.embedder, state.answerer, get_settings())


ChatContextDep = Annotated[ChatContext, Depends(get_chat_context)]


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(db: DbSession, current: CurrentUserDep) -> ConversationOut:
    return await service.create_conversation(db, current)


@router.get("/conversations")
async def list_conversations(
    db: DbSession, current: CurrentUserDep, limit: Annotated[int, Query(ge=1, le=100)] = 30
) -> list[ConversationOut]:
    conversations = await repository.list_owned(db, current, limit)
    return [ConversationOut.model_validate(c, from_attributes=True) for c in conversations]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID, db: DbSession, current: CurrentUserDep
) -> ConversationDetail:
    return await service.get_detail(db, current, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID, db: DbSession, current: CurrentUserDep
) -> None:
    await service.delete_conversation(db, current, conversation_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def ask(
    conversation_id: UUID,
    body: AskRequest,
    db: DbSession,
    current: CurrentUserDep,
    client: Client,
    settings: SettingsDep,
    chat: ChatContextDep,
) -> StreamingResponse:
    await service.reserve_question(db, current, conversation_id, body.question, settings, client)
    return StreamingResponse(
        service.stream_answer(chat, current, conversation_id, body.question),
        media_type="text/event-stream",
        # Sem buffer em proxies: os eventos chegam ao navegador conforme são gerados.
        # "no-transform" impede a compressão (o proxy do Next acumularia a resposta inteira).
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )

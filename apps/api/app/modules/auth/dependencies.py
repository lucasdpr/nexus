from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.db import set_tenant
from app.core.errors import AuthenticationError, ForbiddenError
from app.modules.auth import service
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.users.models import Role

SESSION_COOKIE = "nexus_session"


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_client_info(request: Request) -> ClientInfo:
    return ClientInfo(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


Client = Annotated[ClientInfo, Depends(get_client_info)]


async def get_current_user(request: Request, db: DbSession) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    current = await service.resolve_session(db, token) if token else None
    if current is None:
        raise AuthenticationError("Sessão inválida ou expirada. Entre novamente.")
    # A partir daqui, toda consulta desta requisição fica restrita à organização do usuário.
    await set_tenant(db, current.org_id, current.user_id)
    return current


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Autorização no backend: a interface esconder um botão não basta."""

    async def dependency(current: CurrentUserDep) -> CurrentUser:
        if current.role not in roles:
            raise ForbiddenError("Você não tem permissão para esta ação.")
        return current

    return dependency

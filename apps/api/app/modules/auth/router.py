from fastapi import APIRouter, Response, status

from app.core.config import Settings
from app.modules.auth import service
from app.modules.auth.dependencies import (
    SESSION_COOKIE,
    Client,
    CurrentUserDep,
    DbSession,
    SettingsDep,
)
from app.modules.auth.schemas import LoginRequest, MeResponse, SignupRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    body: SignupRequest, response: Response, db: DbSession, client: Client, settings: SettingsDep
) -> MeResponse:
    token, current = await service.signup(db, body, client, settings)
    _set_session_cookie(response, token, settings)
    return await service.get_me(db, current)


@router.post("/login")
async def login(
    body: LoginRequest, response: Response, db: DbSession, client: Client, settings: SettingsDep
) -> MeResponse:
    token, current = await service.login(db, body.email, body.password, client, settings)
    _set_session_cookie(response, token, settings)
    return await service.get_me(db, current)


@router.post("/demo")
async def demo_login(
    response: Response, db: DbSession, client: Client, settings: SettingsDep
) -> MeResponse:
    token, current = await service.demo_login(db, client, settings)
    _set_session_cookie(response, token, settings)
    return await service.get_me(db, current)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, db: DbSession, current: CurrentUserDep, client: Client
) -> None:
    await service.logout(db, current, client)
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
async def me(db: DbSession, current: CurrentUserDep) -> MeResponse:
    return await service.get_me(db, current)

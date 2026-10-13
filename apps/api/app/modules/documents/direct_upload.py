"""Envio direto do navegador para a API, para arquivos que não cabem no corpo de requisição
das hospedagens de front-end (a Vercel recusa corpos acima de ~4,5 MB).

Fluxo: o navegador pede um token curto pela rota normal (com o cookie de sessão) e depois envia
o arquivo direto à API, com o token no formulário. O token é assinado (HMAC), vale poucos
minutos, é preso a quem o pediu, e a sessão de origem é conferida de novo no envio, então
sair do sistema invalida os tokens em aberto.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import set_tenant
from app.modules.auth.identity import CurrentUser
from app.modules.auth.models import UserSession
from app.modules.users.models import Role, User, UserStatus

TOKEN_TTL_SECONDS = 300


def _secret(settings: Settings) -> bytes:
    # Chave derivada do que só o servidor sabe; não exige configuração nova.
    material = settings.database_url.get_secret_value().encode()
    return hashlib.sha256(b"nexus-direct-upload:" + material).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(settings: Settings, current: CurrentUser, *, now: float | None = None) -> str:
    payload = {
        "u": str(current.user_id),
        "o": str(current.org_id),
        "r": current.role.value,
        "s": str(current.session_id),
        "x": int((now if now is not None else time.time()) + TOKEN_TTL_SECONDS),
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = hmac.new(_secret(settings), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64(signature)}"


def read_token(settings: Settings, token: str, *, now: float | None = None) -> CurrentUser | None:
    """O usuário do token, ou None se a assinatura, o prazo ou o conteúdo não valem."""
    try:
        body, signature = token.split(".")
        expected = hmac.new(_secret(settings), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        payload = json.loads(_unb64(body))
        if payload["x"] < (now if now is not None else time.time()):
            return None
        return CurrentUser(
            UUID(payload["u"]), UUID(payload["o"]), Role(payload["r"]), UUID(payload["s"])
        )
    except ValueError, KeyError, TypeError:
        return None


async def refresh_authorization(db: AsyncSession, current: CurrentUser) -> CurrentUser | None:
    """O mesmo usuário com o papel de agora, se a sessão do token segue ativa e ele está habilitado.

    O papel do token pode estar desatualizado (quem foi rebaixado depois de pedi-lo), por isso
    o que vale é o do banco.
    """
    await set_tenant(db, current.org_id, current.user_id)
    session = await db.scalar(
        select(UserSession.id).where(
            UserSession.org_id == current.org_id,
            UserSession.id == current.session_id,
            UserSession.user_id == current.user_id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > datetime.now(UTC),
        )
    )
    if session is None:
        return None
    user = (
        await db.execute(
            select(User.status, User.role).where(
                User.org_id == current.org_id, User.id == current.user_id
            )
        )
    ).one_or_none()
    if user is None or user.status != UserStatus.ACTIVE:
        return None
    return CurrentUser(current.user_id, current.org_id, Role(user.role), current.session_id)

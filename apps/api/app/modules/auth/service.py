import asyncio
import re
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid7

from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.db import set_tenant
from app.core.errors import AuthenticationError, ConflictError, NotFoundError, RateLimitedError
from app.core.security import hash_password, hash_token, new_session_token, verify_password
from app.modules.audit import service as audit
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.auth.models import LoginAttempt, UserSession
from app.modules.auth.schemas import MeResponse, OrganizationOut, SignupRequest
from app.modules.organizations.models import Organization
from app.modules.users.models import Role, User, UserStatus
from app.modules.users.schemas import UserOut
from app.modules.users.service import EMAIL_TAKEN

INVALID_CREDENTIALS = "E-mail ou senha incorretos."

_FIND_USER = text("select user_id, org_id, password_hash, status from auth_find_user(:email)")
_RESOLVE_SESSION = text(
    "select session_id, user_id, org_id, role from auth_resolve_session(:token_hash)"
)
_DEMO_VISITOR = text("select user_id, org_id from auth_demo_visitor(:email)")


def _slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:60] or "org"
    # Sufixo aleatório: a unicidade é global, mas o RLS impede consultar slugs de outros tenants.
    return f"{base}-{secrets.token_hex(3)}"


def _now() -> datetime:
    return datetime.now(UTC)


def _open_session(
    db: AsyncSession, org_id: UUID, user_id: UUID, client: ClientInfo, settings: Settings
) -> tuple[str, UserSession]:
    token = new_session_token()
    session = UserSession(
        org_id=org_id,
        user_id=user_id,
        token_hash=hash_token(token),
        expires_at=_now() + timedelta(hours=settings.session_ttl_hours),
        ip=client.ip,
        user_agent=client.user_agent[:500] if client.user_agent else None,
    )
    db.add(session)
    return token, session


async def signup(
    db: AsyncSession, data: SignupRequest, client: ClientInfo, settings: Settings
) -> tuple[str, CurrentUser]:
    org_id, user_id = uuid7(), uuid7()
    await set_tenant(db, org_id, user_id)

    password_hash = await asyncio.to_thread(hash_password, data.password)
    db.add(
        Organization(id=org_id, name=data.organization_name, slug=_slugify(data.organization_name))
    )
    db.add(
        User(
            id=user_id,
            org_id=org_id,
            name=data.name,
            email=data.email,
            password_hash=password_hash,
            role=Role.ADMIN,
            last_login_at=_now(),
        )
    )
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(EMAIL_TAKEN) from exc

    token, session = _open_session(db, org_id, user_id, client, settings)
    audit.record(db, org_id=org_id, actor_id=user_id, action="auth.signup", ip=client.ip)
    await db.commit()
    return token, CurrentUser(user_id, org_id, Role.ADMIN, session.id)


async def _ensure_not_throttled(
    db: AsyncSession, email: str, ip: str | None, settings: Settings
) -> None:
    since = _now() - timedelta(minutes=settings.login_window_minutes)
    failures = select(func.count()).where(
        LoginAttempt.success.is_(False), LoginAttempt.created_at >= since
    )
    by_email = await db.scalar(failures.where(LoginAttempt.email == email)) or 0
    by_ip = await db.scalar(failures.where(LoginAttempt.ip == ip)) if ip else 0
    if (
        by_email >= settings.login_max_failures_per_email
        or (by_ip or 0) >= settings.login_max_failures_per_ip
    ):
        raise RateLimitedError("Muitas tentativas de login. Aguarde alguns minutos.")


async def login(
    db: AsyncSession, email: str, password: str, client: ClientInfo, settings: Settings
) -> tuple[str, CurrentUser]:
    await _ensure_not_throttled(db, email, client.ip, settings)

    account = (await db.execute(_FIND_USER, {"email": email})).one_or_none()
    password_ok = await asyncio.to_thread(
        verify_password, account.password_hash if account else None, password
    )
    success = password_ok and account is not None and account.status == UserStatus.ACTIVE
    db.add(LoginAttempt(email=email, ip=client.ip, success=success))

    if account is None or not success:
        if account is not None:
            await set_tenant(db, account.org_id)
            audit.record(
                db,
                org_id=account.org_id,
                actor_id=account.user_id,
                action="auth.login_failed",
                ip=client.ip,
            )
        await db.commit()
        raise AuthenticationError(INVALID_CREDENTIALS)

    await set_tenant(db, account.org_id, account.user_id)
    user = await db.get_one(User, account.user_id)
    user.last_login_at = _now()
    token, session = _open_session(db, user.org_id, user.id, client, settings)
    audit.record(db, org_id=user.org_id, actor_id=user.id, action="auth.login", ip=client.ip)
    await db.commit()
    return token, CurrentUser(user.id, user.org_id, user.role, session.id)


async def demo_login(
    db: AsyncSession, client: ClientInfo, settings: Settings
) -> tuple[str, CurrentUser]:
    visitor = (
        await db.execute(_DEMO_VISITOR, {"email": settings.demo_visitor_email})
    ).one_or_none()
    if not settings.demo_enabled or visitor is None:
        raise NotFoundError("A demonstração não está disponível no momento.")

    await set_tenant(db, visitor.org_id, visitor.user_id)
    token, session = _open_session(db, visitor.org_id, visitor.user_id, client, settings)
    audit.record(
        db, org_id=visitor.org_id, actor_id=visitor.user_id, action="auth.demo_login", ip=client.ip
    )
    await db.commit()
    return token, CurrentUser(visitor.user_id, visitor.org_id, Role.MEMBER, session.id)


async def resolve_session(db: AsyncSession, token: str) -> CurrentUser | None:
    row = (await db.execute(_RESOLVE_SESSION, {"token_hash": hash_token(token)})).one_or_none()
    if row is None:
        return None
    return CurrentUser(row.user_id, row.org_id, Role(row.role), row.session_id)


async def logout(db: AsyncSession, current: CurrentUser, client: ClientInfo) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.org_id == current.org_id, UserSession.id == current.session_id)
        .values(revoked_at=_now())
    )
    audit.record(
        db, org_id=current.org_id, actor_id=current.user_id, action="auth.logout", ip=client.ip
    )
    await db.commit()


async def get_me(db: AsyncSession, current: CurrentUser) -> MeResponse:
    row = (
        await db.execute(
            select(User, Organization)
            .join(Organization, Organization.id == User.org_id)
            .where(User.org_id == current.org_id, User.id == current.user_id)
        )
    ).one()
    user, organization = row
    return MeResponse(
        user=UserOut.model_validate(user), organization=OrganizationOut.model_validate(organization)
    )

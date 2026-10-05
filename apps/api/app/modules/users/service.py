import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.auth.models import UserSession
from app.modules.users import repository
from app.modules.users.models import User, UserStatus
from app.modules.users.schemas import UserCreate, UserUpdate

EMAIL_TAKEN = "Já existe uma conta com este e-mail."


async def create_user(
    db: AsyncSession, current: CurrentUser, data: UserCreate, client: ClientInfo
) -> User:
    user = User(
        org_id=current.org_id,
        name=data.name,
        email=data.email,
        password_hash=await asyncio.to_thread(hash_password, data.password),
        role=data.role,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError(EMAIL_TAKEN) from exc

    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="user.created",
        resource_type="user",
        resource_id=user.id,
        ip=client.ip,
        details={"role": user.role.value},
    )
    await db.commit()
    return user


async def update_user(
    db: AsyncSession, current: CurrentUser, user_id: UUID, data: UserUpdate, client: ClientInfo
) -> User:
    user = await repository.get_user(db, current.org_id, user_id)
    if user is None:
        raise NotFoundError("Usuário não encontrado.")

    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    # Só ADMIN chega aqui e ninguém altera o próprio acesso: sempre resta ao menos um ADMIN ativo.
    if user.id == current.user_id and ({"role", "status"} & changes.keys()):
        raise ConflictError("Você não pode alterar o próprio papel ou status.")

    for field, value in changes.items():
        setattr(user, field, value)

    if changes.get("status") == UserStatus.DISABLED:
        await db.execute(
            update(UserSession)
            .where(
                UserSession.org_id == current.org_id,
                UserSession.user_id == user.id,
                UserSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )

    if changes:
        audit.record(
            db,
            org_id=current.org_id,
            actor_id=current.user_id,
            action="user.updated",
            resource_type="user",
            resource_id=user.id,
            ip=client.ip,
            details={key: str(value) for key, value in changes.items()},
        )
    await db.commit()
    return user

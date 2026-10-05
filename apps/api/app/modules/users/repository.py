"""Consultas de usuários. Todas filtram por organização explicitamente, além do RLS."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def list_users(db: AsyncSession, org_id: UUID) -> Sequence[User]:
    result = await db.scalars(select(User).where(User.org_id == org_id).order_by(User.name))
    return result.all()


async def get_user(db: AsyncSession, org_id: UUID, user_id: UUID) -> User | None:
    return await db.scalar(select(User).where(User.org_id == org_id, User.id == user_id))

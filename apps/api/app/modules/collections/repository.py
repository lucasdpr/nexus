"""Consultas de coleções. Todas filtram por organização explicitamente, além do RLS."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.identity import CurrentUser
from app.modules.collections.models import Collection, CollectionMember
from app.modules.users.models import Role, User


def _visible(current: CurrentUser) -> Select[Collection]:
    """ADMIN vê todas as coleções da organização; os demais, só as que integram."""
    query = select(Collection).where(Collection.org_id == current.org_id)
    if current.role != Role.ADMIN:
        query = query.where(
            exists().where(
                CollectionMember.collection_id == Collection.id,
                CollectionMember.user_id == current.user_id,
            )
        )
    return query


async def list_visible(db: AsyncSession, current: CurrentUser) -> Sequence[Collection]:
    return (await db.scalars(_visible(current).order_by(Collection.name))).all()


async def get_visible(
    db: AsyncSession, current: CurrentUser, collection_id: UUID
) -> Collection | None:
    return await db.scalar(_visible(current).where(Collection.id == collection_id))


async def is_member(db: AsyncSession, collection_id: UUID, user_id: UUID) -> bool:
    found = await db.scalar(
        select(
            exists().where(
                CollectionMember.collection_id == collection_id,
                CollectionMember.user_id == user_id,
            )
        )
    )
    return bool(found)


async def list_members(db: AsyncSession, org_id: UUID, collection_id: UUID) -> Sequence[User]:
    query = (
        select(User)
        .join(CollectionMember, CollectionMember.user_id == User.id)
        .where(CollectionMember.org_id == org_id, CollectionMember.collection_id == collection_id)
        .order_by(User.name)
    )
    return (await db.scalars(query)).all()

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.modules.audit import service as audit
from app.modules.auth.identity import ClientInfo, CurrentUser
from app.modules.collections import repository
from app.modules.collections.models import Collection, CollectionMember
from app.modules.collections.schemas import CollectionCreate
from app.modules.users import repository as users
from app.modules.users.models import Role

NOT_FOUND = "Coleção não encontrada."


async def create_collection(
    db: AsyncSession, current: CurrentUser, data: CollectionCreate, client: ClientInfo
) -> Collection:
    collection = Collection(org_id=current.org_id, name=data.name, description=data.description)
    db.add(collection)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Já existe uma coleção com este nome.") from exc

    # Quem cria passa a integrar a coleção e pode gerenciá-la.
    db.add(
        CollectionMember(
            org_id=current.org_id, collection_id=collection.id, user_id=current.user_id
        )
    )
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="collection.created",
        resource_type="collection",
        resource_id=collection.id,
        ip=client.ip,
        details={"name": collection.name},
    )
    await db.commit()
    return collection


async def _managed_collection(
    db: AsyncSession, current: CurrentUser, collection_id: UUID
) -> Collection:
    """Coleção que o usuário pode gerenciar: ADMIN, ou MANAGER que a integra."""
    collection = await repository.get_visible(db, current, collection_id)
    if collection is None:
        raise NotFoundError(NOT_FOUND)
    if current.role == Role.MEMBER:
        raise ForbiddenError("Você não tem permissão para gerenciar esta coleção.")
    return collection


async def add_member(
    db: AsyncSession, current: CurrentUser, collection_id: UUID, user_id: UUID, client: ClientInfo
) -> None:
    collection = await _managed_collection(db, current, collection_id)
    if await users.get_user(db, current.org_id, user_id) is None:
        raise NotFoundError("Usuário não encontrado.")
    if await repository.is_member(db, collection.id, user_id):
        return

    db.add(CollectionMember(org_id=current.org_id, collection_id=collection.id, user_id=user_id))
    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="collection.member_added",
        resource_type="collection",
        resource_id=collection.id,
        ip=client.ip,
        details={"user_id": str(user_id)},
    )
    await db.commit()


async def remove_member(
    db: AsyncSession, current: CurrentUser, collection_id: UUID, user_id: UUID, client: ClientInfo
) -> None:
    collection = await _managed_collection(db, current, collection_id)
    result = await db.execute(
        delete(CollectionMember).where(
            CollectionMember.org_id == current.org_id,
            CollectionMember.collection_id == collection.id,
            CollectionMember.user_id == user_id,
        )
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        return

    audit.record(
        db,
        org_id=current.org_id,
        actor_id=current.user_id,
        action="collection.member_removed",
        resource_type="collection",
        resource_id=collection.id,
        ip=client.ip,
        details={"user_id": str(user_id)},
    )
    await db.commit()

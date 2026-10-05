from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.errors import NotFoundError
from app.modules.auth.dependencies import Client, CurrentUserDep, DbSession, require_roles
from app.modules.auth.identity import CurrentUser
from app.modules.collections import repository, service
from app.modules.collections.schemas import CollectionCreate, CollectionOut, MemberAdd
from app.modules.users.models import Role
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/api/v1/collections", tags=["collections"])

AdminOrManager = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.MANAGER))]


@router.get("")
async def list_collections(db: DbSession, current: CurrentUserDep) -> list[CollectionOut]:
    collections = await repository.list_visible(db, current)
    return [CollectionOut.model_validate(collection) for collection in collections]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate, db: DbSession, current: AdminOrManager, client: Client
) -> CollectionOut:
    collection = await service.create_collection(db, current, body, client)
    return CollectionOut.model_validate(collection)


@router.get("/{collection_id}/members")
async def list_members(
    collection_id: UUID, db: DbSession, current: CurrentUserDep
) -> list[UserOut]:
    if await repository.get_visible(db, current, collection_id) is None:
        raise NotFoundError(service.NOT_FOUND)
    members = await repository.list_members(db, current.org_id, collection_id)
    return [UserOut.model_validate(member) for member in members]


@router.post("/{collection_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(
    collection_id: UUID, body: MemberAdd, db: DbSession, current: CurrentUserDep, client: Client
) -> None:
    await service.add_member(db, current, collection_id, body.user_id, client)


@router.delete("/{collection_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    collection_id: UUID, user_id: UUID, db: DbSession, current: CurrentUserDep, client: Client
) -> None:
    await service.remove_member(db, current, collection_id, user_id, client)

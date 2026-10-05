from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.modules.auth.dependencies import Client, DbSession, require_roles
from app.modules.auth.identity import CurrentUser
from app.modules.users import repository, service
from app.modules.users.models import Role
from app.modules.users.schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/v1/users", tags=["users"])

AdminOrManager = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN, Role.MANAGER))]
Admin = Annotated[CurrentUser, Depends(require_roles(Role.ADMIN))]


@router.get("")
async def list_users(db: DbSession, current: AdminOrManager) -> list[UserOut]:
    users = await repository.list_users(db, current.org_id)
    return [UserOut.model_validate(user) for user in users]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: DbSession, current: Admin, client: Client) -> UserOut:
    return UserOut.model_validate(await service.create_user(db, current, body, client))


@router.patch("/{user_id}")
async def update_user(
    user_id: UUID, body: UserUpdate, db: DbSession, current: Admin, client: Client
) -> UserOut:
    return UserOut.model_validate(await service.update_user(db, current, user_id, body, client))

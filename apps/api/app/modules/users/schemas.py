from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.modules.users.models import Role, UserStatus

PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Password = Annotated[str, Field(min_length=10, max_length=128)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: Role
    status: UserStatus
    avatar_url: str | None
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(BaseModel):
    name: PersonName
    email: EmailStr
    password: Password
    role: Role = Role.MEMBER


class UserUpdate(BaseModel):
    name: PersonName | None = None
    role: Role | None = None
    status: UserStatus | None = None

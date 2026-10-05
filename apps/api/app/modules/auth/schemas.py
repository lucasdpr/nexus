from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.modules.users.schemas import Password, PersonName, UserOut

OrganizationName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)
]


class SignupRequest(BaseModel):
    name: PersonName
    email: EmailStr
    password: Password
    organization_name: OrganizationName


class LoginRequest(BaseModel):
    # Sem validação de formato: no login basta comparar com o que está cadastrado.
    email: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_demo: bool


class MeResponse(BaseModel):
    user: UserOut
    organization: OrganizationOut

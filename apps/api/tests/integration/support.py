from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from httpx2 import AsyncClient

from tests.conftest import ClientFactory

PASSWORD = "senha-segura-123"


def unique_email() -> str:
    return f"{uuid4().hex[:12]}@teste.example.com"


@dataclass
class Account:
    client: AsyncClient
    email: str
    me: dict[str, Any]

    @property
    def user_id(self) -> str:
        return str(self.me["user"]["id"])

    @property
    def org_id(self) -> str:
        return str(self.me["organization"]["id"])


async def signup(make_client: ClientFactory, organization: str = "Organização Teste") -> Account:
    client, email = make_client(), unique_email()
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Ana Admin",
            "email": email,
            "password": PASSWORD,
            "organization_name": organization,
        },
    )
    assert response.status_code == 201, response.text
    return Account(client, email, response.json())


async def add_user(admin: Account, make_client: ClientFactory, role: str) -> Account:
    email = unique_email()
    created = await admin.client.post(
        "/api/v1/users",
        json={"name": f"Pessoa {role.title()}", "email": email, "password": PASSWORD, "role": role},
    )
    assert created.status_code == 201, created.text

    client = make_client()
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return Account(client, email, response.json())

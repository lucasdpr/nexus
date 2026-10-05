"""Isolamento entre organizações, verificado na API e direto no banco (RLS)."""

from uuid import UUID

import pytest
from fastapi import FastAPI
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import set_tenant
from app.modules.users.models import User
from tests.conftest import ClientFactory
from tests.integration.support import add_user, signup

pytestmark = pytest.mark.anyio


async def test_admin_cannot_see_or_change_users_of_another_organization(
    make_client: ClientFactory,
) -> None:
    org_a = await signup(make_client, "Organização A")
    org_b = await signup(make_client, "Organização B")

    listed = await org_b.client.get("/api/v1/users")
    patched = await org_b.client.patch(f"/api/v1/users/{org_a.user_id}", json={"name": "Invasor"})

    assert org_a.email not in {user["email"] for user in listed.json()}
    assert patched.status_code == 404


async def test_collections_are_invisible_to_other_organizations(
    make_client: ClientFactory,
) -> None:
    org_a = await signup(make_client, "Organização A")
    org_b = await signup(make_client, "Organização B")
    created = await org_a.client.post("/api/v1/collections", json={"name": "Jurídico"})
    collection_id = created.json()["id"]

    listed = await org_b.client.get("/api/v1/collections")
    members = await org_b.client.get(f"/api/v1/collections/{collection_id}/members")
    added = await org_b.client.post(
        f"/api/v1/collections/{collection_id}/members", json={"user_id": org_b.user_id}
    )

    assert collection_id not in {collection["id"] for collection in listed.json()}
    assert members.status_code == 404
    assert added.status_code == 404


async def test_row_level_security_filters_queries_without_where_clause(
    app: FastAPI, make_client: ClientFactory
) -> None:
    org_a = await signup(make_client, "Organização A")
    await add_user(org_a, make_client, "MEMBER")
    await signup(make_client, "Organização B")

    async with app.state.sessionmaker() as db:
        await set_tenant(db, UUID(org_a.org_id))
        visible = await db.scalar(select(func.count()).select_from(User))
        other_orgs = await db.scalar(
            select(func.count()).select_from(User).where(User.org_id != UUID(org_a.org_id))
        )

    assert visible == 2
    assert other_orgs == 0


async def test_row_level_security_without_tenant_sees_nothing(
    app: FastAPI, make_client: ClientFactory
) -> None:
    await signup(make_client)

    async with app.state.sessionmaker() as db:
        users = await db.scalar(select(func.count()).select_from(User))

    assert users == 0


async def test_audit_events_cannot_be_altered_by_the_application(
    app: FastAPI, make_client: ClientFactory
) -> None:
    account = await signup(make_client)

    async with app.state.sessionmaker() as db:
        await set_tenant(db, UUID(account.org_id))
        with pytest.raises(DBAPIError, match="permission denied"):
            await db.execute(text("UPDATE audit_events SET action = 'adulterado'"))

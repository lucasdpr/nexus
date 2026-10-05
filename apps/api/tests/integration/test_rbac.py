"""Autorização por papel, sempre verificada no backend."""

import pytest

from tests.conftest import ClientFactory
from tests.integration.support import PASSWORD, add_user, signup, unique_email

pytestmark = pytest.mark.anyio


async def test_member_cannot_manage_users(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    member = await add_user(admin, make_client, "MEMBER")

    listed = await member.client.get("/api/v1/users")
    created = await member.client.post(
        "/api/v1/users",
        json={"name": "Nova Pessoa", "email": unique_email(), "password": PASSWORD},
    )

    assert listed.status_code == 403
    assert created.status_code == 403


async def test_manager_can_list_users_but_not_change_roles(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    manager = await add_user(admin, make_client, "MANAGER")

    listed = await manager.client.get("/api/v1/users")
    promoted = await manager.client.patch(
        f"/api/v1/users/{manager.user_id}", json={"role": "ADMIN"}
    )

    assert listed.status_code == 200
    assert promoted.status_code == 403


async def test_admin_cannot_change_own_role_or_status(make_client: ClientFactory) -> None:
    admin = await signup(make_client)

    demoted = await admin.client.patch(f"/api/v1/users/{admin.user_id}", json={"role": "MEMBER"})
    renamed = await admin.client.patch(f"/api/v1/users/{admin.user_id}", json={"name": "Ana"})

    assert demoted.status_code == 409
    assert renamed.status_code == 200


async def test_members_only_see_collections_they_belong_to(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    manager = await add_user(admin, make_client, "MANAGER")
    member = await add_user(admin, make_client, "MEMBER")

    engineering = await manager.client.post("/api/v1/collections", json={"name": "Engenharia"})
    await admin.client.post("/api/v1/collections", json={"name": "Jurídico"})
    added = await manager.client.post(
        f"/api/v1/collections/{engineering.json()['id']}/members",
        json={"user_id": member.user_id},
    )

    assert engineering.status_code == 201
    assert added.status_code == 204
    member_view = await member.client.get("/api/v1/collections")
    admin_view = await admin.client.get("/api/v1/collections")
    assert [c["name"] for c in member_view.json()] == ["Engenharia"]
    assert {c["name"] for c in admin_view.json()} == {"Engenharia", "Jurídico"}


async def test_member_cannot_create_or_manage_collections(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    member = await add_user(admin, make_client, "MEMBER")
    collection = await admin.client.post("/api/v1/collections", json={"name": "Suprimentos"})
    await admin.client.post(
        f"/api/v1/collections/{collection.json()['id']}/members", json={"user_id": member.user_id}
    )

    created = await member.client.post("/api/v1/collections", json={"name": "Minha"})
    removed = await member.client.delete(
        f"/api/v1/collections/{collection.json()['id']}/members/{member.user_id}"
    )

    assert created.status_code == 403
    assert removed.status_code == 403


async def test_manager_cannot_manage_collection_outside_their_membership(
    make_client: ClientFactory,
) -> None:
    admin = await signup(make_client)
    manager = await add_user(admin, make_client, "MANAGER")
    legal = await admin.client.post("/api/v1/collections", json={"name": "Jurídico"})

    response = await manager.client.post(
        f"/api/v1/collections/{legal.json()['id']}/members", json={"user_id": manager.user_id}
    )

    assert response.status_code == 404


async def test_only_admin_reads_the_audit_log_with_cursor_pagination(
    make_client: ClientFactory,
) -> None:
    admin = await signup(make_client)
    manager = await add_user(admin, make_client, "MANAGER")

    first = await admin.client.get("/api/v1/audit-events", params={"limit": 1})
    second = await admin.client.get(
        "/api/v1/audit-events", params={"limit": 1, "cursor": first.json()["next_cursor"]}
    )
    forbidden = await manager.client.get("/api/v1/audit-events")

    assert first.status_code == 200
    assert first.json()["items"][0]["action"] == "auth.login"
    assert second.json()["items"][0]["id"] != first.json()["items"][0]["id"]
    assert forbidden.status_code == 403

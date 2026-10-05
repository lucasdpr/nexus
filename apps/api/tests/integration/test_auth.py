import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.cli import seed_demo
from app.core.config import get_settings
from app.core.db import create_engine
from app.modules.auth.dependencies import SESSION_COOKIE
from app.modules.auth.service import INVALID_CREDENTIALS
from tests.conftest import ClientFactory
from tests.integration.support import PASSWORD, add_user, signup, unique_email

pytestmark = pytest.mark.anyio


async def test_signup_creates_organization_and_admin_session(make_client: ClientFactory) -> None:
    account = await signup(make_client, organization="Metalúrgica Teste")

    me = await account.client.get("/api/v1/auth/me")

    assert me.status_code == 200
    assert me.json()["user"]["role"] == "ADMIN"
    assert me.json()["organization"]["name"] == "Metalúrgica Teste"
    assert me.json()["organization"]["slug"].startswith("metalurgica-teste-")


async def test_session_cookie_is_http_only_and_same_site(make_client: ClientFactory) -> None:
    response = await make_client().post(
        "/api/v1/auth/signup",
        json={
            "name": "Ana",
            "email": unique_email(),
            "password": PASSWORD,
            "organization_name": "Org",
        },
    )

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


async def test_signup_with_existing_email_conflicts(make_client: ClientFactory) -> None:
    account = await signup(make_client)

    response = await make_client().post(
        "/api/v1/auth/signup",
        json={
            "name": "Outra Pessoa",
            "email": account.email.upper(),
            "password": PASSWORD,
            "organization_name": "Outra Org",
        },
    )

    assert response.status_code == 409


async def test_login_rejects_wrong_password_and_unknown_email_alike(
    make_client: ClientFactory,
) -> None:
    account = await signup(make_client)
    client = make_client()

    wrong_password = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": "senha-errada-000"}
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": unique_email(), "password": PASSWORD}
    )
    correct = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"] == INVALID_CREDENTIALS
    assert correct.status_code == 200
    assert (await client.get("/api/v1/auth/me")).status_code == 200


async def test_login_is_throttled_after_repeated_failures(make_client: ClientFactory) -> None:
    account = await signup(make_client)
    client = make_client()
    limit = get_settings().login_max_failures_per_email

    for _ in range(limit):
        await client.post(
            "/api/v1/auth/login", json={"email": account.email, "password": "senha-errada-000"}
        )
    blocked = await client.post(
        "/api/v1/auth/login", json={"email": account.email, "password": PASSWORD}
    )

    assert blocked.status_code == 429


async def test_failed_attempts_from_another_ip_do_not_lock_the_account(
    make_client: ClientFactory,
) -> None:
    account = await signup(make_client)
    attacker = make_client(ip="203.0.113.7")
    limit = get_settings().login_max_failures_per_email

    for _ in range(limit + 1):
        await attacker.post(
            "/api/v1/auth/login", json={"email": account.email, "password": "senha-errada-000"}
        )
    owner = await make_client(ip="198.51.100.20").post(
        "/api/v1/auth/login", json={"email": account.email, "password": PASSWORD}
    )

    assert owner.status_code == 200


async def test_logout_revokes_the_session_on_the_server(make_client: ClientFactory) -> None:
    account = await signup(make_client)
    token = account.client.cookies[SESSION_COOKIE]

    assert (await account.client.post("/api/v1/auth/logout")).status_code == 204

    reused = make_client()
    reused.cookies.set(SESSION_COOKIE, token)
    assert (await reused.get("/api/v1/auth/me")).status_code == 401


async def test_disabling_a_user_ends_sessions_and_blocks_login(make_client: ClientFactory) -> None:
    admin = await signup(make_client)
    member = await add_user(admin, make_client, "MEMBER")

    disabled = await admin.client.patch(
        f"/api/v1/users/{member.user_id}", json={"status": "DISABLED"}
    )
    login = await make_client().post(
        "/api/v1/auth/login", json={"email": member.email, "password": PASSWORD}
    )

    assert disabled.status_code == 200
    assert (await member.client.get("/api/v1/auth/me")).status_code == 401
    assert login.status_code == 401


async def test_requests_without_session_are_rejected(make_client: ClientFactory) -> None:
    response = await make_client().get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_demo_login_enters_demo_organization_as_member(
    app: FastAPI, database_url: str, make_client: ClientFactory
) -> None:
    engine = create_engine(database_url, pooled=False)
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        await seed_demo(db, get_settings())
    await engine.dispose()

    client = make_client()
    response = await client.post("/api/v1/auth/demo")

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "MEMBER"
    assert response.json()["organization"]["is_demo"] is True
    collections = await client.get("/api/v1/collections")
    assert len(collections.json()) == 4

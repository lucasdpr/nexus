import pytest

from tests.conftest import ClientFactory
from tests.integration.support import PASSWORD, unique_email

pytestmark = pytest.mark.anyio

LOGIN = {"email": "ninguem@teste.example.com", "password": PASSWORD}


async def test_state_changing_requests_from_other_origins_are_rejected(
    make_client: ClientFactory,
) -> None:
    response = await make_client().post(
        "/api/v1/auth/login", json=LOGIN, headers={"Origin": "https://site-malicioso.example"}
    )

    assert response.status_code == 403


async def test_requests_from_the_web_origin_pass_the_guard(make_client: ClientFactory) -> None:
    response = await make_client().post(
        "/api/v1/auth/login",
        json={**LOGIN, "email": unique_email()},
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 401

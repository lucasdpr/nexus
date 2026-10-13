from uuid import uuid4

from pydantic import SecretStr

from app.core.config import Settings
from app.modules.auth.identity import CurrentUser
from app.modules.documents import direct_upload
from app.modules.users.models import Role


def _settings(database_url: str = "postgresql://a:senha-um@h/db") -> Settings:
    return Settings(database_url=SecretStr(database_url))


def _user() -> CurrentUser:
    return CurrentUser(uuid4(), uuid4(), Role.MANAGER, uuid4())


def test_a_fresh_token_returns_the_same_user() -> None:
    settings, user = _settings(), _user()

    assert direct_upload.read_token(settings, direct_upload.issue_token(settings, user)) == user


def test_an_expired_token_is_rejected() -> None:
    settings, user = _settings(), _user()
    token = direct_upload.issue_token(settings, user, now=1_000.0)

    assert direct_upload.read_token(settings, token, now=1_000.0 + 299) == user
    assert direct_upload.read_token(settings, token, now=1_000.0 + 301) is None


def test_a_tampered_token_is_rejected() -> None:
    settings = _settings()
    token = direct_upload.issue_token(settings, _user())
    body, signature = token.split(".")
    other = direct_upload.issue_token(settings, _user()).split(".")[0]

    assert direct_upload.read_token(settings, f"{other}.{signature}") is None
    assert direct_upload.read_token(settings, f"{body}.{signature[:-2]}AA") is None
    assert direct_upload.read_token(settings, "lixo") is None
    assert direct_upload.read_token(settings, "") is None


def test_a_token_from_another_server_secret_is_rejected() -> None:
    user = _user()
    token = direct_upload.issue_token(_settings(), user)

    assert direct_upload.read_token(_settings("postgresql://a:outra@h/db"), token) is None


def test_the_direct_url_comes_from_the_public_url_or_from_render() -> None:
    url = SecretStr("postgresql://a:b@h/db")

    assert Settings(database_url=url).direct_upload_url is None
    assert (
        Settings(database_url=url, render_external_url="https://api.exemplo.com/").direct_upload_url
        == "https://api.exemplo.com/api/v1/documents/direct"
    )
    assert (
        Settings(
            database_url=url, public_api_url="https://x.com", render_external_url="https://y.com"
        ).direct_upload_url
        == "https://x.com/api/v1/documents/direct"
    )

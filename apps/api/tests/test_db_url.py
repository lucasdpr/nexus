from app.core.db import to_async_url


def test_neon_url_is_converted_to_asyncpg_with_ssl() -> None:
    url, connect_args = to_async_url(
        "postgresql://user:pass@ep-x.neon.tech/nexus?sslmode=require&channel_binding=require"
    )

    assert url.drivername == "postgresql+asyncpg"
    assert dict(url.query) == {}
    assert connect_args == {"ssl": "require"}


def test_local_url_without_ssl_has_no_connect_args() -> None:
    url, connect_args = to_async_url("postgresql://nexus:nexus@localhost:5432/nexus")

    assert url.drivername == "postgresql+asyncpg"
    assert url.database == "nexus"
    assert connect_args == {}

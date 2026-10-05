from app.modules.auth.service import _ip_bucket


def test_ipv4_is_kept_as_is() -> None:
    assert _ip_bucket("203.0.113.7") == "203.0.113.7"


def test_ipv6_addresses_in_the_same_64_share_a_bucket() -> None:
    first = _ip_bucket("2001:db8:abcd:12::1")
    second = _ip_bucket("2001:db8:abcd:12:ffff::42")

    assert first == second == "2001:db8:abcd:12::/64"


def test_missing_or_unparseable_ip() -> None:
    assert _ip_bucket(None) is None
    assert _ip_bucket("testclient") == "testclient"

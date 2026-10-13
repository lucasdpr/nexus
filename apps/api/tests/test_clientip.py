from starlette.requests import Request

from app.core.clientip import client_ip


def _request(forwarded: str | None, peer: str = "10.0.0.9") -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    return Request({"type": "http", "headers": headers, "client": (peer, 5000)})


def test_without_trusted_proxies_the_connection_address_is_used() -> None:
    assert client_ip(_request("203.0.113.7"), 0) == "10.0.0.9"


def test_the_address_is_counted_from_the_right_by_the_number_of_trusted_proxies() -> None:
    # cliente -> Vercel -> Render: o Render acrescenta o IP da Vercel ao fim.
    assert client_ip(_request("203.0.113.7, 76.76.21.21"), 2) == "203.0.113.7"
    # Um valor forjado pelo cliente fica à esquerda do que os proxies acrescentaram.
    assert client_ip(_request("1.2.3.4, 203.0.113.7, 76.76.21.21"), 2) == "203.0.113.7"
    assert client_ip(_request("203.0.113.7"), 1) == "203.0.113.7"


def test_a_short_or_missing_or_malformed_header_falls_back_to_the_connection() -> None:
    assert client_ip(_request(None), 2) == "10.0.0.9"
    assert client_ip(_request("203.0.113.7"), 2) == "10.0.0.9"
    assert client_ip(_request("nao-e-ip, 76.76.21.21"), 2) == "10.0.0.9"
    assert client_ip(_request(""), 1) == "10.0.0.9"


def test_ipv6_clients_are_normalized() -> None:
    assert client_ip(_request("2001:DB8::1, 76.76.21.21"), 2) == "2001:db8::1"


def test_the_chain_measured_in_production_resolves_to_the_real_client() -> None:
    # Medido no ambiente real: cliente, saída da Vercel, borda da Cloudflare e balanceador.
    chain = "177.71.70.206,18.230.57.233, 104.23.213.149, 10.28.185.167"

    assert client_ip(_request(chain, peer="10.28.185.167"), 4) == "177.71.70.206"

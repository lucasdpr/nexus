"""IP real do cliente atrás de proxies (Vercel, Render).

Sem isto, atrás de um proxy todos os usuários chegam com o IP dele, e os limites por IP
(tentativas de login, cadastros) passam a valer para todo mundo junto.
"""

import ipaddress

from fastapi import Request


def client_ip(request: Request, trusted_hops: int) -> str | None:
    """IP do cliente, contando `trusted_hops` proxies confiáveis a partir da direita.

    Cada proxy confiável acrescenta ao fim de `X-Forwarded-For` o endereço de quem falou com
    ele; quem está à esquerda disso pode ter sido escrito pelo próprio cliente e não vale.
    Com `trusted_hops=0` (ou cabeçalho ausente ou malformado) vale o endereço da conexão.
    """
    peer = request.client.host if request.client else None
    if trusted_hops <= 0:
        return peer
    parts = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",")]
    parts = [part for part in parts if part]
    if len(parts) < trusted_hops:
        return peer
    candidate = parts[-trusted_hops]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return peer

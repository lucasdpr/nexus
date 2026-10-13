"""Cliente mínimo da API para os scripts de demonstração e de avaliação.

Configuração por variáveis de ambiente (nada de senha em arquivo versionado):
NEXUS_URL (padrão http://localhost:3000), NEXUS_EMAIL e NEXUS_PASSWORD.
"""

import os
import sys

import httpx2


def connect() -> httpx2.Client:
    base = os.environ.get("NEXUS_URL", "http://localhost:3000").rstrip("/")
    email = os.environ.get("NEXUS_EMAIL", "admin@novaforja.example.com")
    password = os.environ.get("NEXUS_PASSWORD")
    if not password:
        sys.exit("Defina NEXUS_PASSWORD (senha do usuário usado nos testes).")
    client = httpx2.Client(base_url=base, headers={"Origin": base}, timeout=180)
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        sys.exit(f"Login recusado ({response.status_code}).")
    return client

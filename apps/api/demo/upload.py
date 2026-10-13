"""Envia os documentos de demonstração pela API e espera o processamento:
`python -m demo.upload` (a partir de apps/api, com NEXUS_URL e NEXUS_PASSWORD definidos).
"""

import sys
import time

from demo.build import OUTPUT
from demo.client import connect
from demo.content import DOCUMENTS

MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def main() -> None:
    client = connect()
    collections = {c["name"]: c["id"] for c in client.get("/api/v1/collections").json()}
    pending: dict[str, str] = {}
    for document in DOCUMENTS:
        path = OUTPUT / document.filename
        if not path.exists():
            sys.exit("Arquivos ausentes: rode `python -m demo.build` antes.")
        collection_id = collections[document.collection]
        files = {"file": (document.filename, path.read_bytes(), MIME[path.suffix])}
        response = client.post(
            "/api/v1/documents",
            data={"collection_id": collection_id, "title": document.title},
            files=files,
        )
        if response.status_code == 409:
            print(f"já existe: {document.title}")
        elif response.status_code == 201:
            pending[response.json()["id"]] = document.title
            print(f"enviado: {document.title}")
        else:
            sys.exit(f"Falha ao enviar {document.title}: {response.status_code} {response.text}")

    for _ in range(90):
        for document_id, title in list(pending.items()):
            status = client.get(f"/api/v1/documents/{document_id}").json()["status"]
            if status == "READY":
                del pending[document_id]
                print(f"pronto: {title}")
            elif status == "FAILED":
                sys.exit(f"O processamento falhou: {title}")
        if not pending:
            return
        time.sleep(2)
    sys.exit(f"Tempo esgotado esperando: {', '.join(pending.values())}")


if __name__ == "__main__":
    main()

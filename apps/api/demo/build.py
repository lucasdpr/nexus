"""Gera os arquivos de demonstração em demo/files: `python -m demo.build` (a partir de apps/api)."""

from pathlib import Path

from demo.content import DOCUMENTS
from tests.files import make_docx, make_pdf

OUTPUT = Path(__file__).parent / "files"


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    for document in DOCUMENTS:
        if document.filename.endswith(".pdf"):
            data = make_pdf(list(document.pages))
        else:
            paragraphs = [line for page in document.pages for line in page.split("\n") if line]
            data = make_docx(paragraphs)
        (OUTPUT / document.filename).write_bytes(data)
        print(f"{document.filename}: {len(data)} bytes")


if __name__ == "__main__":
    main()

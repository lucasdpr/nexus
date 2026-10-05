import io
import zipfile

import pytest

from app.core.errors import UnsupportedMediaTypeError
from app.ingestion import detection
from app.ingestion.detection import detect_kind
from app.modules.documents.models import DocumentKind
from tests.files import make_docx, make_pdf


def _zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def test_detects_by_content_regardless_of_the_name() -> None:
    assert detect_kind("relatorio.bin", make_pdf(["Texto"])) == DocumentKind.PDF
    assert detect_kind("contrato", make_docx(["Cláusula 1"])) == DocumentKind.DOCX


def test_text_files_need_a_text_extension_and_utf8() -> None:
    assert detect_kind("notas.md", "# Título".encode()) == DocumentKind.MD
    assert detect_kind("notas.txt", b"texto") == DocumentKind.TXT
    with pytest.raises(UnsupportedMediaTypeError, match="UTF-8"):
        detect_kind("notas.txt", "acentuação".encode("latin-1"))


@pytest.mark.parametrize(
    ("filename", "data"),
    [
        ("programa.pdf", b"MZ\x90\x00 executavel disfarcado"),
        ("planilha.docx", _zip({"xl/workbook.xml": b"<workbook/>"})),
        ("binario.txt", b"texto\x00com nulos"),
        ("vazio.pdf", b""),
    ],
)
def test_rejects_unsupported_or_disguised_files(filename: str, data: bytes) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        detect_kind(filename, data)


def test_rejects_docx_that_expands_too_much(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detection, "MAX_DOCX_UNCOMPRESSED_BYTES", 10_000)
    bomb = _zip({"[Content_Types].xml": b"<x/>", "word/document.xml": b"0" * 50_000})

    with pytest.raises(UnsupportedMediaTypeError, match="descompactado"):
        detect_kind("bomba.docx", bomb)

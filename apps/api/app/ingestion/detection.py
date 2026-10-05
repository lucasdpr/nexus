"""Identifica o tipo do arquivo pelo conteúdo, não pela extensão nem pelo Content-Type."""

import io
import zipfile
from pathlib import PurePath

from app.core.errors import UnsupportedMediaTypeError
from app.modules.documents.models import DocumentKind

MIME_TYPES = {
    DocumentKind.PDF: "application/pdf",
    DocumentKind.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    DocumentKind.TXT: "text/plain; charset=utf-8",
    DocumentKind.MD: "text/markdown; charset=utf-8",
}

TEXT_EXTENSIONS = {".txt": DocumentKind.TXT, ".md": DocumentKind.MD, ".markdown": DocumentKind.MD}

# Limites contra "zip bombs": DOCX é um ZIP e pode crescer muito ao ser descompactado.
MAX_DOCX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000

UNSUPPORTED = "Formato não suportado. Envie PDF, DOCX, TXT ou MD."


def detect_kind(filename: str, data: bytes) -> DocumentKind:
    if not data:
        raise UnsupportedMediaTypeError("O arquivo está vazio.")
    if data.startswith(b"%PDF-"):
        return DocumentKind.PDF
    if data.startswith(b"PK\x03\x04"):
        _check_docx(data)
        return DocumentKind.DOCX

    kind = TEXT_EXTENSIONS.get(PurePath(filename).suffix.lower())
    if kind is None:
        raise UnsupportedMediaTypeError(UNSUPPORTED)
    _check_text(data)
    return kind


def _check_docx(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
    except zipfile.BadZipFile as exc:
        raise UnsupportedMediaTypeError("O arquivo DOCX está corrompido.") from exc

    names = {entry.filename for entry in entries}
    if not {"[Content_Types].xml", "word/document.xml"} <= names:
        raise UnsupportedMediaTypeError(UNSUPPORTED)
    uncompressed = sum(entry.file_size for entry in entries)
    if len(entries) > MAX_DOCX_ENTRIES or uncompressed > MAX_DOCX_UNCOMPRESSED_BYTES:
        raise UnsupportedMediaTypeError("O documento DOCX é grande demais depois de descompactado.")


def _check_text(data: bytes) -> None:
    if b"\x00" in data:
        raise UnsupportedMediaTypeError("O arquivo de texto contém dados binários.")
    try:
        data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsupportedMediaTypeError("Arquivos de texto precisam estar em UTF-8.") from exc

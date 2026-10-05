import io
from dataclasses import dataclass

import docx
import pypdfium2 as pdfium
from docx.table import Table

from app.ingestion.errors import PipelineError
from app.ingestion.normalization import normalize_text
from app.modules.documents.models import DocumentKind


@dataclass(frozen=True, slots=True)
class PageText:
    # Número da página (1, 2, ...) quando o formato tem páginas; None para DOCX e texto.
    page: int | None
    text: str


@dataclass(frozen=True, slots=True)
class Extraction:
    pages: list[PageText]
    # Total de páginas do arquivo, incluindo as sem texto; None quando o formato não tem páginas.
    page_count: int | None


NO_TEXT = {
    DocumentKind.PDF: (
        "Nenhum texto encontrado. O PDF parece ser digitalizado (imagem), e o reconhecimento "
        "de texto (OCR) ainda não é suportado."
    ),
    DocumentKind.DOCX: "O documento DOCX não tem texto.",
    DocumentKind.TXT: "O arquivo está vazio.",
    DocumentKind.MD: "O arquivo está vazio.",
}


def extract_text(kind: DocumentKind, data: bytes, max_pdf_pages: int) -> Extraction:
    match kind:
        case DocumentKind.PDF:
            raw_pages = _extract_pdf(data, max_pdf_pages)
        case DocumentKind.DOCX:
            raw_pages = [PageText(None, _extract_docx(data))]
        case DocumentKind.TXT | DocumentKind.MD:
            raw_pages = [PageText(None, data.decode("utf-8-sig"))]

    pages = [PageText(page.page, normalize_text(page.text)) for page in raw_pages]
    pages = [page for page in pages if page.text]
    if not pages:
        raise PipelineError(NO_TEXT[kind])
    page_count = len(raw_pages) if kind == DocumentKind.PDF else None
    return Extraction(pages, page_count)


def _extract_pdf(data: bytes, max_pages: int) -> list[PageText]:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        if "password" in str(exc).lower():
            raise PipelineError("O PDF é protegido por senha.") from exc
        raise PipelineError("Não foi possível abrir o PDF; o arquivo parece corrompido.") from exc

    try:
        if len(pdf) > max_pages:
            raise PipelineError(f"O PDF tem {len(pdf)} páginas; o limite é {max_pages}.")
        pages = []
        for index in range(len(pdf)):
            page = pdf[index]
            textpage = page.get_textpage()
            pages.append(PageText(index + 1, textpage.get_text_range()))
            textpage.close()
            page.close()
        return pages
    finally:
        pdf.close()


def _extract_docx(data: bytes) -> str:
    document = docx.Document(io.BytesIO(data))
    parts: list[str] = []
    # Parágrafos e tabelas na ordem em que aparecem no documento.
    for block in document.iter_inner_content():
        # Cada linha de tabela vira um parágrafo, para não se fundir com a seguinte.
        lines = (
            [" | ".join(cell.text for cell in row.cells) for row in block.rows]
            if isinstance(block, Table)
            else [block.text]
        )
        for line in lines:
            parts += [line, ""]
    return "\n".join(parts)

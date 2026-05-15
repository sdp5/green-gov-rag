# parsers/__init__.py

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from green_gov_rag.types import ParserType

from .html_parser import parse_html, parse_html_structured
from .pdf_parser import parse_pdf

if TYPE_CHECKING:
    from .layout_parser import HierarchicalPDFParser

SUPPORTED_PARSERS = {
    ParserType.PDF.value: parse_pdf,
    ParserType.HTML.value: parse_html,
    ParserType.HTM.value: parse_html,
}


def get_parser(file_path: str):
    """Dispatcher function to get the right parser function
    based on file extension.

    Args:
    ----
        file_path (str): Path to the file.

    Returns:
    -------
        function: A parser function that accepts `file_path`
                  and returns extracted text.

    """
    ext = Path(file_path).suffix.lower()
    parser = SUPPORTED_PARSERS.get(ext)

    if not parser:
        msg = f"Unsupported file extension: {ext}"
        raise ValueError(msg)

    return parser


def parse_file(file_path: str) -> str:
    """Directly parse a file using the dispatcher.

    Args:
    ----
        file_path (str): Path to the file.

    Returns:
    -------
        str: Extracted text content.

    """
    parser = get_parser(file_path)
    return parser(file_path)


def parse_file_structured(
    file_path: str | Path,
    base_metadata: dict[str, Any] | None = None,
    pdf_parser: HierarchicalPDFParser | None = None,
) -> list[dict[str, Any]]:
    """Parse a document into structured elements with metadata.

    For PDFs, uses HierarchicalPDFParser (Unstructured.io / PyMuPDF) to
    extract page numbers, section hierarchy, clause references, etc.
    For HTML, extracts text via BeautifulSoup.

    Args:
        file_path: Path to the document.
        base_metadata: Document-level metadata (title, jurisdiction, etc.)
            to merge into every element's metadata.
        pdf_parser: Pre-configured HierarchicalPDFParser instance.
            If None, a default instance is created.

    Returns:
        List of ``{"content": str, "metadata": dict}`` elements.
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        if pdf_parser is None:
            from .layout_parser import HierarchicalPDFParser as _HP

            pdf_parser = _HP()
        return pdf_parser.parse_with_structure(file_path, base_metadata)

    if ext in (".html", ".htm"):
        return parse_html_structured(str(file_path), base_metadata)

    msg = f"Unsupported file type for structured parsing: {ext}"
    raise ValueError(msg)

# etl/parsers/pdf_parser.py

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from green_gov_rag.etl.utils import clean_text


class PDFParser:
    """Parser for extracting and cleaning text from PDF files."""

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

    def extract_text(self) -> str:
        """Extract raw text from the entire PDF."""
        text = []
        with fitz.open(self.filepath) as doc:
            for page in doc:
                text.append(page.get_text())
        return "\n".join(text)

    def parse(self) -> list[str]:
        """Parse the PDF and return a list of cleaned text chunks.
        You could later add chunking logic here (e.g., 500 tokens).
        """
        raw_text = self.extract_text()
        cleaned = clean_text(raw_text)
        return [cleaned] if cleaned else []


def parse_pdf(file_path: str | Path) -> str:
    """Parse a PDF file and return cleaned text.

    Args:
        file_path: Path to the PDF file

    Returns:
        Cleaned text content from the PDF
    """
    parser = PDFParser(file_path)
    chunks = parser.parse()
    return "\n".join(chunks) if chunks else ""


# Example usage:
# from etl.parsers.pdf_parser import PDFParser
#
# parser = PDFParser("data/sample.pdf")
# chunks = parser.parse()
#
# print(chunks[0][:500])  # preview first 500 chars

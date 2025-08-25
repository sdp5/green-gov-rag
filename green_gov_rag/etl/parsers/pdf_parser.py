# etl/parsers/pdf_parser.py
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from etl.utils import clean_text


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

    def parse(self) -> List[str]:
        """
        Parse the PDF and return a list of cleaned text chunks.
        You could later add chunking logic here (e.g., 500 tokens).
        """
        raw_text = self.extract_text()
        cleaned = clean_text(raw_text)
        return [cleaned] if cleaned else []


# Example usage:
# from etl.parsers.pdf_parser import PDFParser
#
# parser = PDFParser("data/sample.pdf")
# chunks = parser.parse()
#
# print(chunks[0][:500])  # preview first 500 chars

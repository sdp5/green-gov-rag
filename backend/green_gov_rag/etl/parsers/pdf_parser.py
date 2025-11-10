# etl/parsers/pdf_parser.py

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from green_gov_rag.etl.utils import clean_text
from green_gov_rag.types import (
    PDF_CHAPTER_KEYWORDS,
    PDF_HEADING_FONT_SIZE_THRESHOLD,
    PDF_HEADING_MAX_LENGTH,
    PDF_HEADING_TITLE_CASE_MAX_LENGTH,
    PDF_SECTION_KEYWORDS,
    ChunkType,
    ClausePrefix,
)


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


class StructuredPDFParser:
    """Parser for extracting structured content with citation metadata from PDFs.

    Uses PyMuPDF to detect headings, extract page numbers, and build section hierarchy.
    This is a fallback parser when Unstructured.io is not available or fails.
    """

    def __init__(self, filepath: str | Path):
        """Initialize structured PDF parser.

        Args:
        ----
            filepath: Path to PDF file

        """
        self.filepath = Path(filepath)

    def parse_with_structure(
        self, base_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Extract chunks with hierarchical metadata from PDF.

        Args:
        ----
            base_metadata: Base metadata to include in all chunks

        Returns:
        -------
            List of chunk dictionaries with citation metadata

        """
        base_metadata = base_metadata or {}
        doc = fitz.open(self.filepath)

        sections: list[dict[str, Any]] = []
        current_section: dict[str, Any] | None = None
        section_stack: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    text = ""
                    font_sizes = []

                    for span in line["spans"]:
                        text += span["text"]
                        font_sizes.append(span["size"])

                    if not text.strip():
                        continue

                    avg_font = sum(font_sizes) / len(font_sizes) if font_sizes else 0

                    # Detect headings (larger font or formatted text)
                    if self._is_heading(text, avg_font):
                        # Save previous section
                        if current_section and current_section["content"].strip():
                            sections.append(current_section)

                        # Update section hierarchy
                        heading = text.strip()
                        level = self._infer_heading_level(heading)
                        self._update_section_stack(section_stack, heading, level)

                        # Start new section
                        current_section = {
                            "content": "",
                            "metadata": {
                                **base_metadata,
                                "page_number": page_num + 1,
                                "page_range": [page_num + 1, page_num + 1],
                                "section_title": heading,
                                "section_hierarchy": section_stack.copy(),
                                "section_level": len(section_stack),
                                "clause_reference": self._extract_clause_reference(
                                    heading, section_stack
                                ),
                                "chunk_type": ChunkType.HEADER.value,
                            },
                        }
                    elif current_section:
                        # Add to current section
                        current_section["content"] += text + " "
                        # Update page range
                        if page_num + 1 > current_section["metadata"]["page_range"][1]:
                            current_section["metadata"]["page_range"][1] = page_num + 1
                    else:
                        # No section yet, create default section
                        current_section = {
                            "content": text + " ",
                            "metadata": {
                                **base_metadata,
                                "page_number": page_num + 1,
                                "page_range": [page_num + 1, page_num + 1],
                                "section_title": "",
                                "section_hierarchy": [],
                                "section_level": 0,
                                "clause_reference": None,
                                "chunk_type": ChunkType.PARAGRAPH.value,
                            },
                        }

        # Save last section
        if current_section and current_section["content"].strip():
            sections.append(current_section)

        doc.close()

        # Add chunk_id to each section
        for i, section in enumerate(sections):
            section["metadata"]["chunk_id"] = i

        return sections

    def _is_heading(self, text: str, font_size: float) -> bool:
        """Detect if text is a heading based on heuristics.

        Args:
        ----
            text: Text to check
            font_size: Average font size

        Returns:
        -------
            True if text appears to be a heading

        """
        text_stripped = text.strip()

        # Check font size (headings typically larger than threshold)
        if font_size > PDF_HEADING_FONT_SIZE_THRESHOLD:
            return True

        # Check for numbered sections (e.g., "1.", "1.1.", "Section 1")
        if re.match(r"^\d+\.?\s+[A-Z]", text_stripped):
            return True
        if re.match(
            r"^(Chapter|Part|Section|Clause)\s+\d+", text_stripped, re.IGNORECASE
        ):
            return True

        # Check for ALL CAPS (but not too long)
        if text_stripped.isupper() and 5 < len(text_stripped) < PDF_HEADING_MAX_LENGTH:
            return True

        # Check for title case with short length
        if (
            text_stripped.istitle()
            and len(text_stripped) < PDF_HEADING_TITLE_CASE_MAX_LENGTH
            and not text_stripped.endswith(".")
        ):
            return True

        return False

    def _infer_heading_level(self, text: str) -> int:
        """Infer heading level from text patterns.

        Args:
        ----
            text: Heading text

        Returns:
        -------
            Heading level (1-6)

        """
        # Check for numbered sections
        match = re.match(r"^(\d+(?:\.\d+)*)", text)
        if match:
            levels = match.group(1).count(".") + 1
            return min(levels, 6)

        # Check for keywords
        for keyword in PDF_CHAPTER_KEYWORDS:
            if re.match(rf"^{keyword}\s+", text, re.IGNORECASE):
                return 1
        for keyword in PDF_SECTION_KEYWORDS:
            if re.match(rf"^{keyword}\s+", text, re.IGNORECASE):
                return 2

        # All caps = higher level
        if text.isupper():
            return 2

        return 3

    def _update_section_stack(
        self, section_stack: list[str], heading: str, level: int
    ) -> None:
        """Update section hierarchy stack.

        Args:
        ----
            section_stack: Current hierarchy (modified in place)
            heading: New heading
            level: Heading level

        """
        while len(section_stack) >= level:
            section_stack.pop()
        section_stack.append(heading.strip())

    def _extract_clause_reference(
        self, text: str, section_hierarchy: list[str]
    ) -> str | None:
        """Extract clause/section reference from text.

        Args:
        ----
            text: Text to extract from
            section_hierarchy: Current section hierarchy

        Returns:
        -------
            Formatted clause reference or None

        """
        # Try current text first
        clause_ref = self._extract_clause_from_text(text)
        if clause_ref:
            return clause_ref

        # Try last section in hierarchy
        if section_hierarchy:
            clause_ref = self._extract_clause_from_text(section_hierarchy[-1])
            if clause_ref:
                return clause_ref

        return None

    def _extract_clause_from_text(self, text: str) -> str | None:
        """Extract clause reference from single text string.

        Args:
        ----
            text: Text to extract from

        Returns:
        -------
            Formatted clause reference or None

        """
        if not text:
            return None

        # Pattern 1: Section numbers
        match = re.search(
            r"(?:section|s\.?)\s*(\d+(?:\.\d+)*(?:\([a-z0-9]+\))*[A-Z]*)",
            text,
            re.IGNORECASE,
        )
        if match:
            return f"{ClausePrefix.SECTION.value}.{match.group(1)}"

        # Pattern 2: Standalone numbers at start
        match = re.match(r"^(\d+(?:\.\d+)*(?:\([a-z0-9]+\))*[A-Z]*)", text)
        if match:
            return f"{ClausePrefix.SECTION.value}.{match.group(1)}"

        # Pattern 3: Clause references
        match = re.search(r"(?:clause|cl\.?)\s*(\d+)", text, re.IGNORECASE)
        if match:
            return f"{ClausePrefix.CLAUSE.value}.{match.group(1)}"

        # Pattern 4: Regulation references
        match = re.search(r"(?:regulation|reg\.?)\s*(\d+)", text, re.IGNORECASE)
        if match:
            return f"{ClausePrefix.REGULATION.value}.{match.group(1)}"

        return None


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

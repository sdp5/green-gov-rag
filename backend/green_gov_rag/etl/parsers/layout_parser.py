"""Hierarchical PDF parser with multiple backends for citation extraction.

Extracts PDFs with section hierarchy, page numbers, and structural context
for improved RAG retrieval and citation quality.

Uses Unstructured.io as primary parser with PyMuPDF as fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class HierarchicalPDFParser:
    """Parse PDFs with hierarchical structure using multiple backends.

    Features:
    - Section hierarchy extraction (chapters, sections, subsections)
    - Page number tracking
    - Table detection and association with sections
    - List recognition and grouping
    - Context-aware chunking that preserves document structure

    Uses Unstructured.io as primary parser, PyMuPDF as fallback.

    Example:
    -------
        >>> parser = HierarchicalPDFParser()
        >>> chunks = parser.parse_with_structure("policy.pdf")
        >>> print(chunks[0]["metadata"]["section_hierarchy"])
        ["Chapter 3", "Section 3.2", "3.2.1 Calculation Methods"]

    """

    def __init__(self) -> None:
        """Initialize hierarchical PDF parser with fallback support."""
        # Lazy import to avoid import errors
        from green_gov_rag.etl.parsers.pdf_parser import StructuredPDFParser
        from green_gov_rag.etl.parsers.unstructured_parser import UnstructuredPDFParser

        self._unstructured_parser: UnstructuredPDFParser | None = None
        self._pymupdf_parser: StructuredPDFParser | None = None

    def parse_with_structure(
        self,
        pdf_path: str | Path,
        base_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract chunks with hierarchical metadata from PDF.

        Args:
        ----
            pdf_path: Path to PDF file
            base_metadata: Base metadata to include in all chunks (e.g., jurisdiction, topic)

        Returns:
        -------
            List of chunk dictionaries with rich metadata including:
            - content: Chunk text with contextual headers
            - metadata: Enhanced metadata with section hierarchy, page numbers, etc.

        """
        pdf_path = Path(pdf_path)
        base_metadata = base_metadata or {}

        # Try Unstructured.io first (primary parser)
        try:
            if self._unstructured_parser is None:
                from green_gov_rag.etl.parsers.unstructured_parser import (
                    UnstructuredPDFParser,
                )

                self._unstructured_parser = UnstructuredPDFParser()

            return self._unstructured_parser.parse_with_structure(
                pdf_path, base_metadata
            )

        except Exception as e:
            # Fall back to PyMuPDF parser
            try:
                if self._pymupdf_parser is None:
                    from green_gov_rag.etl.parsers.pdf_parser import StructuredPDFParser

                    self._pymupdf_parser = StructuredPDFParser(pdf_path)
                else:
                    # Update filepath for new document
                    self._pymupdf_parser.filepath = pdf_path

                return self._pymupdf_parser.parse_with_structure(base_metadata)

            except Exception as fallback_error:
                # If both parsers fail, raise informative error
                error_msg = (
                    f"Failed to parse PDF with all available parsers.\n"
                    f"Unstructured.io error: {e}\n"
                    f"PyMuPDF error: {fallback_error}"
                )
                raise RuntimeError(error_msg) from fallback_error

    def parse_simple(self, pdf_path: str | Path) -> list[dict[str, Any]]:
        """Simple extraction without hierarchy (fallback method).

        Args:
        ----
            pdf_path: Path to PDF file

        Returns:
        -------
            List of basic chunks with minimal metadata

        """
        from green_gov_rag.etl.parsers.pdf_parser import PDFParser

        parser = PDFParser(pdf_path)
        text = parser.extract_text()

        return [
            {
                "content": text,
                "metadata": {
                    "chunk_id": 0,
                    "source": Path(pdf_path).name,
                },
            }
        ]


# Backward compatibility: create alias for existing code
LayoutPDFParser = HierarchicalPDFParser

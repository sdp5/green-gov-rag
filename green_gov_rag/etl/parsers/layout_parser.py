"""Hierarchical PDF parser using LLMSherpa LayoutPDFReader.

Extracts PDFs with section hierarchy, page numbers, and structural context
for improved RAG retrieval and citation quality.

Based on industry best practices from LlamaIndex/LLMSherpa (2025).
"""

from pathlib import Path
from typing import Any

from llmsherpa.readers import LayoutPDFReader


class HierarchicalPDFParser:
    """Parse PDFs with hierarchical structure using LLMSherpa LayoutPDFReader.

    Features:
    - Section hierarchy extraction (chapters, sections, subsections)
    - Page number tracking
    - Table detection and association with sections
    - List recognition and grouping
    - Context-aware chunking that preserves document structure

    Example:
        >>> parser = HierarchicalPDFParser()
        >>> chunks = parser.parse_with_structure("policy.pdf")
        >>> print(chunks[0]["metadata"]["section_hierarchy"])
        ["Chapter 3", "Section 3.2", "3.2.1 Calculation Methods"]
    """

    def __init__(self, api_url: str | None = None) -> None:
        """Initialize hierarchical PDF parser.

        Args:
            api_url: LLMSherpa API endpoint. Defaults to public API.
                    For production, consider self-hosting.
        """
        self.api_url = api_url or (
            "https://readers.llmsherpa.com/api/document/developer/"
            "parseDocument?renderFormat=all"
        )
        self.reader = LayoutPDFReader(self.api_url)

    def parse_with_structure(
        self, pdf_path: str | Path, base_metadata: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Extract chunks with hierarchical metadata from PDF.

        Args:
            pdf_path: Path to PDF file
            base_metadata: Base metadata to include in all chunks (e.g., jurisdiction, topic)

        Returns:
            List of chunk dictionaries with rich metadata including:
            - content: Chunk text with contextual headers
            - metadata: Enhanced metadata with section hierarchy, page numbers, etc.
        """
        pdf_path = Path(pdf_path)
        base_metadata = base_metadata or {}

        # Parse PDF with LayoutPDFReader
        doc = self.reader.read_pdf(str(pdf_path))

        chunks = []
        for chunk_idx, chunk in enumerate(doc.chunks()):
            # Extract hierarchical context
            section_hierarchy = self._extract_hierarchy(chunk)
            section_title = self._extract_section_title(chunk)
            chunk_type = self._get_chunk_type(chunk)

            # Build chunk with metadata
            chunk_data = {
                "content": chunk.to_context_text(),  # Includes section headers as context
                "metadata": {
                    **base_metadata,
                    # Chunk identification
                    "chunk_id": chunk_idx,
                    "chunk_type": chunk_type,  # paragraph, table, list, header
                    # Page information
                    "page_number": chunk.page_idx + 1
                    if hasattr(chunk, "page_idx")
                    else None,
                    # Section hierarchy
                    "section_hierarchy": section_hierarchy,
                    "section_title": section_title,
                    "section_level": len(section_hierarchy),
                    "parent_sections": section_hierarchy[:-1]
                    if section_hierarchy
                    else [],
                    # For citation building
                    "heading_hierarchy": section_hierarchy,  # Alias for compatibility
                },
            }

            chunks.append(chunk_data)

        return chunks

    def _extract_hierarchy(self, chunk: Any) -> list[str]:
        """Extract section hierarchy from chunk.

        Args:
            chunk: LLMSherpa chunk object

        Returns:
            List of section titles from top-level to current section
            e.g., ["Chapter 3", "Section 3.2", "3.2.1 Methods"]
        """
        hierarchy = []

        # Try to get parent chain if available
        if hasattr(chunk, "parent_chain") and callable(chunk.parent_chain):
            try:
                parent_chain = chunk.parent_chain()
                if parent_chain:
                    hierarchy = [str(p) for p in parent_chain]
            except Exception:  # noqa: BLE001, S110
                pass

        # Fallback: try to get section from chunk attributes
        if not hierarchy and hasattr(chunk, "sections"):
            try:
                sections = chunk.sections()
                if sections:
                    hierarchy = [str(s) for s in sections]
            except Exception:  # noqa: BLE001, S110
                pass

        return hierarchy

    def _extract_section_title(self, chunk: Any) -> str:
        """Extract current section title from chunk.

        Args:
            chunk: LLMSherpa chunk object

        Returns:
            Section title or empty string if not available
        """
        # Try multiple methods to extract section title
        if hasattr(chunk, "section_title"):
            return str(chunk.section_title)

        if hasattr(chunk, "title"):
            return str(chunk.title)

        # If part of hierarchy, use last element
        hierarchy = self._extract_hierarchy(chunk)
        if hierarchy:
            return hierarchy[-1]

        return ""

    def _get_chunk_type(self, chunk: Any) -> str:
        """Determine chunk type (paragraph, table, list, header).

        Args:
            chunk: LLMSherpa chunk object

        Returns:
            Chunk type string
        """
        if hasattr(chunk, "tag"):
            tag = str(chunk.tag).lower()
            # Map LLMSherpa tags to standardized types
            if "table" in tag:
                return "table"
            if "list" in tag or "item" in tag:
                return "list"
            if any(h in tag for h in ["h1", "h2", "h3", "h4", "h5", "h6", "header"]):
                return "header"

        return "paragraph"

    def parse_simple(self, pdf_path: str | Path) -> list[dict[str, Any]]:
        """Simple extraction without hierarchy (fallback method).

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of basic chunks with minimal metadata
        """
        pdf_path = Path(pdf_path)
        doc = self.reader.read_pdf(str(pdf_path))

        chunks = []
        for chunk_idx, chunk in enumerate(doc.chunks()):
            chunks.append(
                {
                    "content": chunk.to_text()
                    if hasattr(chunk, "to_text")
                    else str(chunk),
                    "metadata": {
                        "chunk_id": chunk_idx,
                        "source": pdf_path.name,
                    },
                }
            )

        return chunks


# Backward compatibility: create alias for existing code
LayoutPDFParser = HierarchicalPDFParser


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python layout_parser.py <pdf_path>")
        sys.exit(1)

    parser = HierarchicalPDFParser()
    chunks = parser.parse_with_structure(sys.argv[1])

    print(f"\n📄 Extracted {len(chunks)} chunks with hierarchical structure:\n")

    for i, chunk in enumerate(chunks[:3], 1):  # Show first 3 chunks
        metadata = chunk["metadata"]
        print(f"Chunk {i}:")
        print(f"  Type: {metadata.get('chunk_type')}")
        print(f"  Page: {metadata.get('page_number')}")
        print(f"  Section: {metadata.get('section_title')}")
        print(f"  Hierarchy: {' > '.join(metadata.get('section_hierarchy', []))}")
        print(f"  Content preview: {chunk['content'][:100]}...")
        print()

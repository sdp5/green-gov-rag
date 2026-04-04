"""Unstructured.io PDF parser for extracting structured document content.

Extracts PDFs with section hierarchy, page numbers, and structural context
for improved RAG retrieval and citation quality using Unstructured.io library.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from unstructured.partition.pdf import partition_pdf

from green_gov_rag.types import (
    UNSTRUCTURED_ELEMENT_TYPE_MAP,
    ChunkType,
    ClausePrefix,
    PDFParserStrategy,
)


class UnstructuredPDFParser:
    """Parse PDFs with hierarchical structure using Unstructured.io.

    Features:
    - Section hierarchy extraction (chapters, sections, subsections)
    - Page number tracking
    - Table detection and association with sections
    - List recognition and grouping
    - Context-aware chunking that preserves document structure

    Example:
    -------
        >>> parser = UnstructuredPDFParser()
        >>> chunks = parser.parse_with_structure("policy.pdf")
        >>> print(chunks[0]["metadata"]["section_hierarchy"])
        ["Chapter 3", "Section 3.2", "3.2.1 Calculation Methods"]

    """

    def __init__(
        self,
        strategy: str = PDFParserStrategy.HI_RES.value,
        extract_images: bool = False,
    ) -> None:
        """Initialize Unstructured PDF parser.

        Args:
        ----
            strategy: Parsing strategy - "hi_res" for detailed analysis (slower),
                     "fast" for quick parsing, or "auto" for automatic selection.
                     Recommended: "hi_res" for regulatory documents.
            extract_images: Whether to extract images from the PDF. Useful for
                     vision-heavy documents (planning maps, diagrams). Default False.

        """
        self.strategy = strategy
        self.extract_images = extract_images

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

        # Parse PDF with Unstructured.io
        elements = partition_pdf(
            str(pdf_path),
            strategy=self.strategy,
            infer_table_structure=True,
            include_page_breaks=True,
            extract_images_in_pdf=self.extract_images,
        )

        # Track section hierarchy as we process elements
        section_stack: list[str] = []
        chunks = []

        for chunk_idx, element in enumerate(elements):
            # Get element metadata
            element_metadata = element.metadata.to_dict() if element.metadata else {}
            page_number = element_metadata.get("page_number")

            # Determine element type
            element_type = element.category if hasattr(element, "category") else "text"
            text = str(element)

            # Update section hierarchy based on element type
            if element_type == "Title":
                # This is a heading - update section stack
                level = self._infer_heading_level(text)
                self._update_section_stack(section_stack, text, level)

            # Skip empty elements
            if not text.strip():
                continue

            # Extract citation information
            section_hierarchy = section_stack.copy()
            section_title = section_stack[-1] if section_stack else ""
            clause_reference = self._extract_clause_reference(text, section_hierarchy)

            # Build page range (for now, single page per element)
            page_range = [page_number, page_number] if page_number else None

            # Build chunk with metadata
            chunk_data = {
                "content": text,
                "metadata": {
                    **base_metadata,
                    # Chunk identification
                    "chunk_id": chunk_idx,
                    "chunk_type": self._map_element_type(element_type),
                    # Page information
                    "page_number": page_number,
                    "page_range": page_range,
                    # Section hierarchy
                    "section_hierarchy": section_hierarchy,
                    "section_title": section_title,
                    "section_level": len(section_hierarchy),
                    "parent_sections": section_hierarchy[:-1]
                    if section_hierarchy
                    else [],
                    # Clause/section reference (for legal citations)
                    "clause_reference": clause_reference,
                    # For citation building
                    "heading_hierarchy": section_hierarchy,  # Alias for compatibility
                },
            }

            chunks.append(chunk_data)

        return chunks

    def _infer_heading_level(self, text: str) -> int:
        """Infer heading level from text patterns.

        Args:
        ----
            text: Heading text

        Returns:
        -------
            Heading level (1-6), where 1 is highest level

        """
        text = text.strip()

        # Check for numbered sections (e.g., "1.", "1.1.", "1.1.1.")
        match = re.match(r"^(\d+(?:\.\d+)*)", text)
        if match:
            levels = match.group(1).count(".") + 1
            return min(levels, 6)

        # Check for "Chapter", "Part", "Section" keywords
        if re.match(r"^(Chapter|Part)\s+", text, re.IGNORECASE):
            return 1
        if re.match(r"^Section\s+", text, re.IGNORECASE):
            return 2

        # All caps headings are typically higher level
        if text.isupper() and len(text) < 100:
            return 2

        # Default to level 3
        return 3

    def _update_section_stack(
        self, section_stack: list[str], heading: str, level: int
    ) -> None:
        """Update section hierarchy stack with new heading.

        Args:
        ----
            section_stack: Current section hierarchy (modified in place)
            heading: New heading text
            level: Heading level (1-6)

        """
        # Trim stack to appropriate level
        while len(section_stack) >= level:
            section_stack.pop()

        # Add new heading
        section_stack.append(heading.strip())

    def _map_element_type(self, element_type: str) -> str:
        """Map Unstructured element type to standardized chunk type.

        Args:
        ----
            element_type: Unstructured element category

        Returns:
        -------
            Standardized chunk type: paragraph, table, list, header

        """
        return UNSTRUCTURED_ELEMENT_TYPE_MAP.get(
            element_type, ChunkType.PARAGRAPH.value
        )

    def _extract_clause_reference(
        self, text: str, section_hierarchy: list[str]
    ) -> str | None:
        """Extract clause/section reference from text or hierarchy.

        Extracts structured references like:
        - Section numbers: "3.2.1" → "s.3.2.1"
        - Clause numbers: "Clause 42" → "cl.42"
        - Subsections: "5(2)(a)" → "s.5(2)(a)"
        - Regulations: "Regulation 12" → "reg.12"

        Args:
        ----
            text: Element text
            section_hierarchy: Section hierarchy from parser

        Returns:
        -------
            Formatted clause reference string or None

        Examples:
        --------
            >>> _extract_clause_reference("Section 3.2.1 Methods", [])
            "s.3.2.1"
            >>> _extract_clause_reference("Clause 42", [])
            "cl.42"

        """
        # First, try to extract from current text
        clause_ref = self._extract_clause_from_text(text)
        if clause_ref:
            return clause_ref

        # If not found, check section hierarchy (last element is most specific)
        if section_hierarchy:
            clause_ref = self._extract_clause_from_text(section_hierarchy[-1])
            if clause_ref:
                return clause_ref

        return None

    def _extract_clause_from_text(self, text: str) -> str | None:
        """Extract clause reference from a single text string.

        Args:
        ----
            text: Text to extract from

        Returns:
        -------
            Formatted clause reference or None

        """
        if not text:
            return None

        # Pattern 1: Section numbers with optional brackets/letters
        match = re.search(
            r"(?:section|s\.?)\s*(\d+(?:\.\d+)*(?:\([a-z0-9]+\))*[A-Z]*)",
            text,
            re.IGNORECASE,
        )
        if match:
            return f"{ClausePrefix.SECTION.value}.{match.group(1)}"

        # Pattern 2: Standalone section numbers at start
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

        # Pattern 5: Subsection with brackets
        match = re.search(r"(\d+(?:\([a-z0-9]+\))+)", text, re.IGNORECASE)
        if match:
            return f"{ClausePrefix.SECTION.value}.{match.group(1)}"

        # Pattern 6: Schedule/Annex references
        match = re.search(r"(schedule|annex)\s+([A-Z0-9]+)", text, re.IGNORECASE)
        if match:
            schedule_type = match.group(1).lower()
            if schedule_type.startswith("sch"):
                prefix = ClausePrefix.SCHEDULE.value
            else:
                prefix = ClausePrefix.ANNEX.value
            return f"{prefix}.{match.group(2)}"

        # Pattern 7: Part references
        match = re.search(r"part\s+([IVX0-9]+)", text, re.IGNORECASE)
        if match:
            return f"{ClausePrefix.PART.value}.{match.group(1)}"

        return None

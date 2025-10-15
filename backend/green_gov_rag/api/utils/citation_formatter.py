"""Citation formatting utilities for legal-grade document references.

Formats hierarchical metadata from PDF parsing into professional citations
following legal RAG best practices.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


class CitationFormatter:
    """Format document metadata into legal-grade citations."""

    @staticmethod
    def format_citation(
        title: str,
        page_number: int | None = None,
        section_title: str | None = None,
        clause_reference: str | None = None,
        year: int | None = None,
        regulator: str | None = None,
    ) -> str:
        """Format a citation string from document metadata.

        Args:
        ----
            title: Document title
            page_number: Page number where content appears
            section_title: Section title or heading
            clause_reference: Clause/section reference (e.g., "s.3.2.1")
            year: Publication year (defaults to current year)
            regulator: Issuing regulatory authority

        Returns:
        -------
            Formatted citation string

        Examples:
        --------
            >>> CitationFormatter.format_citation(
            ...     title="Scope 2 Emissions Guideline",
            ...     page_number=42,
            ...     section_title="Market-Based Accounting",
            ...     clause_reference="s.3.2.1",
            ...     regulator="Clean Energy Regulator"
            ... )
            "Clean Energy Regulator (2025), Scope 2 Emissions Guideline, Page 42, Section 3.2.1"

        """
        parts = []

        # Add regulator/author if available
        if regulator:
            year_str = f"({year or datetime.now().year})"
            parts.append(f"{regulator} {year_str}")

        # Add title
        parts.append(title)

        # Add page number if available
        if page_number:
            parts.append(f"Page {page_number}")

        # Add clause reference or section title
        if clause_reference:
            parts.append(f"Section {clause_reference}")
        elif section_title:
            parts.append(section_title)

        return ", ".join(parts)

    @staticmethod
    def build_deep_link(
        source_url: str,
        page_number: int | None = None,
        section_id: str | None = None,
    ) -> str:
        """Build a deep link to a specific section/page in a document.

        Args:
        ----
            source_url: Base URL of the document
            page_number: Page number to link to
            section_id: HTML section ID or PDF anchor

        Returns:
        -------
            Deep link URL

        Examples:
        --------
            >>> CitationFormatter.build_deep_link(
            ...     source_url="https://cer.gov.au/doc.pdf",
            ...     page_number=42
            ... )
            "https://cer.gov.au/doc.pdf#page=42"

        """
        if not page_number and not section_id:
            return source_url

        # PDF deep linking
        if source_url.endswith(".pdf"):
            if page_number:
                return f"{source_url}#page={page_number}"
            if section_id:
                return f"{source_url}#{section_id}"

        # HTML deep linking
        if section_id:
            return f"{source_url}#{section_id}"

        # Default: return base URL
        return source_url

    @staticmethod
    def extract_section_id(
        section_hierarchy: list[str] | None,
        clause_reference: str | None = None,
    ) -> str | None:
        """Extract a URL-friendly section ID from hierarchy or clause reference.

        Args:
        ----
            section_hierarchy: List of section titles
            clause_reference: Clause reference (e.g., "s.3.2.1")

        Returns:
        -------
            URL-friendly section ID or None

        Examples:
        --------
            >>> CitationFormatter.extract_section_id(
            ...     section_hierarchy=["Part 3", "Section 3.2", "3.2.1 Methods"],
            ...     clause_reference="s.3.2.1"
            ... )
            "section-3-2-1"

        """
        if clause_reference:
            # Convert "s.3.2.1" -> "section-3-2-1"
            section_id = clause_reference.replace("s.", "section-").replace(".", "-")
            return section_id.lower()

        if section_hierarchy and len(section_hierarchy) > 0:
            # Use the last (most specific) section from hierarchy
            last_section = section_hierarchy[-1]
            # Extract section number if present (e.g., "3.2.1 Methods" -> "3-2-1")
            import re

            match = re.search(r"(\d+(?:\.\d+)*)", last_section)
            if match:
                section_num = match.group(1).replace(".", "-")
                return f"section-{section_num}"

        return None

    @staticmethod
    def format_section_hierarchy_display(
        section_hierarchy: list[str] | None,
    ) -> str | None:
        """Format section hierarchy for display (breadcrumb-style).

        Args:
        ----
            section_hierarchy: List of section titles from top to bottom

        Returns:
        -------
            Formatted hierarchy string or None

        Examples:
        --------
            >>> CitationFormatter.format_section_hierarchy_display([
            ...     "Part 3: Scope 2 Emissions",
            ...     "Section 3.2: Calculation Methods",
            ...     "3.2.1 Market-Based Accounting"
            ... ])
            "Part 3 > Section 3.2 > 3.2.1"

        """
        if not section_hierarchy:
            return None

        # Shorten each section for display (keep main identifier)
        shortened = []
        for section in section_hierarchy:
            # Extract main identifier (e.g., "Part 3", "Section 3.2", "3.2.1")
            import re

            # Match patterns like "Part 3:", "Section 3.2:", "3.2.1 "
            match = re.match(
                r"((?:Part|Section|Chapter)\s+[\d.]+|[\d.]+)", section, re.IGNORECASE
            )
            if match:
                shortened.append(match.group(1))
            else:
                # If no pattern match, take first 30 chars
                shortened.append(section[:30])

        return " > ".join(shortened)

    @staticmethod
    def enrich_source_document(source_doc: dict[str, Any]) -> dict[str, Any]:
        """Enrich source document with formatted citation and deep links.

        Takes a source document dict with metadata and adds:
        - citation: Formatted citation string
        - deep_link: Deep link to specific page/section
        - section_hierarchy formatted for display

        Args:
        ----
            source_doc: Source document dictionary with metadata

        Returns:
        -------
            Enriched source document dictionary

        """
        metadata = source_doc.get("metadata", {})

        # Extract citation components
        title = source_doc.get("title") or metadata.get("title", "")
        source_url = source_doc.get("source_url") or metadata.get("source_url", "")
        page_number = metadata.get("page_number")
        section_title = metadata.get("section_title")
        section_hierarchy = metadata.get("section_hierarchy")
        clause_reference = metadata.get("clause_reference")

        # Extract regulator from esg_metadata if available
        esg_metadata = metadata.get("esg_metadata", {})
        regulator = esg_metadata.get("regulator")

        # Format citation
        citation = CitationFormatter.format_citation(
            title=title,
            page_number=page_number,
            section_title=section_title,
            clause_reference=clause_reference,
            regulator=regulator,
        )

        # Build deep link
        section_id = CitationFormatter.extract_section_id(
            section_hierarchy, clause_reference
        )
        deep_link = CitationFormatter.build_deep_link(
            source_url=source_url,
            page_number=page_number,
            section_id=section_id,
        )

        # Format section hierarchy for display
        hierarchy_display = CitationFormatter.format_section_hierarchy_display(
            section_hierarchy
        )

        # Enrich source document
        enriched = {
            **source_doc,
            "citation": citation,
            "deep_link": deep_link,
            "section_hierarchy_display": hierarchy_display,
        }

        return enriched


# Example usage
if __name__ == "__main__":
    # Example source document from RAG query
    source_doc: dict[str, Any] = {
        "title": "Scope 2 Emissions Guideline",
        "source_url": "https://cer.gov.au/document/voluntary-market-based-scope-2-emissions-guideline.pdf",
        "excerpt": "Market-based accounting requires documentation...",
        "metadata": {
            "page_number": 42,
            "section_title": "Market-Based Accounting Methods",
            "section_hierarchy": [
                "Part 3: Scope 2 Emissions Accounting",
                "Section 3.2: Calculation Methods",
                "3.2.1 Market-Based Accounting",
            ],
            "clause_reference": "s.3.2.1",
            "esg_metadata": {
                "regulator": "Clean Energy Regulator",
                "frameworks": ["NGER", "ISSB"],
            },
        },
    }

    # Enrich with citation metadata
    enriched = CitationFormatter.enrich_source_document(source_doc)

    print("=" * 70)
    print("Citation Formatter Demo")
    print("=" * 70)

    metadata: dict[str, Any] = source_doc.get("metadata", {})
    print(f"\nOriginal title: {source_doc.get('title', '')}")
    print(f"Page number: {metadata.get('page_number', '')}")
    print(f"Section: {metadata.get('section_title', '')}")

    print(f"\n✅ Formatted citation:\n   {enriched['citation']}")
    print(f"\n✅ Deep link:\n   {enriched['deep_link']}")
    print(
        f"\n✅ Section hierarchy display:\n   {enriched['section_hierarchy_display']}"
    )

    print("\n" + "=" * 70)
    print("Full enriched document:")
    print("=" * 70)
    import json

    print(json.dumps(enriched, indent=2))

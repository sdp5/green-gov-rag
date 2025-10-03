"""Enhanced Response Generator with Citations and Deep Links.

This module provides advanced RAG response formatting with:
1. Inline citations with source numbers [1], [2], etc.
2. Deep links to specific PDF pages/sections
3. Hierarchical section path display (e.g., "Section 2.1.3")
4. Source attribution with document metadata
5. Confidence scoring for cited passages
"""

from typing import Any

from langchain.docstore.document import Document


class Citation:
    """A citation linking answer text to source document."""

    def __init__(
        self,
        source_number: int,
        document: Document,
        text_snippet: str,
        confidence: float = 1.0,
    ):
        """Initialize citation.

        Args:
            source_number: Citation number (1, 2, 3, etc.)
            document: Source Document object
            text_snippet: Text excerpt that was cited
            confidence: Confidence score for this citation (0-1)
        """
        self.source_number = source_number
        self.document = document
        self.text_snippet = text_snippet
        self.confidence = confidence
        self.metadata = document.metadata

    def get_deep_link(self) -> str | None:
        """Generate deep link to specific page/section in PDF.

        Returns:
            URL with fragment identifier for PDF page
        """
        source_url = self.metadata.get("source_url")
        if not source_url:
            return None

        # Get page number if available
        page = self.metadata.get("page")
        if page is not None:
            # PDF page fragment (page=N)
            return f"{source_url}#page={page}"

        # Get section anchor if available
        section_id = self.metadata.get("section_id")
        if section_id:
            return f"{source_url}#{section_id}"

        return source_url

    def get_section_path(self) -> str | None:
        """Get hierarchical section path (e.g., 'Section 2.1.3').

        Returns:
            Formatted section path string
        """
        # Check for hierarchical metadata from LayoutPDFReader
        section_path = self.metadata.get("section_path")
        if section_path:
            return section_path

        # Fallback: construct from section_number and section_title
        section_num = self.metadata.get("section_number")
        section_title = self.metadata.get("section_title")

        if section_num and section_title:
            return f"Section {section_num}: {section_title}"
        elif section_num:
            return f"Section {section_num}"
        elif section_title:
            return section_title

        return None

    def format_citation_markdown(self) -> str:
        """Format citation as markdown with link.

        Returns:
            Markdown-formatted citation string
        """
        title = self.metadata.get("title", "Untitled Document")
        deep_link = self.get_deep_link()
        section_path = self.get_section_path()

        # Build citation components
        citation_parts = [f"[{self.source_number}]"]

        if deep_link:
            citation_parts.append(f"[{title}]({deep_link})")
        else:
            citation_parts.append(title)

        # Add section path if available
        if section_path:
            citation_parts.append(f"({section_path})")

        # Add page number if no section path
        elif "page" in self.metadata:
            citation_parts.append(f"(p. {self.metadata['page']})")

        return " ".join(citation_parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert citation to dictionary.

        Returns:
            Dict representation of citation
        """
        return {
            "source_number": self.source_number,
            "title": self.metadata.get("title", "Untitled"),
            "text_snippet": self.text_snippet,
            "confidence": self.confidence,
            "deep_link": self.get_deep_link(),
            "section_path": self.get_section_path(),
            "page": self.metadata.get("page"),
            "source_url": self.metadata.get("source_url"),
            "metadata": self.metadata,
        }


class EnhancedResponse:
    """Enhanced RAG response with inline citations and source attribution."""

    def __init__(self, answer: str, sources: list[Document], query: str):
        """Initialize enhanced response.

        Args:
            answer: Generated answer text
            sources: List of source Documents used
            query: Original user query
        """
        self.answer = answer
        self.sources = sources
        self.query = query
        self.citations: list[Citation] = []
        self._build_citations()

    def _build_citations(self) -> None:
        """Build citation objects from source documents."""
        for i, doc in enumerate(self.sources, start=1):
            # Create citation with snippet from document
            snippet = (
                doc.page_content[:200] + "..."
                if len(doc.page_content) > 200
                else doc.page_content
            )

            citation = Citation(
                source_number=i,
                document=doc,
                text_snippet=snippet,
                confidence=doc.metadata.get("relevance_score", 1.0),
            )
            self.citations.append(citation)

    def format_answer_with_inline_citations(self) -> str:
        """Format answer with inline citation markers.

        Returns:
            Answer text with inline [1], [2], etc. citations
        """
        # In a production system, this would use NLP to identify
        # which parts of the answer come from which sources
        # For now, add all citations at the end

        answer_with_citations = self.answer

        # Add citation markers if not already present
        if not any(f"[{i}]" in self.answer for i in range(1, len(self.sources) + 1)):
            # Append source indicators
            citation_markers = ", ".join(
                [f"[{i}]" for i in range(1, len(self.sources) + 1)]
            )
            answer_with_citations = f"{self.answer} {citation_markers}"

        return answer_with_citations

    def format_sources_markdown(self) -> str:
        """Format sources as markdown list with deep links.

        Returns:
            Markdown-formatted sources section
        """
        sources_md = ["## Sources\n"]

        for citation in self.citations:
            sources_md.append(citation.format_citation_markdown())
            sources_md.append("")  # Blank line

        return "\n".join(sources_md)

    def format_full_response_markdown(self) -> str:
        """Format complete response with answer and sources.

        Returns:
            Complete markdown response
        """
        parts = [
            f"**Query:** {self.query}\n",
            "## Answer\n",
            self.format_answer_with_inline_citations(),
            "\n",
            self.format_sources_markdown(),
        ]

        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary format.

        Returns:
            Dict representation for API/JSON responses
        """
        return {
            "query": self.query,
            "answer": self.answer,
            "answer_with_citations": self.format_answer_with_inline_citations(),
            "citations": [c.to_dict() for c in self.citations],
            "source_count": len(self.sources),
        }


class ResponseFormatter:
    """Utility class for formatting RAG responses with citations."""

    @staticmethod
    def create_enhanced_response(
        query: str,
        answer: str,
        sources: list[Document],
    ) -> EnhancedResponse:
        """Create an enhanced response with citations.

        Args:
            query: User query
            answer: Generated answer
            sources: Source documents

        Returns:
            EnhancedResponse object
        """
        return EnhancedResponse(answer=answer, sources=sources, query=query)

    @staticmethod
    def format_with_hierarchical_context(
        sources: list[Document],
    ) -> list[dict[str, Any]]:
        """Format sources with hierarchical section context.

        Args:
            sources: List of source documents

        Returns:
            List of formatted source dictionaries
        """
        formatted_sources = []

        for i, doc in enumerate(sources, start=1):
            metadata = doc.metadata

            # Extract hierarchical metadata
            section_hierarchy = {
                "section_path": metadata.get("section_path"),
                "section_number": metadata.get("section_number"),
                "section_title": metadata.get("section_title"),
                "parent_section": metadata.get("parent_section"),
                "section_level": metadata.get("section_level"),
            }

            # Build formatted source
            formatted_source = {
                "citation_number": i,
                "title": metadata.get("title", "Untitled"),
                "content_snippet": doc.page_content[:300],
                "page": metadata.get("page"),
                "source_url": metadata.get("source_url"),
                "hierarchy": section_hierarchy,
                "deep_link": ResponseFormatter._build_deep_link(metadata),
                "breadcrumb": ResponseFormatter._build_breadcrumb(metadata),
            }

            formatted_sources.append(formatted_source)

        return formatted_sources

    @staticmethod
    def _build_deep_link(metadata: dict) -> str | None:
        """Build deep link to specific section/page.

        Args:
            metadata: Document metadata dict

        Returns:
            Deep link URL or None
        """
        source_url = metadata.get("source_url")
        if not source_url:
            return None

        # Prefer section ID over page number
        section_id = metadata.get("section_id")
        if section_id:
            return f"{source_url}#{section_id}"

        # Fallback to page number
        page = metadata.get("page")
        if page is not None:
            return f"{source_url}#page={page}"

        return source_url

    @staticmethod
    def _build_breadcrumb(metadata: dict) -> str | None:
        """Build hierarchical breadcrumb (e.g., 'Document > Section 2 > Subsection 2.1').

        Args:
            metadata: Document metadata dict

        Returns:
            Breadcrumb string or None
        """
        parts = []

        # Document title
        title = metadata.get("title")
        if title:
            parts.append(title)

        # Section hierarchy
        section_path = metadata.get("section_path")
        if section_path:
            parts.append(section_path)
        else:
            # Fallback: build from section_number and section_title
            section_num = metadata.get("section_number")
            section_title = metadata.get("section_title")

            if section_num and section_title:
                parts.append(f"Section {section_num}: {section_title}")
            elif section_num:
                parts.append(f"Section {section_num}")
            elif section_title:
                parts.append(section_title)

        if not parts:
            return None

        return " > ".join(parts)


# Example usage
if __name__ == "__main__":
    from langchain.docstore.document import Document

    # Sample documents with hierarchical metadata
    sample_sources = [
        Document(
            page_content="NGER requires reporting of Scope 1 emissions from facilities exceeding 25,000 tonnes CO2-e annually.",
            metadata={
                "title": "NGER Act Explanatory Guide",
                "source_url": "https://www.cleanenergyregulator.gov.au/nger/guide.pdf",
                "page": 15,
                "section_number": "2.1.3",
                "section_title": "Scope 1 Emissions Thresholds",
                "section_path": "Part 2: Reporting Requirements > Section 2.1: Thresholds > 2.1.3 Scope 1",
                "section_level": 3,
            },
        ),
        Document(
            page_content="Scope 3 Category 4 covers upstream transportation and distribution of purchased goods.",
            metadata={
                "title": "GHG Protocol Scope 3 Standard",
                "source_url": "https://ghgprotocol.org/scope3-standard.pdf",
                "page": 42,
                "section_number": "4.1",
                "section_title": "Category 4: Upstream Transport",
                "section_path": "Chapter 4: Upstream Categories > 4.1 Transport and Distribution",
                "section_level": 2,
            },
        ),
    ]

    # Create enhanced response
    query = "What are the NGER Scope 1 thresholds?"
    answer = "NGER requires facilities to report Scope 1 emissions if they exceed 25,000 tonnes of CO2-e annually. This applies to direct emissions from owned or controlled sources."

    enhanced_response = ResponseFormatter.create_enhanced_response(
        query=query,
        answer=answer,
        sources=sample_sources,
    )

    # Display formatted response
    print("=" * 70)
    print("Enhanced Response with Citations")
    print("=" * 70)
    print(enhanced_response.format_full_response_markdown())

    print("\n" + "=" * 70)
    print("JSON Output")
    print("=" * 70)
    import json

    print(json.dumps(enhanced_response.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("Hierarchical Sources")
    print("=" * 70)
    hierarchical_sources = ResponseFormatter.format_with_hierarchical_context(
        sample_sources
    )
    print(json.dumps(hierarchical_sources, indent=2))

"""Hierarchical PDF parser with multiple backends for citation extraction.

Extracts PDFs with section hierarchy, page numbers, and structural context
for improved RAG retrieval and citation quality.

Uses Unstructured.io as primary parser with PyMuPDF as fallback.
Strategy selection priority:
  1. Per-document config override (parsing_strategy in YAML / base_metadata)
  2. CLI default_strategy (--fast / --accurate flag)
  3. Automatic PDFComplexityClassifier (default when neither override is set)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from green_gov_rag.types import PDFClassificationResult, PDFParserStrategy

logger = logging.getLogger(__name__)

# Map of YAML parsing_strategy strings to (PDFParserStrategy, extract_images)
_STRATEGY_MAP: dict[str, tuple[PDFParserStrategy, bool] | None] = {
    "fast": (PDFParserStrategy.FAST, False),
    "hi_res": (PDFParserStrategy.HI_RES, False),
    "hi_res_vision": (PDFParserStrategy.HI_RES, True),
    "auto": None,
}


def _classification_from_metadata(
    base_metadata: dict[str, Any],
) -> PDFClassificationResult | None:
    """Build a PDFClassificationResult from parsing_strategy in base_metadata.

    Returns None if no override is set or if the value is "auto".
    """
    raw = base_metadata.get("parsing_strategy")
    if raw is None:
        return None
    resolved = _STRATEGY_MAP.get(str(raw).lower())
    if resolved is None:
        return None
    strategy, extract_images = resolved
    return PDFClassificationResult(
        strategy=strategy,
        extract_images=extract_images,
        confidence=1.0,
        override_source="config",
    )


class HierarchicalPDFParser:
    """Parse PDFs with hierarchical structure using multiple backends.

    Features:
    - Section hierarchy extraction (chapters, sections, subsections)
    - Page number tracking
    - Table detection and association with sections
    - List recognition and grouping
    - Context-aware chunking that preserves document structure

    Uses Unstructured.io as primary parser, PyMuPDF as fallback.
    Automatically classifies each PDF to select the optimal strategy unless
    overridden by config or the CLI default_strategy.

    Example:
    -------
        >>> parser = HierarchicalPDFParser()
        >>> chunks = parser.parse_with_structure("policy.pdf")
        >>> print(chunks[0]["metadata"]["section_hierarchy"])
        ["Chapter 3", "Section 3.2", "3.2.1 Calculation Methods"]

    """

    def __init__(
        self,
        default_strategy: PDFParserStrategy | None = None,
        enable_classifier: bool = True,
    ) -> None:
        """Initialize hierarchical PDF parser.

        Args:
        ----
            default_strategy: Strategy to use for all documents when no per-doc
                override is present. None means "use classifier" (default).
                Set to PDFParserStrategy.FAST or HI_RES to apply uniformly
                (e.g., from the CLI --fast / --accurate flag).
            enable_classifier: Whether to run the complexity classifier when no
                override or default_strategy is set. Defaults to True.

        """
        self.default_strategy = default_strategy
        self.enable_classifier = enable_classifier

    def parse_with_structure(
        self,
        pdf_path: str | Path,
        base_metadata: dict[str, Any] | None = None,
        strategy_override: PDFClassificationResult | None = None,
    ) -> list[dict[str, Any]]:
        """Extract chunks with hierarchical metadata from PDF.

        Strategy resolution (highest priority first):
        1. ``strategy_override`` argument (set from per-doc config)
        2. ``parsing_strategy`` key in ``base_metadata`` (from .metadata.json sidecar)
        3. ``self.default_strategy`` (from CLI --fast / --accurate)
        4. ``PDFComplexityClassifier`` (auto-classification, default)

        Args:
        ----
            pdf_path: Path to PDF file.
            base_metadata: Base metadata to include in all chunks.  Also checked
                for a ``parsing_strategy`` key (written by ingest from YAML config).
            strategy_override: Explicit classification result.  Takes priority
                over all other sources.

        Returns:
        -------
            List of chunk dictionaries with rich metadata.

        """
        pdf_path = Path(pdf_path)
        base_metadata = base_metadata or {}

        classification = self._resolve_strategy(
            pdf_path, strategy_override, base_metadata
        )

        logger.info(
            "Parsing %s with strategy=%s extract_images=%s (source=%s)",
            pdf_path.name,
            classification.strategy.value,
            classification.extract_images,
            classification.override_source,
        )

        if classification.strategy == PDFParserStrategy.ADI:
            raise NotImplementedError(
                "Azure Document Intelligence strategy is not yet implemented."
            )

        # Try Unstructured.io first (primary parser) — create fresh per document
        # so each doc can have a different strategy without caching issues.
        try:
            from green_gov_rag.etl.parsers.unstructured_parser import (
                UnstructuredPDFParser,
            )

            unstructured_parser = UnstructuredPDFParser(
                strategy=classification.strategy.value,
                extract_images=classification.extract_images,
            )
            return unstructured_parser.parse_with_structure(pdf_path, base_metadata)

        except Exception as e:
            # Fall back to PyMuPDF parser
            try:
                from green_gov_rag.etl.parsers.pdf_parser import StructuredPDFParser

                pymupdf_parser = StructuredPDFParser(pdf_path)
                return pymupdf_parser.parse_with_structure(base_metadata)

            except Exception as fallback_error:
                error_msg = (
                    f"Failed to parse PDF with all available parsers.\n"
                    f"Unstructured.io error: {e}\n"
                    f"PyMuPDF error: {fallback_error}"
                )
                raise RuntimeError(error_msg) from fallback_error

    def _resolve_strategy(
        self,
        pdf_path: Path,
        strategy_override: PDFClassificationResult | None,
        base_metadata: dict[str, Any],
    ) -> PDFClassificationResult:
        """Resolve the parsing strategy using the priority chain."""
        # Priority 1: explicit override argument
        if strategy_override is not None:
            return strategy_override

        # Priority 2: parsing_strategy in base_metadata (from .metadata.json)
        from_metadata = _classification_from_metadata(base_metadata)
        if from_metadata is not None:
            return from_metadata

        # Priority 3: CLI default strategy
        if self.default_strategy is not None:
            return PDFClassificationResult(
                strategy=self.default_strategy,
                extract_images=False,
                confidence=1.0,
                override_source="cli",
            )

        # Priority 4: automatic classifier
        if self.enable_classifier:
            from green_gov_rag.etl.parsers.pdf_classifier import PDFComplexityClassifier

            return PDFComplexityClassifier().classify(pdf_path)

        # Final fallback — should not normally be reached
        return PDFClassificationResult(
            strategy=PDFParserStrategy.FAST,
            extract_images=False,
            confidence=0.0,
            override_source="classifier",
        )

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

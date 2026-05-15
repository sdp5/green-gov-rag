"""PDF complexity classifier for selecting optimal parsing strategy.

Analyses PDFs using cheap PyMuPDF heuristics (no ML models) to determine
the best Unstructured.io parsing strategy: fast, hi_res, or hi_res with
image extraction. Designed to run in under 1 second per PDF by sampling
at most 5 representative pages.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from green_gov_rag.types import PDFClassificationResult, PDFParserStrategy

logger = logging.getLogger(__name__)


class PDFComplexityClassifier:
    """Classify PDF complexity to select the optimal parsing strategy.

    Uses PyMuPDF to collect heuristic signals from sampled pages, then
    applies threshold rules to select between fast, hi_res, or hi_res
    with image extraction strategies.

    Thresholds are class-level constants so they can be tuned by overriding
    in tests or subclasses without changing the algorithm.

    Example:
    -------
        >>> classifier = PDFComplexityClassifier()
        >>> result = classifier.classify("legislation.pdf")
        >>> print(result.strategy, result.override_source)
        PDFParserStrategy.FAST classifier

    """

    # Classification thresholds
    IMAGE_AREA_THRESHOLD = 0.25  # Image area fraction of page → vision hi_res
    IMAGE_COUNT_THRESHOLD = 3.0  # Avg images/page (combined with low text) → vision
    TEXT_SCANNED_THRESHOLD = 200  # Avg chars/page below this → likely scanned → hi_res
    TEXT_FAST_THRESHOLD = 500  # Avg chars/page above this helps qualify for fast
    TABLE_LINE_THRESHOLD = 8.0  # Avg vector line drawings/page → table-heavy → hi_res
    FILE_SIZE_THRESHOLD_KB = 150  # KB/page above this → complex content → hi_res

    # Sampling configuration
    MAX_SAMPLE_PAGES = 5  # Max pages to analyse per PDF

    # Column detection
    COLUMN_BIN_SIZE_PX = 50  # Histogram bin width for x0 clustering
    COLUMN_MIN_SEPARATION_PX = 100  # Minimum px gap between column clusters
    COLUMN_MIN_BLOCKS_PER_BIN = 3  # Minimum text blocks to count as a column
    COLUMN_MIN_WORDS_PER_BLOCK = 3  # Minimum words to include a block in analysis
    COLUMN_MIN_PAGES_WITH_MULTICOL = 2  # Pages with multi-column to call it multi-col

    def classify(self, pdf_path: Path | str) -> PDFClassificationResult:
        """Classify a PDF and return the recommended parsing strategy.

        Falls back to FAST with low confidence if the PDF cannot be opened.

        Args:
        ----
            pdf_path: Path to the PDF file.

        Returns:
        -------
            PDFClassificationResult with recommended strategy and signal data.

        """
        pdf_path = Path(pdf_path)
        doc = None
        try:
            doc = fitz.open(str(pdf_path))
            signals = self._collect_signals(doc, pdf_path)
            strategy, extract_images = self._select_strategy(signals)
            confidence = self._compute_confidence(signals, strategy)

            logger.debug(
                "PDF classified: %s → strategy=%s extract_images=%s confidence=%.2f signals=%s",
                pdf_path.name,
                strategy.value,
                extract_images,
                confidence,
                signals,
            )

            return PDFClassificationResult(
                strategy=strategy,
                extract_images=extract_images,
                confidence=confidence,
                signals=signals,
                override_source="classifier",
            )

        except Exception as exc:
            logger.warning(
                "PDF classifier failed for %s (%s); defaulting to FAST strategy.",
                pdf_path,
                exc,
            )
            return PDFClassificationResult(
                strategy=PDFParserStrategy.FAST,
                extract_images=False,
                confidence=0.0,
                signals={},
                override_source="classifier",
            )
        finally:
            if doc is not None:
                doc.close()

    # ------------------------------------------------------------------
    # Signal collection
    # ------------------------------------------------------------------

    def _collect_signals(self, doc: fitz.Document, pdf_path: Path) -> dict[str, float]:
        """Collect heuristic signals from sampled pages."""
        page_count = len(doc)
        sample_indices = self._sample_pages(doc)

        text_chars: list[float] = []
        image_counts: list[float] = []
        image_area_fracs: list[float] = []
        table_line_densities: list[float] = []
        column_counts: list[int] = []

        for idx in sample_indices:
            page = doc[idx]
            page_area = page.rect.width * page.rect.height

            # Text density
            text_chars.append(float(len(page.get_text())))

            # Image signals
            images = page.get_images(full=True)
            image_counts.append(float(len(images)))
            if page_area > 0 and images:
                total_img_area = sum(self._image_area(page, img) for img in images)
                image_area_fracs.append(total_img_area / page_area)
            else:
                image_area_fracs.append(0.0)

            # Table line density
            table_line_densities.append(self._measure_table_density(page))

            # Column count
            column_counts.append(self._detect_columns(page))

        file_size_kb = os.path.getsize(str(pdf_path)) / 1024
        file_size_kb_per_page = file_size_kb / max(page_count, 1)

        pages_with_multicol = sum(1 for c in column_counts if c >= 2)

        return {
            "page_count": float(page_count),
            "sample_page_count": float(len(sample_indices)),
            "avg_text_chars_per_page": _avg(text_chars),
            "avg_image_count_per_page": _avg(image_counts),
            "avg_image_area_fraction": _avg(image_area_fracs),
            "avg_table_line_density": _avg(table_line_densities),
            "max_column_count": float(max(column_counts, default=0)),
            "pages_with_multicol": float(pages_with_multicol),
            "file_size_kb_per_page": file_size_kb_per_page,
        }

    def _image_area(self, page: fitz.Page, img: tuple[Any, ...]) -> float:
        """Estimate the area of an image on the page."""
        try:
            # img[0] is the xref; use get_image_rects to find bounding box
            rects = page.get_image_rects(img[0])
            if rects:
                r = rects[0]
                return float(r.width * r.height)
        except Exception:
            pass
        return 0.0

    def _measure_table_density(self, page: fitz.Page) -> float:
        """Count near-horizontal and near-vertical vector lines as table indicators."""
        drawings = page.get_drawings()
        line_count = 0
        for drawing in drawings:
            for item in drawing.get("items", []):
                if item[0] == "l":  # line item: ('l', p1, p2)
                    p1, p2 = item[1], item[2]
                    dx = abs(p2.x - p1.x)
                    dy = abs(p2.y - p1.y)
                    # Count lines that are predominantly horizontal or vertical
                    if dx > 20 and dy < 5:  # horizontal
                        line_count += 1
                    elif dy > 20 and dx < 5:  # vertical
                        line_count += 1
        return float(line_count)

    def _detect_columns(self, page: fitz.Page) -> int:
        """Estimate the number of text columns via x0 coordinate clustering.

        Returns the number of distinct column clusters found.
        """
        blocks = page.get_text("blocks")
        # Filter: only blocks with enough words (skip headers/footers/short captions)
        x0_values = []
        for block in blocks:
            if len(block) < 5:
                continue
            text = str(block[4]) if len(block) > 4 else ""
            if len(text.split()) < self.COLUMN_MIN_WORDS_PER_BLOCK:
                continue
            x0_values.append(block[0])  # x0 of the block bbox

        if not x0_values:
            return 1

        # Build histogram of x0 values in COLUMN_BIN_SIZE_PX-wide bins
        min_x0 = min(x0_values)
        bins: dict[int, int] = {}
        for x0 in x0_values:
            bin_key = int((x0 - min_x0) / self.COLUMN_BIN_SIZE_PX)
            bins[bin_key] = bins.get(bin_key, 0) + 1

        # Keep bins with enough blocks
        significant_bins = sorted(
            [k for k, v in bins.items() if v >= self.COLUMN_MIN_BLOCKS_PER_BIN]
        )

        if len(significant_bins) < 2:
            return 1

        # Count distinct clusters separated by COLUMN_MIN_SEPARATION_PX
        min_sep_bins = self.COLUMN_MIN_SEPARATION_PX / self.COLUMN_BIN_SIZE_PX
        clusters = 1
        for i in range(1, len(significant_bins)):
            if significant_bins[i] - significant_bins[i - 1] >= min_sep_bins:
                clusters += 1

        return clusters

    def _sample_pages(self, doc: fitz.Document) -> list[int]:
        """Return indices of representative pages to sample."""
        page_count = len(doc)
        if page_count <= self.MAX_SAMPLE_PAGES:
            return list(range(page_count))
        # Evenly spaced sample including first and last pages
        step = (page_count - 1) / (self.MAX_SAMPLE_PAGES - 1)
        return list(
            dict.fromkeys(int(round(i * step)) for i in range(self.MAX_SAMPLE_PAGES))
        )

    # ------------------------------------------------------------------
    # Strategy selection
    # ------------------------------------------------------------------

    def _select_strategy(
        self, signals: dict[str, float]
    ) -> tuple[PDFParserStrategy, bool]:
        """Apply threshold rules to select strategy.

        Returns:
            (strategy, extract_images) tuple.
        """
        avg_image_area = signals.get("avg_image_area_fraction", 0.0)
        avg_image_count = signals.get("avg_image_count_per_page", 0.0)
        avg_text_chars = signals.get("avg_text_chars_per_page", 0.0)
        avg_table_density = signals.get("avg_table_line_density", 0.0)
        pages_with_multicol = signals.get("pages_with_multicol", 0.0)
        file_size_kb_per_page = signals.get("file_size_kb_per_page", 0.0)

        # Rule 1: Vision hi_res — image-dominant content
        if avg_image_area > self.IMAGE_AREA_THRESHOLD or (
            avg_image_count > self.IMAGE_COUNT_THRESHOLD
            and avg_text_chars < self.TEXT_FAST_THRESHOLD
        ):
            return PDFParserStrategy.HI_RES, True

        # Rule 2: Hi_res — complex layout needing accurate parsing
        if (
            avg_text_chars < self.TEXT_SCANNED_THRESHOLD  # likely scanned
            or pages_with_multicol >= self.COLUMN_MIN_PAGES_WITH_MULTICOL
            or avg_table_density > self.TABLE_LINE_THRESHOLD
            or file_size_kb_per_page > self.FILE_SIZE_THRESHOLD_KB
        ):
            return PDFParserStrategy.HI_RES, False

        # Rule 3: Fast — text-heavy, simple layout
        return PDFParserStrategy.FAST, False

    def _compute_confidence(
        self, signals: dict[str, float], strategy: PDFParserStrategy
    ) -> float:
        """Estimate confidence in the classification (0.0–1.0).

        Higher confidence when signals clearly point to one strategy.
        """
        avg_text_chars = signals.get("avg_text_chars_per_page", 0.0)
        avg_image_area = signals.get("avg_image_area_fraction", 0.0)

        if strategy == PDFParserStrategy.FAST:
            # More confident the higher the text density
            return min(1.0, avg_text_chars / 1500)
        if strategy == PDFParserStrategy.HI_RES:
            if avg_image_area > self.IMAGE_AREA_THRESHOLD:
                return min(1.0, avg_image_area / self.IMAGE_AREA_THRESHOLD)
            return 0.8  # hi_res from other signals
        return 0.5


def _avg(values: list[float]) -> float:
    """Return mean of a list, or 0.0 if empty."""
    return sum(values) / len(values) if values else 0.0

"""Tests for PDFComplexityClassifier."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from green_gov_rag.etl.parsers.pdf_classifier import PDFComplexityClassifier, _avg
from green_gov_rag.types import PDFParserStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_page(
    text: str = "word " * 200,
    images: list | None = None,
    drawings: list | None = None,
    blocks: list | None = None,
    width: float = 595.0,
    height: float = 842.0,
) -> MagicMock:
    """Create a mock fitz.Page with controllable signals."""
    page = MagicMock()
    page.rect = MagicMock(width=width, height=height)
    page.get_text.return_value = text
    page.get_images.return_value = images or []
    page.get_drawings.return_value = drawings or []
    page.get_text.side_effect = None  # override if needed

    # Default: get_text returns text regardless of arg
    page.get_text = MagicMock(return_value=text)
    page.get_text("blocks")  # consumed by side-effect; reset
    page.get_text = MagicMock(
        side_effect=lambda *args, **kwargs: text if not args else blocks or []
    )

    return page


def _make_fitz_doc(pages: list[MagicMock], path: Path | None = None) -> MagicMock:
    """Create a mock fitz.Document."""
    doc = MagicMock()
    doc.__len__ = MagicMock(return_value=len(pages))
    doc.__getitem__ = MagicMock(side_effect=lambda i: pages[i])
    doc.close = MagicMock()
    return doc


# ---------------------------------------------------------------------------
# Test _avg helper
# ---------------------------------------------------------------------------


class TestAvgHelper:
    def test_normal(self):
        assert _avg([1.0, 2.0, 3.0]) == pytest.approx(2.0)

    def test_empty(self):
        assert _avg([]) == 0.0


# ---------------------------------------------------------------------------
# Test signal collection
# ---------------------------------------------------------------------------


class TestCollectSignals:
    def test_text_heavy_page_signals(self, tmp_path):
        """High-text page produces high avg_text_chars_per_page."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"")
        big_text = "word " * 300  # 1500 chars
        page = _make_page(text=big_text, blocks=[])
        doc = _make_fitz_doc([page])

        with patch(
            "green_gov_rag.etl.parsers.pdf_classifier.fitz.open", return_value=doc
        ):
            with patch("os.path.getsize", return_value=50 * 1024):
                classifier = PDFComplexityClassifier()
                signals = classifier._collect_signals(doc, pdf)

        assert signals["avg_text_chars_per_page"] == pytest.approx(len(big_text))
        assert signals["page_count"] == 1.0

    def test_image_heavy_page_signals(self, tmp_path):
        """Page with many large images → high avg_image_area_fraction."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"")

        page = _make_page(
            text="short",
            images=[(1, None, None, None, None, None, None, None)],
            blocks=[],
        )
        page.rect = MagicMock(width=595.0, height=842.0)

        # image_rects returns a rect covering 50% of the page
        half_area_rect = MagicMock(width=595.0, height=421.0)
        page.get_image_rects = MagicMock(return_value=[half_area_rect])

        doc = _make_fitz_doc([page])

        with patch(
            "green_gov_rag.etl.parsers.pdf_classifier.fitz.open", return_value=doc
        ):
            with patch("os.path.getsize", return_value=200 * 1024):
                classifier = PDFComplexityClassifier()
                signals = classifier._collect_signals(doc, pdf)

        assert signals["avg_image_count_per_page"] == 1.0
        assert signals["avg_image_area_fraction"] > 0.0

    def test_file_size_per_page(self, tmp_path):
        """File size per page is computed correctly."""
        pdf = tmp_path / "doc.pdf"
        pdf.write_bytes(b"")
        page = _make_page(blocks=[])
        doc = _make_fitz_doc([page, page])  # 2 pages

        with patch(
            "green_gov_rag.etl.parsers.pdf_classifier.fitz.open", return_value=doc
        ):
            with patch("os.path.getsize", return_value=600 * 1024):  # 600 KB
                classifier = PDFComplexityClassifier()
                signals = classifier._collect_signals(doc, pdf)

        assert signals["file_size_kb_per_page"] == pytest.approx(300.0)
        assert signals["page_count"] == 2.0


# ---------------------------------------------------------------------------
# Test strategy selection rules
# ---------------------------------------------------------------------------


class TestSelectStrategy:
    def _classifier(self) -> PDFComplexityClassifier:
        return PDFComplexityClassifier()

    def test_vision_hi_res_from_high_image_area(self):
        """Image area > threshold → hi_res with extract_images=True."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.40,  # > 0.25
            "avg_image_count_per_page": 1.0,
            "avg_text_chars_per_page": 800,
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is True

    def test_vision_hi_res_from_many_images_low_text(self):
        """Many images + sparse text → hi_res with extract_images=True."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.10,
            "avg_image_count_per_page": 5.0,  # > 3
            "avg_text_chars_per_page": 100,  # < 500
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is True

    def test_hi_res_from_scanned_low_text(self):
        """Very low text → scanned PDF → hi_res, no image extraction."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.0,
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 50,  # < 200
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is False

    def test_hi_res_from_multicolumn(self):
        """Multiple multi-col pages → hi_res."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.0,
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 800,
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 2.0,  # >= COLUMN_MIN_PAGES_WITH_MULTICOL
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is False

    def test_hi_res_from_table_density(self):
        """Dense table lines → hi_res."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.0,
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 800,
            "avg_table_line_density": 12.0,  # > 8
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is False

    def test_hi_res_from_large_file_per_page(self):
        """Heavy file per page → hi_res."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.0,
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 800,
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 200.0,  # > 150
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.HI_RES
        assert extract_images is False

    def test_fast_for_simple_text(self):
        """High text density, no images, single-column → fast."""
        c = self._classifier()
        signals = {
            "avg_image_area_fraction": 0.0,
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 1200,
            "avg_table_line_density": 1.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 40.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        assert strategy == PDFParserStrategy.FAST
        assert extract_images is False


# ---------------------------------------------------------------------------
# Test column detection
# ---------------------------------------------------------------------------


class TestColumnDetection:
    def _classifier(self) -> PDFComplexityClassifier:
        return PDFComplexityClassifier()

    def _make_block(self, x0: float, text: str = "word word word word") -> tuple:
        """Create a minimal text block tuple: (x0, y0, x1, y1, text, ...)."""
        return (x0, 0.0, x0 + 200, 20.0, text)

    def test_single_column_uniform_x0(self):
        """All blocks near same x → single column."""
        c = self._classifier()
        page = MagicMock()
        blocks = [self._make_block(72.0) for _ in range(10)]
        page.get_text = MagicMock(
            side_effect=lambda *a, **kw: blocks if a and a[0] == "blocks" else ""
        )
        result = c._detect_columns(page)
        assert result == 1

    def test_two_columns_detected(self):
        """Two distinct x0 clusters → 2 columns."""
        c = self._classifier()
        page = MagicMock()
        # Left column at x=72, right column at x=320 (gap > 100px)
        blocks = [self._make_block(72.0) for _ in range(5)] + [
            self._make_block(320.0) for _ in range(5)
        ]
        page.get_text = MagicMock(
            side_effect=lambda *a, **kw: blocks if a and a[0] == "blocks" else ""
        )
        result = c._detect_columns(page)
        assert result >= 2

    def test_short_blocks_ignored(self):
        """Blocks with fewer than min words are excluded."""
        c = self._classifier()
        page = MagicMock()
        # Short block at x=320 (would be 2nd column if counted)
        blocks = (
            [self._make_block(72.0) for _ in range(5)]
            + [(320.0, 0.0, 520.0, 20.0, "hi")]  # 1 word — excluded
        )
        page.get_text = MagicMock(
            side_effect=lambda *a, **kw: blocks if a and a[0] == "blocks" else ""
        )
        result = c._detect_columns(page)
        assert result == 1


# ---------------------------------------------------------------------------
# Test sampling
# ---------------------------------------------------------------------------


class TestSampling:
    def test_small_pdf_all_pages_sampled(self):
        """PDF with ≤ MAX_SAMPLE_PAGES pages → all sampled."""
        c = PDFComplexityClassifier()
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=4)
        indices = c._sample_pages(doc)
        assert indices == [0, 1, 2, 3]

    def test_large_pdf_capped_at_max(self):
        """PDF with 30 pages → exactly MAX_SAMPLE_PAGES sampled."""
        c = PDFComplexityClassifier()
        doc = MagicMock()
        doc.__len__ = MagicMock(return_value=30)
        indices = c._sample_pages(doc)
        assert len(indices) == c.MAX_SAMPLE_PAGES
        assert 0 in indices
        assert 29 in indices  # first and last always included


# ---------------------------------------------------------------------------
# Test graceful fallback on error
# ---------------------------------------------------------------------------


class TestGracefulFallback:
    def test_fallback_on_fitz_error(self, tmp_path):
        """If fitz.open raises, classifier returns FAST with confidence=0."""
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"not a pdf")

        with patch(
            "green_gov_rag.etl.parsers.pdf_classifier.fitz.open",
            side_effect=RuntimeError("corrupt"),
        ):
            result = PDFComplexityClassifier().classify(pdf)

        assert result.strategy == PDFParserStrategy.FAST
        assert result.confidence == 0.0
        assert result.override_source == "classifier"


# ---------------------------------------------------------------------------
# Test threshold tunability
# ---------------------------------------------------------------------------


class TestThresholdTunability:
    def test_custom_image_area_threshold(self):
        """Class constants can be overridden for threshold tuning."""
        c = PDFComplexityClassifier()
        c.IMAGE_AREA_THRESHOLD = 0.50  # raise threshold
        signals = {
            "avg_image_area_fraction": 0.40,  # would normally trigger vision
            "avg_image_count_per_page": 0.0,
            "avg_text_chars_per_page": 800,
            "avg_table_line_density": 0.0,
            "pages_with_multicol": 0.0,
            "file_size_kb_per_page": 50.0,
        }
        strategy, extract_images = c._select_strategy(signals)
        # With raised threshold, 0.40 should NOT trigger vision hi_res
        assert extract_images is False

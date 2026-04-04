"""Tests for HierarchicalPDFParser strategy resolution."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from green_gov_rag.etl.parsers.layout_parser import (
    HierarchicalPDFParser,
    _classification_from_metadata,
)
from green_gov_rag.types import PDFClassificationResult, PDFParserStrategy

# ---------------------------------------------------------------------------
# Test _classification_from_metadata helper
# ---------------------------------------------------------------------------


class TestClassificationFromMetadata:
    def test_fast_value(self):
        result = _classification_from_metadata({"parsing_strategy": "fast"})
        assert result is not None
        assert result.strategy == PDFParserStrategy.FAST
        assert result.extract_images is False
        assert result.override_source == "config"

    def test_hi_res_value(self):
        result = _classification_from_metadata({"parsing_strategy": "hi_res"})
        assert result is not None
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.extract_images is False

    def test_hi_res_vision_value(self):
        result = _classification_from_metadata({"parsing_strategy": "hi_res_vision"})
        assert result is not None
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.extract_images is True

    def test_auto_returns_none(self):
        result = _classification_from_metadata({"parsing_strategy": "auto"})
        assert result is None

    def test_absent_returns_none(self):
        result = _classification_from_metadata({})
        assert result is None

    def test_unknown_value_returns_none(self):
        result = _classification_from_metadata({"parsing_strategy": "unknown_mode"})
        assert result is None

    def test_case_insensitive(self):
        result = _classification_from_metadata({"parsing_strategy": "FAST"})
        assert result is not None
        assert result.strategy == PDFParserStrategy.FAST


# ---------------------------------------------------------------------------
# Test strategy resolution priority
# ---------------------------------------------------------------------------


class TestStrategyResolution:
    """Tests for HierarchicalPDFParser._resolve_strategy priority chain."""

    def _parser(self, **kwargs) -> HierarchicalPDFParser:
        return HierarchicalPDFParser(**kwargs)

    def test_explicit_override_takes_priority_over_metadata(self, tmp_path):
        """strategy_override argument beats parsing_strategy in base_metadata."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        override = PDFClassificationResult(
            strategy=PDFParserStrategy.HI_RES,
            extract_images=True,
            override_source="config",
        )
        parser = self._parser(
            default_strategy=PDFParserStrategy.FAST, enable_classifier=False
        )

        result = parser._resolve_strategy(
            pdf,
            strategy_override=override,
            base_metadata={"parsing_strategy": "fast"},
        )
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.extract_images is True
        assert result.override_source == "config"

    def test_metadata_overrides_cli_default(self, tmp_path):
        """parsing_strategy in base_metadata takes priority over CLI default."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        parser = self._parser(
            default_strategy=PDFParserStrategy.HI_RES, enable_classifier=False
        )

        result = parser._resolve_strategy(
            pdf,
            strategy_override=None,
            base_metadata={"parsing_strategy": "fast"},
        )
        assert result.strategy == PDFParserStrategy.FAST
        assert result.override_source == "config"

    def test_cli_default_used_when_no_override_no_metadata(self, tmp_path):
        """When no override or metadata, CLI default_strategy is applied."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        parser = self._parser(
            default_strategy=PDFParserStrategy.HI_RES, enable_classifier=False
        )

        result = parser._resolve_strategy(pdf, strategy_override=None, base_metadata={})
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.override_source == "cli"

    def test_classifier_called_when_no_default_no_override(self, tmp_path):
        """Classifier is invoked when both default_strategy and override are None."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        parser = self._parser(default_strategy=None, enable_classifier=True)

        classifier_result = PDFClassificationResult(
            strategy=PDFParserStrategy.FAST,
            extract_images=False,
            confidence=0.9,
            override_source="classifier",
        )

        with patch(
            "green_gov_rag.etl.parsers.pdf_classifier.PDFComplexityClassifier.classify",
            return_value=classifier_result,
        ) as mock_classify:
            result = parser._resolve_strategy(
                pdf, strategy_override=None, base_metadata={}
            )

        mock_classify.assert_called_once_with(pdf)
        assert result.strategy == PDFParserStrategy.FAST
        assert result.override_source == "classifier"

    def test_fallback_fast_when_classifier_disabled_and_no_default(self, tmp_path):
        """If classifier disabled and no default, safe fallback to FAST."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        parser = self._parser(default_strategy=None, enable_classifier=False)

        result = parser._resolve_strategy(pdf, strategy_override=None, base_metadata={})
        assert result.strategy == PDFParserStrategy.FAST


# ---------------------------------------------------------------------------
# Test backward compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibility:
    def test_no_args_constructor(self):
        """HierarchicalPDFParser() with no args still works."""
        parser = HierarchicalPDFParser()
        assert parser.default_strategy is None
        assert parser.enable_classifier is True

    def test_parse_with_structure_no_strategy_override_arg(self, tmp_path):
        """parse_with_structure can be called with just pdf_path and base_metadata."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        parser = HierarchicalPDFParser(
            default_strategy=PDFParserStrategy.FAST, enable_classifier=False
        )

        fake_chunks = [{"content": "hello", "metadata": {}}]

        with patch(
            "green_gov_rag.etl.parsers.unstructured_parser.UnstructuredPDFParser"
        ) as MockParser:
            instance = MockParser.return_value
            instance.parse_with_structure.return_value = fake_chunks
            result = parser.parse_with_structure(pdf, base_metadata={})

        assert result == fake_chunks


# ---------------------------------------------------------------------------
# Test ADI raises NotImplementedError
# ---------------------------------------------------------------------------


class TestADIStrategy:
    def test_adi_raises(self, tmp_path):
        """ADI strategy raises NotImplementedError."""
        pdf = tmp_path / "doc.pdf"
        pdf.touch()
        adi_result = PDFClassificationResult(
            strategy=PDFParserStrategy.ADI,
            override_source="config",
        )
        parser = HierarchicalPDFParser(enable_classifier=False)

        with pytest.raises(NotImplementedError, match="Azure Document Intelligence"):
            parser.parse_with_structure(pdf, strategy_override=adi_result)

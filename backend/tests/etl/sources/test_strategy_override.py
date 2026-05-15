"""Tests for DocumentSource.get_parsing_strategy()."""

from __future__ import annotations

from typing import Any

from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult
from green_gov_rag.types import PDFParserStrategy

# ---------------------------------------------------------------------------
# Concrete stub for testing
# ---------------------------------------------------------------------------


class StubSource(DocumentSource):
    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        return []

    def get_metadata(self) -> dict[str, Any]:
        return {"title": self.config.get("title", "")}

    def get_document_id(self, url: str) -> str:
        return "stub_id"

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        return f"{base_dir}/stub.pdf"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetParsingStrategy:
    def _source(self, parsing_strategy=None, **extra) -> StubSource:
        config: dict[str, Any] = {"title": "Test", "jurisdiction": "federal", **extra}
        if parsing_strategy is not None:
            config["parsing_strategy"] = parsing_strategy
        return StubSource(config)

    def test_absent_returns_none(self):
        """No parsing_strategy in config → None (auto-classify)."""
        assert self._source().get_parsing_strategy() is None

    def test_auto_returns_none(self):
        """parsing_strategy: auto → None."""
        assert self._source("auto").get_parsing_strategy() is None

    def test_unknown_value_returns_none(self):
        """Unknown parsing_strategy value → None (safe fallback)."""
        assert self._source("turbo_mode").get_parsing_strategy() is None

    def test_fast(self):
        result = self._source("fast").get_parsing_strategy()
        assert result is not None
        assert result.strategy == PDFParserStrategy.FAST
        assert result.extract_images is False
        assert result.override_source == "config"
        assert result.confidence == 1.0

    def test_hi_res(self):
        result = self._source("hi_res").get_parsing_strategy()
        assert result is not None
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.extract_images is False

    def test_hi_res_vision(self):
        result = self._source("hi_res_vision").get_parsing_strategy()
        assert result is not None
        assert result.strategy == PDFParserStrategy.HI_RES
        assert result.extract_images is True

    def test_case_insensitive(self):
        result = self._source("HI_RES_VISION").get_parsing_strategy()
        assert result is not None
        assert result.extract_images is True

    def test_parsing_strategy_in_optional_fields(self):
        """parsing_strategy should appear in get_optional_fields()."""
        source = self._source()
        assert "parsing_strategy" in source.get_optional_fields()


class TestExtractStructuredMetadata:
    def test_parsing_strategy_propagated(self):
        """parsing_strategy in config is included in _extract_structured_metadata."""
        source = StubSource(
            {
                "title": "Test",
                "jurisdiction": "federal",
                "parsing_strategy": "hi_res_vision",
            }
        )
        metadata = source._extract_structured_metadata()
        assert metadata.get("parsing_strategy") == "hi_res_vision"

    def test_absent_parsing_strategy_not_in_metadata(self):
        """If parsing_strategy absent from config, not injected into metadata."""
        source = StubSource({"title": "Test", "jurisdiction": "federal"})
        metadata = source._extract_structured_metadata()
        assert "parsing_strategy" not in metadata

"""Tests for base document source interface."""

from typing import Any

from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_success(self):
        """Test successful validation result."""
        result = ValidationResult.success()
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_failure(self):
        """Test failed validation result."""
        errors = ["Error 1", "Error 2"]
        warnings = ["Warning 1"]
        result = ValidationResult.failure(errors, warnings)
        assert result.is_valid is False
        assert result.errors == errors
        assert result.warnings == warnings

    def test_failure_without_warnings(self):
        """Test failed validation without warnings."""
        errors = ["Error 1"]
        result = ValidationResult.failure(errors)
        assert result.is_valid is False
        assert result.errors == errors
        assert result.warnings == []


class ConcreteDocumentSource(DocumentSource):
    """Concrete implementation for testing."""

    def validate(self) -> ValidationResult:
        return ValidationResult.success()

    def get_download_urls(self) -> list[str]:
        return self.config.get("download_urls", [])

    def get_metadata(self) -> dict:
        return {"title": self.config.get("title")}

    def get_document_id(self, url: str) -> str:
        return self._generate_document_id(url)

    def get_destination_path(self, url: str, base_dir: str = "data/raw") -> str:
        return self._generate_destination_path(url, base_dir)


class TestDocumentSource:
    """Tests for DocumentSource abstract base class."""

    def test_initialization(self):
        """Test source initialization with config."""
        config = {"title": "Test Document"}
        source = ConcreteDocumentSource(config)
        assert source.config == config

    def test_get_source_type(self):
        """Test source type extraction from class name."""
        config: dict[str, Any] = {}
        source = ConcreteDocumentSource(config)
        assert source.get_source_type() == "concretedocument"

    def test_get_required_fields(self):
        """Test default required fields."""
        config: dict[str, Any] = {}
        source = ConcreteDocumentSource(config)
        required = source.get_required_fields()
        assert "title" in required
        assert "jurisdiction" in required
        assert "category" in required
        assert "topic" in required

    def test_get_optional_fields(self):
        """Test default optional fields."""
        config: dict[str, Any] = {}
        source = ConcreteDocumentSource(config)
        optional = source.get_optional_fields()
        assert "source_url" in optional
        assert "download_urls" in optional
        assert "esg_metadata" in optional
        assert "spatial_metadata" in optional

    def test_validate_required_fields_success(self):
        """Test validation passes with all required fields."""
        config = {
            "title": "Test",
            "jurisdiction": "federal",
            "category": "legislation",
            "topic": "environment",
        }
        source = ConcreteDocumentSource(config)
        errors = source._validate_required_fields()
        assert errors == []

    def test_validate_required_fields_missing(self):
        """Test validation fails with missing required fields."""
        config = {"title": "Test"}
        source = ConcreteDocumentSource(config)
        errors = source._validate_required_fields()
        assert len(errors) > 0
        assert any("jurisdiction" in error for error in errors)
        assert any("category" in error for error in errors)

    def test_validate_urls_success(self):
        """Test URL validation with valid URLs."""
        config = {
            "source_url": "https://example.com",
            "download_urls": [
                "https://example.com/doc1.pdf",
                "https://example.com/doc2.pdf",
            ],
        }
        source = ConcreteDocumentSource(config)
        errors = source._validate_urls()
        assert errors == []

    def test_validate_urls_invalid_source(self):
        """Test URL validation with invalid source URL."""
        config = {"source_url": "not-a-url"}
        source = ConcreteDocumentSource(config)
        errors = source._validate_urls()
        assert len(errors) > 0
        assert any("source_url" in error for error in errors)

    def test_validate_urls_invalid_download(self):
        """Test URL validation with invalid download URLs."""
        config = {"download_urls": ["https://valid.com/doc.pdf", "invalid-url"]}
        source = ConcreteDocumentSource(config)
        errors = source._validate_urls()
        assert len(errors) > 0
        assert any("invalid-url" in error for error in errors)

    def test_get_download_urls(self):
        """Test getting download URLs."""
        config = {"download_urls": ["https://example.com/doc.pdf"]}
        source = ConcreteDocumentSource(config)
        urls = source.get_download_urls()
        assert urls == ["https://example.com/doc.pdf"]

    def test_get_metadata(self):
        """Test getting metadata."""
        config = {"title": "Test Document", "jurisdiction": "federal"}
        source = ConcreteDocumentSource(config)
        metadata = source.get_metadata()
        assert metadata["title"] == "Test Document"

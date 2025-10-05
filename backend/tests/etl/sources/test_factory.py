"""Tests for document source factory."""


from green_gov_rag.etl.sources.emissions import EmissionsReportingSource
from green_gov_rag.etl.sources.factory import (
    DocumentSourceFactory,
    GenericDocumentSource,
)
from green_gov_rag.etl.sources.federal import FederalLegislationSource
from green_gov_rag.etl.sources.local_government import LocalGovernmentSource
from green_gov_rag.etl.sources.state import StateLegislationSource


class TestDocumentSourceFactory:
    """Tests for DocumentSourceFactory."""

    def test_initialization(self):
        """Test factory initialization."""
        factory = DocumentSourceFactory()
        assert factory.registry is not None

    def test_infer_federal_legislation(self):
        """Test inference of federal legislation source."""
        factory = DocumentSourceFactory()
        config = {
            "jurisdiction": "federal",
            "category": "legislation",
            "topic": "biodiversity",
        }
        source_type = factory._infer_source_type(config)
        assert source_type == "federal_legislation"

    def test_infer_emissions_reporting(self):
        """Test inference of emissions reporting source."""
        factory = DocumentSourceFactory()
        config = {
            "jurisdiction": "federal",
            "category": "environment",
            "topic": "emissions_reporting",
            "esg_metadata": {"frameworks": ["NGER"]},
        }
        source_type = factory._infer_source_type(config)
        assert source_type == "emissions_reporting"

    def test_infer_state_legislation(self):
        """Test inference of state legislation source."""
        factory = DocumentSourceFactory()
        config = {
            "jurisdiction": "state",
            "category": "legislation",
            "topic": "planning",
        }
        source_type = factory._infer_source_type(config)
        assert source_type == "state_legislation"

    def test_infer_local_government(self):
        """Test inference of local government source."""
        factory = DocumentSourceFactory()
        config = {
            "jurisdiction": "local",
            "category": "development_plan",
            "topic": "zoning",
        }
        source_type = factory._infer_source_type(config)
        assert source_type == "local_government"

    def test_create_federal_source(self):
        """Test creating federal legislation source."""
        factory = DocumentSourceFactory()
        config = {
            "title": "Test Act",
            "jurisdiction": "federal",
            "category": "legislation",
            "topic": "environment",
            "region": "Australia",
        }
        source = factory.create_source(config)
        assert isinstance(source, FederalLegislationSource)

    def test_create_emissions_source(self):
        """Test creating emissions reporting source."""
        factory = DocumentSourceFactory()
        config = {
            "title": "NGER Guidelines",
            "jurisdiction": "federal",
            "category": "environment",
            "topic": "emissions_reporting",
            "esg_metadata": {"frameworks": ["NGER"]},
        }
        source = factory.create_source(config)
        assert isinstance(source, EmissionsReportingSource)

    def test_create_state_source(self):
        """Test creating state legislation source."""
        factory = DocumentSourceFactory()
        config = {
            "title": "NSW Planning Act",
            "jurisdiction": "state",
            "category": "legislation",
            "topic": "planning",
            "region": "New South Wales",
        }
        source = factory.create_source(config)
        assert isinstance(source, StateLegislationSource)

    def test_create_local_source(self):
        """Test creating local government source."""
        factory = DocumentSourceFactory()
        config = {
            "title": "City Guidelines",
            "jurisdiction": "local",
            "category": "development_plan",
            "topic": "zoning",
            "region": "City of Adelaide",
            "spatial_metadata": {"spatial_scope": "local", "state": "SA"},
        }
        source = factory.create_source(config)
        assert isinstance(source, LocalGovernmentSource)

    def test_create_sources_from_list(self):
        """Test creating multiple sources from list."""
        factory = DocumentSourceFactory()
        configs = [
            {
                "title": "Federal Act",
                "jurisdiction": "federal",
                "category": "legislation",
                "topic": "environment",
                "region": "Australia",
            },
            {
                "title": "State Act",
                "jurisdiction": "state",
                "category": "legislation",
                "topic": "planning",
                "region": "NSW",
            },
        ]
        sources = factory.create_sources_from_list(configs)
        assert len(sources) == 2
        assert isinstance(sources[0], FederalLegislationSource)
        assert isinstance(sources[1], StateLegislationSource)

    def test_generic_fallback(self):
        """Test fallback to generic source for unrecognized types."""
        factory = DocumentSourceFactory()
        config = {
            "title": "Unknown Document",
            "jurisdiction": "unknown",
            "category": "misc",
            "topic": "other",
        }
        source = factory.create_source(config)
        assert isinstance(source, GenericDocumentSource)


class TestGenericDocumentSource:
    """Tests for GenericDocumentSource."""

    def test_validate(self):
        """Test validation of generic source."""
        config = {
            "title": "Test",
            "jurisdiction": "unknown",
            "category": "misc",
            "topic": "other",
        }
        source = GenericDocumentSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_get_download_urls(self):
        """Test getting download URLs."""
        config = {"download_urls": ["https://example.com/doc.pdf"]}
        source = GenericDocumentSource(config)
        urls = source.get_download_urls()
        assert urls == ["https://example.com/doc.pdf"]

    def test_get_metadata(self):
        """Test getting metadata returns full config."""
        config = {"title": "Test", "custom_field": "value"}
        source = GenericDocumentSource(config)
        metadata = source.get_metadata()
        assert metadata == config

    def test_get_source_type(self):
        """Test source type is generic."""
        source = GenericDocumentSource({})
        assert source.get_source_type() == "generic"

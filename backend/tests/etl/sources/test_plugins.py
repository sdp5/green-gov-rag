"""Tests for document source plugins."""


from green_gov_rag.etl.sources.emissions import EmissionsReportingSource
from green_gov_rag.etl.sources.federal import FederalLegislationSource
from green_gov_rag.etl.sources.local_government import LocalGovernmentSource
from green_gov_rag.etl.sources.state import StateLegislationSource


class TestFederalLegislationSource:
    """Tests for FederalLegislationSource."""

    def test_validate_success(self):
        """Test validation with valid federal config."""
        config = {
            "title": "EPBC Act",
            "jurisdiction": "federal",
            "category": "legislation",
            "topic": "biodiversity",
            "region": "Australia",
            "source_url": "https://legislation.gov.au/test",
        }
        source = FederalLegislationSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_validate_wrong_jurisdiction(self):
        """Test validation fails with wrong jurisdiction."""
        config = {
            "title": "Test",
            "jurisdiction": "state",
            "category": "legislation",
            "topic": "test",
            "region": "Australia",
        }
        source = FederalLegislationSource(config)
        result = source.validate()
        assert result.is_valid is False
        assert any("jurisdiction" in error for error in result.errors)

    def test_get_source_type(self):
        """Test source type."""
        source = FederalLegislationSource({})
        assert source.get_source_type() == "federal_legislation"


class TestEmissionsReportingSource:
    """Tests for EmissionsReportingSource."""

    def test_validate_with_esg_metadata(self):
        """Test validation with ESG metadata."""
        config = {
            "title": "NGER Guidelines",
            "jurisdiction": "federal",
            "category": "environment",
            "topic": "emissions_reporting",
            "esg_metadata": {
                "frameworks": ["NGER"],
                "emission_scopes": ["scope_1"],
                "greenhouse_gases": ["CO2", "CH4"],
            },
        }
        source = EmissionsReportingSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_validate_missing_esg_metadata(self):
        """Test validation warns when ESG metadata missing."""
        config = {
            "title": "Test",
            "jurisdiction": "federal",
            "category": "environment",
            "topic": "emissions_reporting",
        }
        source = EmissionsReportingSource(config)
        result = source.validate()
        assert len(result.warnings) > 0

    def test_get_emission_scopes(self):
        """Test getting emission scopes."""
        config = {
            "esg_metadata": {
                "emission_scopes": ["scope_1", "scope_2"],
            }
        }
        source = EmissionsReportingSource(config)
        scopes = source.get_emission_scopes()
        assert scopes == ["scope_1", "scope_2"]

    def test_get_scope_3_categories(self):
        """Test getting Scope 3 categories."""
        config = {
            "esg_metadata": {
                "scope_3_categories": ["purchased_goods_services", "business_travel"],
            }
        }
        source = EmissionsReportingSource(config)
        categories = source.get_scope_3_categories()
        assert "purchased_goods_services" in categories

    def test_is_nger_reportable(self):
        """Test NGER reportable check."""
        config = {"esg_metadata": {"reportable_under_nger": True}}
        source = EmissionsReportingSource(config)
        assert source.is_nger_reportable() is True


class TestStateLegislationSource:
    """Tests for StateLegislationSource."""

    def test_validate_success(self):
        """Test validation with valid state config."""
        config = {
            "title": "NSW EPA Act",
            "jurisdiction": "state",
            "category": "legislation",
            "topic": "environment",
            "region": "New South Wales",
            "spatial_metadata": {"spatial_scope": "state", "state": "NSW"},
        }
        source = StateLegislationSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_validate_invalid_state(self):
        """Test validation fails with invalid state code."""
        config = {
            "title": "Test",
            "jurisdiction": "state",
            "category": "legislation",
            "topic": "test",
            "region": "Test",
            "spatial_metadata": {"spatial_scope": "state", "state": "INVALID"},
        }
        source = StateLegislationSource(config)
        result = source.validate()
        assert result.is_valid is False

    def test_get_state(self):
        """Test getting state code."""
        config = {"spatial_metadata": {"state": "NSW"}}
        source = StateLegislationSource(config)
        assert source.get_state() == "NSW"


class TestLocalGovernmentSource:
    """Tests for LocalGovernmentSource."""

    def test_validate_success(self):
        """Test validation with valid local config."""
        config = {
            "title": "City Guidelines",
            "jurisdiction": "local",
            "category": "development_plan",
            "topic": "zoning",
            "region": "City of Adelaide",
            "spatial_metadata": {
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": [40070],
                "lga_names": ["City of Adelaide"],
                "applies_to_all_lgas": False,
            },
        }
        source = LocalGovernmentSource(config)
        result = source.validate()
        assert result.is_valid is True

    def test_validate_missing_spatial_metadata(self):
        """Test validation fails without spatial metadata."""
        config = {
            "title": "Test",
            "jurisdiction": "local",
            "category": "plan",
            "topic": "test",
            "region": "Test",
        }
        source = LocalGovernmentSource(config)
        result = source.validate()
        assert result.is_valid is False

    def test_get_lga_codes(self):
        """Test getting LGA codes."""
        config = {"spatial_metadata": {"lga_codes": [40070, 40280]}}
        source = LocalGovernmentSource(config)
        codes = source.get_lga_codes()
        assert codes == [40070, 40280]

    def test_get_lga_names(self):
        """Test getting LGA names."""
        config = {"spatial_metadata": {"lga_names": ["City of Adelaide"]}}
        source = LocalGovernmentSource(config)
        names = source.get_lga_names()
        assert "City of Adelaide" in names

    def test_applies_to_point(self):
        """Test checking if applies to point."""
        config = {"spatial_metadata": {"applies_to_point": True}}
        source = LocalGovernmentSource(config)
        assert source.applies_to_point() is True

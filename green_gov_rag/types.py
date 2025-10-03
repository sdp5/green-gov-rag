"""Type definitions and Enums for GreenGovRAG.

This module centralizes all type definitions, enums, and constants used throughout
the application, replacing hardcoded strings and static dictionaries.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

# ============================================================================
# Australian Geographic Types
# ============================================================================


class AustralianState(str, Enum):
    """Australian states and territories."""

    NSW = "NSW"  # New South Wales
    VIC = "VIC"  # Victoria
    QLD = "QLD"  # Queensland
    SA = "SA"  # South Australia
    WA = "WA"  # Western Australia
    TAS = "TAS"  # Tasmania
    NT = "NT"  # Northern Territory
    ACT = "ACT"  # Australian Capital Territory

    @classmethod
    def from_name(cls, name: str) -> "AustralianState":
        """Get state from full name or abbreviation.

        Args:
        ----
            name: State name (case-insensitive)

        Returns:
        -------
            AustralianState enum value

        Raises:
        ------
            ValueError: If name doesn't match any state

        """
        name_lower = name.lower().strip()

        # Mapping of various names to state codes
        name_mappings = {
            # Full names
            "new south wales": cls.NSW,
            "victoria": cls.VIC,
            "queensland": cls.QLD,
            "south australia": cls.SA,
            "western australia": cls.WA,
            "tasmania": cls.TAS,
            "northern territory": cls.NT,
            "australian capital territory": cls.ACT,
            # Abbreviations
            "nsw": cls.NSW,
            "vic": cls.VIC,
            "qld": cls.QLD,
            "sa": cls.SA,
            "wa": cls.WA,
            "tas": cls.TAS,
            "nt": cls.NT,
            "act": cls.ACT,
            # State codes (numeric from ABS)
            "1": cls.NSW,
            "2": cls.VIC,
            "3": cls.QLD,
            "4": cls.SA,
            "5": cls.WA,
            "6": cls.TAS,
            "7": cls.NT,
            "8": cls.ACT,
        }

        if name_lower in name_mappings:
            return name_mappings[name_lower]

        msg = f"Unknown state name: {name}"
        raise ValueError(msg)

    @property
    def full_name(self) -> str:
        """Get full state name."""
        full_names = {
            self.NSW: "New South Wales",
            self.VIC: "Victoria",
            self.QLD: "Queensland",
            self.SA: "South Australia",
            self.WA: "Western Australia",
            self.TAS: "Tasmania",
            self.NT: "Northern Territory",
            self.ACT: "Australian Capital Territory",
        }
        return full_names[self]


class LGAInfo(NamedTuple):
    """Local Government Area information."""

    name: str  # Official LGA name
    code: str  # ABS LGA code
    state: AustralianState  # State/territory


# Major LGAs (can be extended)
class KnownLGA:
    """Known Local Government Areas with codes."""

    # South Australia - Adelaide Metro
    ADELAIDE = LGAInfo("City of Adelaide", "40070", AustralianState.SA)
    PORT_ADELAIDE_ENFIELD = LGAInfo(
        "Port Adelaide Enfield",
        "40280",
        AustralianState.SA,
    )
    NORWOOD_PAYNEHAM_ST_PETERS = LGAInfo(
        "Norwood Payneham and St Peters",
        "40340",
        AustralianState.SA,
    )
    UNLEY = LGAInfo("Unley", "40370", AustralianState.SA)
    BURNSIDE = LGAInfo("Burnside", "40070", AustralianState.SA)
    WEST_TORRENS = LGAInfo("West Torrens", "40430", AustralianState.SA)
    PROSPECT = LGAInfo("Prospect", "40290", AustralianState.SA)

    # New South Wales
    SYDNEY = LGAInfo("City of Sydney", "10050", AustralianState.NSW)
    PARRAMATTA = LGAInfo("Parramatta", "12260", AustralianState.NSW)

    # Victoria
    MELBOURNE = LGAInfo("Melbourne", "20260", AustralianState.VIC)

    @classmethod
    def get_all(cls) -> dict[str, LGAInfo]:
        """Get all known LGAs as a dictionary.

        Returns
        -------
            Dict mapping lowercase LGA names (with variants) to LGAInfo

        """
        lgas = {}

        # Adelaide
        lgas["adelaide"] = cls.ADELAIDE
        lgas["city of adelaide"] = cls.ADELAIDE

        # Port Adelaide Enfield
        lgas["port adelaide"] = cls.PORT_ADELAIDE_ENFIELD
        lgas["port adelaide enfield"] = cls.PORT_ADELAIDE_ENFIELD

        # Norwood Payneham St Peters
        lgas["norwood"] = cls.NORWOOD_PAYNEHAM_ST_PETERS
        lgas["norwood payneham"] = cls.NORWOOD_PAYNEHAM_ST_PETERS
        lgas["norwood payneham st peters"] = cls.NORWOOD_PAYNEHAM_ST_PETERS

        # Unley
        lgas["unley"] = cls.UNLEY
        lgas["city of unley"] = cls.UNLEY

        # Burnside
        lgas["burnside"] = cls.BURNSIDE
        lgas["city of burnside"] = cls.BURNSIDE

        # West Torrens
        lgas["west torrens"] = cls.WEST_TORRENS
        lgas["city of west torrens"] = cls.WEST_TORRENS

        # Prospect
        lgas["prospect"] = cls.PROSPECT
        lgas["city of prospect"] = cls.PROSPECT

        # Sydney
        lgas["sydney"] = cls.SYDNEY
        lgas["city of sydney"] = cls.SYDNEY

        # Parramatta
        lgas["parramatta"] = cls.PARRAMATTA

        # Melbourne
        lgas["melbourne"] = cls.MELBOURNE
        lgas["city of melbourne"] = cls.MELBOURNE

        return lgas


# ============================================================================
# ESG / Emissions Types
# ============================================================================


class EmissionScope(str, Enum):
    """GHG Protocol emission scopes."""

    SCOPE_1 = "scope_1"  # Direct emissions from owned/controlled sources
    SCOPE_2 = "scope_2"  # Indirect emissions from purchased energy
    SCOPE_3 = "scope_3"  # Indirect emissions in value chain


class Scope3Category(str, Enum):
    """GHG Protocol Scope 3 emission categories (all 15 ISSB categories)."""

    # Upstream Categories (1-8)
    PURCHASED_GOODS_SERVICES = "purchased_goods_services"  # Category 1
    CAPITAL_GOODS = "capital_goods"  # Category 2
    FUEL_ENERGY_ACTIVITIES = "fuel_energy_activities"  # Category 3
    UPSTREAM_TRANSPORT = "upstream_transport"  # Category 4
    WASTE_GENERATED = "waste_generated"  # Category 5
    BUSINESS_TRAVEL = "business_travel"  # Category 6
    EMPLOYEE_COMMUTING = "employee_commuting"  # Category 7
    UPSTREAM_LEASED_ASSETS = "upstream_leased_assets"  # Category 8

    # Downstream Categories (9-15)
    DOWNSTREAM_TRANSPORT = "downstream_transport"  # Category 9
    PROCESSING_SOLD_PRODUCTS = "processing_sold_products"  # Category 10
    USE_OF_SOLD_PRODUCTS = "use_of_sold_products"  # Category 11
    END_OF_LIFE_TREATMENT = "end_of_life_treatment"  # Category 12
    DOWNSTREAM_LEASED_ASSETS = "downstream_leased_assets"  # Category 13
    FRANCHISES = "franchises"  # Category 14
    INVESTMENTS = "investments"  # Category 15

    @classmethod
    def upstream_categories(cls) -> list["Scope3Category"]:
        """Get all upstream Scope 3 categories (1-8)."""
        return [
            cls.PURCHASED_GOODS_SERVICES,
            cls.CAPITAL_GOODS,
            cls.FUEL_ENERGY_ACTIVITIES,
            cls.UPSTREAM_TRANSPORT,
            cls.WASTE_GENERATED,
            cls.BUSINESS_TRAVEL,
            cls.EMPLOYEE_COMMUTING,
            cls.UPSTREAM_LEASED_ASSETS,
        ]

    @classmethod
    def downstream_categories(cls) -> list["Scope3Category"]:
        """Get all downstream Scope 3 categories (9-15)."""
        return [
            cls.DOWNSTREAM_TRANSPORT,
            cls.PROCESSING_SOLD_PRODUCTS,
            cls.USE_OF_SOLD_PRODUCTS,
            cls.END_OF_LIFE_TREATMENT,
            cls.DOWNSTREAM_LEASED_ASSETS,
            cls.FRANCHISES,
            cls.INVESTMENTS,
        ]


class GreenhouseGas(str, Enum):
    """NGER-compliant greenhouse gases."""

    CO2 = "CO2"  # Carbon Dioxide
    CH4 = "CH4"  # Methane
    N2O = "N2O"  # Nitrous Oxide
    SF6 = "SF6"  # Sulfur Hexafluoride
    HFCS = "HFCs"  # Hydrofluorocarbons
    PFCS = "PFCs"  # Perfluorocarbons
    NF3 = "NF3"  # Nitrogen Trifluoride


class ESGFramework(str, Enum):
    """ESG reporting frameworks and standards."""

    NGER = "NGER"  # National Greenhouse and Energy Reporting
    ISSB = "ISSB"  # International Sustainability Standards Board
    GHG_PROTOCOL = "GHG_Protocol"  # GHG Protocol Corporate Standard
    GRI = "GRI"  # Global Reporting Initiative
    TCFD = "TCFD"  # Task Force on Climate-related Financial Disclosures
    CDP = "CDP"  # Carbon Disclosure Project
    SAFEGUARD_MECHANISM = "Safeguard_Mechanism"  # Australian Safeguard Mechanism


class ConsolidationMethod(str, Enum):
    """Emissions accounting consolidation approaches."""

    OPERATIONAL_CONTROL = "operational_control"  # Operational control approach
    EQUITY_SHARE = "equity_share"  # Equity share approach
    FINANCIAL_CONTROL = "financial_control"  # Financial control approach


class MethodologyType(str, Enum):
    """Types of emissions methodology."""

    CALCULATION = "calculation"  # Calculation methodology
    REPORTING = "reporting"  # Reporting methodology
    VERIFICATION = "verification"  # Verification methodology
    MEASUREMENT = "measurement"  # Direct measurement


class ActivityType(str, Enum):
    """Emissions activity types."""

    FUEL_COMBUSTION = "fuel_combustion"
    ELECTRICITY_CONSUMPTION = "electricity_consumption"
    FUGITIVE_EMISSIONS = "fugitive_emissions"
    REFRIGERANT_USE = "refrigerant_use"
    TRANSPORT = "transport"
    WASTE = "waste"
    SUPPLY_CHAIN = "supply_chain"
    INDUSTRIAL_PROCESSES = "industrial_processes"


class FacilityType(str, Enum):
    """Facility or organization types."""

    COAL_MINE = "coal_mine"
    POWER_STATION = "power_station"
    MANUFACTURING = "manufacturing"
    COMMERCIAL_BUILDING = "commercial_building"
    LANDFILL = "landfill"
    WASTEWATER = "wastewater"
    ALL = "all"  # Applies to all facilities
    LARGE_EMITTERS = "large_emitters"  # Facilities >25,000 tonnes CO2-e


# ============================================================================
# Document Metadata Types
# ============================================================================


class JurisdictionLevel(str, Enum):
    """Government jurisdiction levels."""

    FEDERAL = "federal"
    STATE = "state"
    LOCAL = "local"


class SpatialScope(str, Enum):
    """Spatial scope of document applicability."""

    FEDERAL = "federal"  # Applies nationwide
    STATE = "state"  # Applies to specific state
    LOCAL = "local"  # Applies to specific LGA


class DocumentCategory(str, Enum):
    """Document categories."""

    ENVIRONMENT = "environment"
    PLANNING = "planning"
    LEGISLATION = "legislation"
    REGULATION = "regulation"
    GUIDELINES = "guidelines"
    POLICY = "policy"
    BUILDING = "building"
    HERITAGE = "heritage"


class DocumentTopic(str, Enum):
    """Specific document topics."""

    EMISSIONS_REPORTING = "emissions_reporting"
    BIODIVERSITY = "biodiversity"
    TREE_MANAGEMENT = "tree_management"
    CLIMATE_CHANGE = "climate_change"
    VEGETATION_MANAGEMENT = "vegetation_management"
    DEVELOPMENT_ASSESSMENT = "development_assessment"
    HERITAGE_PROTECTION = "heritage_protection"
    WASTE_MANAGEMENT = "waste_management"


# ============================================================================
# Regulatory Authorities
# ============================================================================


class RegulatoryAuthority(str, Enum):
    """Government regulatory authorities."""

    # Federal
    CLEAN_ENERGY_REGULATOR = "Clean Energy Regulator"
    IFRS_FOUNDATION = "IFRS Foundation"

    # NSW
    NSW_EPA = "NSW EPA"
    NSW_PLANNING = "NSW Planning"

    # Victoria
    VICTORIAN_EPA = "Victorian EPA"
    VIC_PLANNING = "Victorian Planning Authority"

    # South Australia
    SA_EPA = "SA EPA"
    SA_PLANNING = "SA Planning"

    # Other
    LOCAL_COUNCIL = "Local Council"


# ============================================================================
# Helper Functions
# ============================================================================


def get_state_mapping() -> dict[str, AustralianState]:
    """Get state name to AustralianState enum mapping.

    Returns
    -------
        Dict with various state name formats as keys

    """
    mapping = {}

    for state in AustralianState:
        # Add abbreviation
        mapping[state.value] = state
        mapping[state.value.lower()] = state

        # Add full name
        full = state.full_name
        mapping[full] = state
        mapping[full.lower()] = state

    # Add numeric codes
    mapping["1"] = AustralianState.NSW
    mapping["2"] = AustralianState.VIC
    mapping["3"] = AustralianState.QLD
    mapping["4"] = AustralianState.SA
    mapping["5"] = AustralianState.WA
    mapping["6"] = AustralianState.TAS
    mapping["7"] = AustralianState.NT
    mapping["8"] = AustralianState.ACT

    return mapping


def get_lga_mappings() -> dict[str, LGAInfo]:
    """Get LGA name to LGAInfo mapping.

    Returns
    -------
        Dict with various LGA name formats as keys

    """
    return KnownLGA.get_all()


# ============================================================================
# Parser Types
# ============================================================================


class ParserType(str, Enum):
    """Supported file parser types."""

    PDF = ".pdf"
    HTML = ".html"
    HTM = ".htm"


# ============================================================================
# Constants
# ============================================================================

# NGER thresholds
NGER_THRESHOLD_SMALL = 25000  # tonnes CO2-e
NGER_THRESHOLD_LARGE = 100000  # tonnes CO2-e

# Default values
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 10

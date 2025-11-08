"""Query Expansion for GreenGovRAG.

Expands queries with synonyms, acronyms, and related terms to improve retrieval.
"""

from __future__ import annotations

# Australian regulatory acronyms and their expansions
ACRONYM_EXPANSIONS = {
    # Federal Environmental
    "EPBC": "Environment Protection and Biodiversity Conservation",
    "EPBC Act": "Environment Protection and Biodiversity Conservation Act",
    "DCCEEW": "Department of Climate Change Energy Environment and Water",
    "DAWE": "Department of Agriculture Water and the Environment",
    # Emissions & Climate
    "NGER": "National Greenhouse and Energy Reporting",
    "NGERS": "National Greenhouse and Energy Reporting Scheme",
    "CER": "Clean Energy Regulator",
    "ACCU": "Australian Carbon Credit Unit",
    "ERF": "Emissions Reduction Fund",
    "NGA": "National Greenhouse Accounts",
    "UNFCCC": "United Nations Framework Convention on Climate Change",
    # ESG Frameworks
    "ISSB": "International Sustainability Standards Board",
    "IFRS": "International Financial Reporting Standards",
    "TCFD": "Task Force on Climate-related Financial Disclosures",
    "CDP": "Carbon Disclosure Project",
    "GRI": "Global Reporting Initiative",
    "SASB": "Sustainability Accounting Standards Board",
    # State Planning - NSW
    "NSW EPA": "New South Wales Environment Protection Authority",
    "SEPP": "State Environmental Planning Policy",
    "LEP": "Local Environmental Plan",
    "DCP": "Development Control Plan",
    # State Planning - Victoria
    "VPP": "Victoria Planning Provisions",
    "VIC EPA": "Victorian Environment Protection Authority",
    "PPF": "Planning Policy Framework",
    # State Planning - South Australia
    "SA EPA": "South Australia Environment Protection Authority",
    "PDC": "Planning and Design Code",
    # State Planning - Western Australia
    "WA EPA": "Western Australian Environment Protection Authority",
    "WAPC": "Western Australian Planning Commission",
    # State Planning - Queensland
    "QLD EPA": "Queensland Environment Protection Authority",
    "SPP": "State Planning Policy",
    # Building & Construction
    "NCC": "National Construction Code",
    "BCA": "Building Code of Australia",
    "ABCB": "Australian Building Codes Board",
    "NABERS": "National Australian Built Environment Rating System",
    # Heritage
    "AHC": "Australian Heritage Council",
    "NHL": "National Heritage List",
    # Other Common Terms
    "LGA": "Local Government Area",
    "ABS": "Australian Bureau of Statistics",
    "MNES": "Matters of National Environmental Significance",
    "EIA": "Environmental Impact Assessment",
    "EIS": "Environmental Impact Statement",
    "ANZSIC": "Australian and New Zealand Standard Industrial Classification",
    # Greenhouse Gases
    "GHG": "Greenhouse Gas",
    "CO2": "Carbon Dioxide",
    "CH4": "Methane",
    "N2O": "Nitrous Oxide",
    "SF6": "Sulfur Hexafluoride",
    "HFC": "Hydrofluorocarbon",
    "PFC": "Perfluorocarbon",
    "NF3": "Nitrogen Trifluoride",
    # Scope 2 Terms
    "REC": "Renewable Energy Certificate",
    "GreenPower": "GreenPower Renewable Energy",
    "LGC": "Large-scale Generation Certificate",
    # Common Abbreviations
    "t CO2-e": "tonnes carbon dioxide equivalent",
    "tCO2e": "tonnes carbon dioxide equivalent",
    "kt": "kilotonnes",
    "Mt": "megatonnes",
    "MWh": "megawatt hour",
    "GWh": "gigawatt hour",
    "TJ": "terajoule",
}


def expand_query(query: str, max_expansions: int = 3) -> str:
    """Expand query with acronym definitions.

    Args:
    ----
        query: Original query string
        max_expansions: Maximum number of acronyms to expand (default: 3)

    Returns:
    -------
        Expanded query string with acronyms replaced/augmented

    Example:
    -------
        >>> expand_query("What triggers EPBC Act referral?")
        "What triggers EPBC Environment Protection and Biodiversity Conservation Act referral?"
        >>> expand_query("NGER reporting threshold")
        "NGER National Greenhouse and Energy Reporting reporting threshold"

    """
    expanded = query
    expansions_made = 0

    # Sort by length (longest first) to avoid partial matches
    sorted_acronyms = sorted(
        ACRONYM_EXPANSIONS.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    )

    for acronym, expansion in sorted_acronyms:
        if expansions_made >= max_expansions:
            break

        # Check if acronym appears as whole word (case-insensitive)
        import re

        pattern = r"\b" + re.escape(acronym) + r"\b"

        if re.search(pattern, query, re.IGNORECASE):
            # Replace first occurrence with "acronym (expansion)"
            # or just add expansion after acronym
            expanded = re.sub(
                pattern,
                f"{acronym} {expansion}",
                expanded,
                count=1,
                flags=re.IGNORECASE,
            )
            expansions_made += 1

    return expanded


def expand_query_with_synonyms(query: str) -> list[str]:
    """Expand query with synonyms and related terms.

    Generates multiple query variations to improve recall.

    Args:
    ----
        query: Original query string

    Returns:
    -------
        List of query variations including original

    Example:
    -------
        >>> expand_query_with_synonyms("emission reporting")
        [
            "emission reporting",
            "emissions reporting",
            "greenhouse gas reporting",
            "GHG reporting"
        ]

    """
    variations = [query]

    # Emission/Emissions variations
    if "emission" in query.lower() and "emissions" not in query.lower():
        variations.append(query.replace("emission", "emissions"))
    elif "emissions" in query.lower():
        variations.append(query.replace("emissions", "emission"))

    # Climate/Environmental variations
    if "climate" in query.lower():
        variations.append(query.replace("climate", "environmental"))
    if "environmental" in query.lower():
        variations.append(query.replace("environmental", "climate"))

    # Planning/Development variations
    if "planning" in query.lower():
        variations.append(query.replace("planning", "development"))
    if "development" in query.lower() and "planning" not in query.lower():
        variations.append(query.replace("development", "planning"))

    # Reporting/Disclosure variations
    if "reporting" in query.lower():
        variations.append(query.replace("reporting", "disclosure"))
    if "disclosure" in query.lower():
        variations.append(query.replace("disclosure", "reporting"))

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for var in variations:
        if var.lower() not in seen:
            seen.add(var.lower())
            unique_variations.append(var)

    return unique_variations


def detect_jurisdiction_from_query(query: str) -> str | None:
    """Detect jurisdiction level from query text.

    Args:
    ----
        query: Query string

    Returns:
    -------
        Jurisdiction level ("federal", "state", or "local") or None

    Example:
    -------
        >>> detect_jurisdiction_from_query("EPBC Act requirements")
        "federal"
        >>> detect_jurisdiction_from_query("Adelaide tree policy")
        "local"

    """
    query_lower = query.lower()

    # Federal indicators
    federal_indicators = [
        "epbc",
        "nger",
        "commonwealth",
        "federal",
        "australia-wide",
        "national",
        "cer",
        "clean energy regulator",
        "dcceew",
        "safeguard mechanism",
        "australian government",
    ]

    # State indicators
    state_indicators = [
        "nsw",
        "victoria",
        "queensland",
        "south australia",
        "western australia",
        "tasmania",
        "vic",
        "qld",
        "sa",
        "wa",
        "tas",
        "nt",
        "act",
        "state planning",
        "sepp",
        "vpp",
        "state epa",
    ]

    # Local indicators
    local_indicators = [
        "city of",
        "council",
        "local government",
        "lga",
        "municipality",
        "adelaide",
        "sydney",
        "melbourne",
        "brisbane",
        "perth",
        "port adelaide",
        "unley",
        "burnside",
        "norwood",
    ]

    # Count matches
    federal_count = sum(1 for ind in federal_indicators if ind in query_lower)
    state_count = sum(1 for ind in state_indicators if ind in query_lower)
    local_count = sum(1 for ind in local_indicators if ind in query_lower)

    # Return jurisdiction with most matches
    if federal_count > state_count and federal_count > local_count:
        return "federal"
    elif state_count > local_count:
        return "state"
    elif local_count > 0:
        return "local"

    return None


def extract_topic_from_query(query: str) -> str | None:
    """Extract topic from query text.

    Args:
    ----
        query: Query string

    Returns:
    -------
        Topic keyword or None

    Example:
    -------
        >>> extract_topic_from_query("What are emission reporting requirements?")
        "emissions_reporting"
        >>> extract_topic_from_query("Biodiversity conservation rules")
        "biodiversity"

    """
    query_lower = query.lower()

    # Topic keyword mapping
    topic_keywords = {
        "emissions_reporting": [
            "emission",
            "reporting",
            "nger",
            "greenhouse gas",
            "ghg",
        ],
        "biodiversity": [
            "biodiversity",
            "species",
            "habitat",
            "ecosystem",
            "flora",
            "fauna",
        ],
        "tree_management": ["tree", "vegetation", "canopy", "urban forest"],
        "climate_change": [
            "climate change",
            "net zero",
            "carbon neutral",
            "decarbonisation",
        ],
        "heritage": ["heritage", "historic", "conservation", "cultural"],
        "planning": ["planning", "zoning", "land use", "development plan"],
        "environmental_assessment": [
            "environmental assessment",
            "eia",
            "eis",
            "impact assessment",
        ],
    }

    # Count keyword matches for each topic
    topic_scores = {}
    for topic, keywords in topic_keywords.items():
        score = sum(1 for kw in keywords if kw in query_lower)
        if score > 0:
            topic_scores[topic] = score

    # Return topic with highest score
    if topic_scores:
        return max(topic_scores, key=lambda k: topic_scores[k])

    return None


if __name__ == "__main__":
    # Example usage
    queries = [
        "What triggers a referral under the EPBC Act?",
        "NGER reporting threshold for facilities",
        "VPP zoning rules in Victoria",
        "Adelaide Park Lands heritage requirements",
        "NSW emission disclosure requirements",
    ]

    print("=== Query Expansion Examples ===\n")
    for query in queries:
        expanded = expand_query(query)
        jurisdiction = detect_jurisdiction_from_query(query)
        topic = extract_topic_from_query(query)

        print(f"Original:     {query}")
        print(f"Expanded:     {expanded}")
        print(f"Jurisdiction: {jurisdiction}")
        print(f"Topic:        {topic}")
        print()

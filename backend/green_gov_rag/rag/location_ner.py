"""Named Entity Recognition for Location Extraction.

Extracts Australian locations (LGAs, states, cities) from text queries
and maps them to standardized codes for geospatial filtering.

Uses both rule-based matching and LLM-based extraction for robustness.
"""

from __future__ import annotations

import re
from typing import Any

from langchain.prompts import ChatPromptTemplate

from green_gov_rag.types import get_lga_mappings, get_state_mapping


class LocationNER:
    """Extract and normalize Australian locations from text."""

    def __init__(self, use_llm: bool = True, llm_model: str = "gpt-3.5-turbo"):
        """Initialize location NER.

        Args:
        ----
            use_llm: Whether to use LLM for extraction (more accurate)
            llm_model: OpenAI model to use for LLM-based extraction

        """
        self.use_llm = use_llm
        self.llm: Any = None
        if use_llm:
            from langchain.chat_models import ChatOpenAI

            self.llm = ChatOpenAI(model=llm_model, temperature=0.0)  # type: ignore[misc]

        # Load mappings from types module
        self._state_mappings = get_state_mapping()
        self._lga_mappings = get_lga_mappings()

    def extract_locations(self, text: str) -> dict[str, Any]:
        """Extract locations from text using both rule-based and LLM methods.

        Args:
        ----
            text: Query text to extract locations from

        Returns:
        -------
            Dict with extracted locations:
            {
                "states": ["SA", "NSW"],
                "lgas": [{"name": "Adelaide", "code": "40070", "state": "SA"}],
                "raw_locations": ["Adelaide", "South Australia"]
            }

        """
        # Rule-based extraction
        rule_based = self._extract_rule_based(text)

        # LLM-based extraction (if enabled)
        if self.use_llm:
            llm_based = self._extract_llm_based(text)
            # Merge results
            return self._merge_results(rule_based, llm_based)

        return rule_based

    def _extract_rule_based(self, text: str) -> dict[str, Any]:
        """Extract locations using rule-based pattern matching.

        Args:
        ----
            text: Query text

        Returns:
        -------
            Dict with extracted locations

        """
        text_lower = text.lower()
        results: dict[str, Any] = {
            "states": [],
            "lgas": [],
            "raw_locations": [],
        }

        # Extract states
        for state_name, state_enum in self._state_mappings.items():
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(state_name) + r"\b"
            if re.search(pattern, text_lower):
                state_code = state_enum.value
                if state_code not in results["states"]:
                    results["states"].append(state_code)
                    results["raw_locations"].append(state_name)

        # Extract LGAs
        for lga_name, lga_info in self._lga_mappings.items():
            pattern = r"\b" + re.escape(lga_name) + r"\b"
            if re.search(pattern, text_lower):
                # Convert LGAInfo to dict format for backward compatibility
                lga_dict = {
                    "name": lga_info.name,
                    "code": lga_info.code,
                    "state": lga_info.state.value,
                }
                if lga_dict not in results["lgas"]:
                    results["lgas"].append(lga_dict)
                    results["raw_locations"].append(lga_name)

        return results

    def _extract_llm_based(self, text: str) -> dict[str, Any]:
        """Extract locations using LLM.

        Args:
        ----
            text: Query text

        Returns:
        -------
            Dict with extracted locations

        """
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a location extraction expert for Australian queries.",
                ),
                (
                    "human",
                    """Extract Australian locations from this text.

Text: {text}

Return a JSON object with:
- "states": list of Australian state/territory codes (NSW, VIC, QLD, SA, WA, TAS, NT, ACT)
- "lgas": list of Local Government Area names
- "cities": list of city/suburb names

If no locations found, return empty lists.

Example:
Text: "What are the tree rules in Adelaide, South Australia?"
Output: {{"states": ["SA"], "lgas": ["Adelaide"], "cities": ["Adelaide"]}}

Only return the JSON object, nothing else.""",
                ),
            ],
        )

        chain: Any = prompt | self.llm
        response = chain.invoke({"text": text})

        # Parse LLM response
        try:
            import json

            result = json.loads(response.content)

            # Map LGAs to our standard format
            lgas = []
            for lga_name in result.get("lgas", []):
                lga_lower = lga_name.lower()
                if lga_lower in self._lga_mappings:
                    lga_info = self._lga_mappings[lga_lower]
                    lga_dict = {
                        "name": lga_info.name,
                        "code": lga_info.code,
                        "state": lga_info.state.value,
                    }
                    lgas.append(lga_dict)

            return {
                "states": result.get("states", []),
                "lgas": lgas,
                "raw_locations": result.get("lgas", []) + result.get("cities", []),
            }
        except json.JSONDecodeError:
            return {"states": [], "lgas": [], "raw_locations": []}

    def _merge_results(
        self,
        rule_based: dict[str, Any],
        llm_based: dict[str, Any],
    ) -> dict[str, Any]:
        """Merge rule-based and LLM results.

        Args:
        ----
            rule_based: Results from rule-based extraction
            llm_based: Results from LLM extraction

        Returns:
        -------
            Merged results

        """
        merged: dict[str, Any] = {
            "states": list(set(rule_based["states"] + llm_based["states"])),
            "lgas": rule_based["lgas"]
            + [lga for lga in llm_based["lgas"] if lga not in rule_based["lgas"]],
            "raw_locations": list(
                set(rule_based["raw_locations"] + llm_based["raw_locations"]),
            ),
        }

        return merged

    def extract_lga_codes(self, text: str) -> list[str]:
        """Extract LGA codes from text (convenience method).

        Args:
        ----
            text: Query text

        Returns:
        -------
            List of LGA codes

        """
        locations = self.extract_locations(text)
        return [lga["code"] for lga in locations["lgas"]]

    def extract_state_codes(self, text: str) -> list[str]:
        """Extract state codes from text (convenience method).

        Args:
        ----
            text: Query text

        Returns:
        -------
            List of state codes

        """
        locations = self.extract_locations(text)
        return locations["states"]

    def add_lga_mapping(
        self,
        name: str,
        lga_code: str,
        state: str,
        official_name: str | None = None,
    ) -> None:
        """Add a new LGA mapping.

        Args:
        ----
            name: Common name (e.g., "adelaide")
            lga_code: ABS LGA code
            state: State code (e.g., "NSW", "VIC")
            official_name: Official LGA name (defaults to capitalized name)

        """
        from green_gov_rag.types import AustralianState, LGAInfo

        # Convert state string to AustralianState enum
        state_enum = AustralianState(state)

        # Create LGAInfo and add to mappings
        lga_info = LGAInfo(
            name=official_name or name.title(),
            code=lga_code,
            state=state_enum,
        )
        self._lga_mappings[name.lower()] = lga_info


class QueryLocationProcessor:
    """Process queries to extract and enrich with location information."""

    def __init__(self, ner: LocationNER | None = None):
        """Initialize processor.

        Args:
        ----
            ner: LocationNER instance (creates one if not provided)

        """
        self.ner = ner or LocationNER(use_llm=True)

    def process_query(self, query: str) -> dict[str, Any]:
        """Process query and extract location metadata.

        Args:
        ----
            query: User query text

        Returns:
        -------
            Dict with query and location metadata

        """
        locations = self.ner.extract_locations(query)

        return {
            "original_query": query,
            "locations": locations,
            "has_location": bool(locations["states"] or locations["lgas"]),
            "lga_codes": [lga["code"] for lga in locations["lgas"]],
            "state_codes": locations["states"],
        }


# Example usage
if __name__ == "__main__":
    # Initialize NER
    ner = LocationNER(use_llm=False)  # Rule-based only for demo

    # Test queries
    test_queries = [
        "What are the tree preservation rules in Adelaide?",
        "Show me emissions reporting requirements for Port Adelaide Enfield",
        "What are the planning policies in South Australia?",
        "Tell me about biodiversity offsets in Sydney",
        "What are the NGER requirements in Victoria?",
    ]

    print("=" * 70)
    print("Location NER Demo")
    print("=" * 70)

    for query in test_queries:
        print(f"\nQuery: {query}")

        locations = ner.extract_locations(query)

        print(f"States: {locations['states']}")
        print(f"LGAs: {[lga['name'] for lga in locations['lgas']]}")
        print(f"LGA Codes: {[lga['code'] for lga in locations['lgas']]}")
        print(f"Raw locations: {locations['raw_locations']}")

    # Test with processor
    print("\n" + "=" * 70)
    print("Query Processor Demo")
    print("=" * 70)

    processor = QueryLocationProcessor(ner)

    query = "What are the tree rules in Adelaide, South Australia?"
    result = processor.process_query(query)

    print(f"\nQuery: {result['original_query']}")
    print(f"Has location: {result['has_location']}")
    print(f"LGA codes: {result['lga_codes']}")
    print(f"State codes: {result['state_codes']}")

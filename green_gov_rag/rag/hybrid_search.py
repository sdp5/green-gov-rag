"""Hybrid Geospatial Search for GreenGovRAG.

Combines vector similarity search, spatial filtering, and metadata filtering
following the Elasticsearch/Bedrock geospatial RAG pattern.

Key Features:
1. Vector similarity search (semantic search)
2. Spatial filtering by LGA codes, state, or coordinates
3. Metadata filtering (jurisdiction, topic, ESG scope)
4. Hierarchical spatial filtering (federal → state → local)
5. Re-ranking by relevance
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from langchain.docstore.document import Document

from green_gov_rag.rag.location_ner import LocationNER
from green_gov_rag.rag.vector_store import VectorStore


@dataclass
class SpatialQuery:
    """Spatial query parameters extracted from user input."""

    location_name: str  # e.g., "City of Adelaide"
    lga_codes: list[str]  # e.g., ["40070"]
    state: str | None = None  # e.g., "SA"
    coordinates: tuple[float, float] | None = None  # (lat, lon)
    radius_km: float = 5.0  # Radius for coordinate-based search


class HybridGeospatialSearch:
    """Combine lexical, spatial, and vector search for geospatial RAG."""

    def __init__(self, vector_store: VectorStore, enable_ner: bool = True):
        """Initialize hybrid search with vector store.

        Args:
        ----
            vector_store: VectorStore instance for similarity search
            enable_ner: Whether to enable NER for automatic location extraction

        """
        self.vector_store = vector_store
        self.ner = LocationNER(use_llm=False) if enable_ner else None

    def search(
        self,
        query: str,
        spatial_query: Optional[SpatialQuery] = None,
        metadata_filters: Optional[dict] = None,
        k: int = 10,
    ) -> list[Document]:
        """Hybrid search combining vector, spatial, and metadata filtering.

        Args:
        ----
            query: User query string
            spatial_query: Optional SpatialQuery for location-based filtering
            metadata_filters: Optional dict for metadata filtering
            k: Number of initial results to retrieve (before filtering)

        Returns:
        -------
            List of Document objects ranked by relevance

        """
        # Step 1: Vector similarity search
        # Retrieve more results initially to account for filtering
        initial_k = k * 3 if (spatial_query or metadata_filters) else k
        results = self.vector_store.similarity_search(query, k=initial_k)

        # Step 2: Apply spatial filters if provided
        if spatial_query:
            results = self._filter_by_spatial(results, spatial_query)

        # Step 3: Apply metadata filters if provided
        if metadata_filters:
            results = self._filter_by_metadata(results, metadata_filters)

        # Step 4: Re-rank by relevance (already ordered by similarity)
        # Keep top k results
        return results[:k]

    def _filter_by_spatial(
        self,
        results: list[Document],
        spatial_query: SpatialQuery,
    ) -> list[Document]:
        """Filter results by spatial criteria using hierarchical filtering.

        Hierarchical filtering logic:
        1. Federal documents (spatial_scope=federal) → always included
        2. State documents (spatial_scope=state) → included if state matches
        3. Local documents (spatial_scope=local) → included if LGA code matches

        Args:
        ----
            results: List of Document objects from vector search
            spatial_query: SpatialQuery with location criteria

        Returns:
        -------
            Filtered list of Document objects

        """
        filtered = []

        for doc in results:
            metadata = doc.metadata
            spatial_scope = metadata.get("spatial_scope", "")

            # Federal documents always apply
            if spatial_scope == "federal":
                filtered.append(doc)
                continue

            # State documents: check if state matches
            if spatial_scope == "state":
                doc_state = metadata.get("state")
                if spatial_query.state and doc_state == spatial_query.state:
                    filtered.append(doc)
                continue

            # Local documents: check LGA codes
            if spatial_scope == "local":
                doc_lga_codes = metadata.get("lga_codes", [])

                # Check if any of the query LGA codes match document LGA codes
                if any(code in spatial_query.lga_codes for code in doc_lga_codes):
                    filtered.append(doc)
                    continue

                # Also check state match for local documents
                # (local docs in the same state may be relevant)
                doc_state = metadata.get("state")
                if spatial_query.state and doc_state == spatial_query.state:
                    # Add with lower priority (could implement scoring here)
                    filtered.append(doc)

        return filtered

    def _filter_by_metadata(
        self,
        results: list[Document],
        metadata_filters: dict,
    ) -> list[Document]:
        """Filter results by metadata criteria.

        Supports filtering by:
        - jurisdiction (federal, state, local)
        - category (environment, planning, etc.)
        - topic (emissions_reporting, biodiversity, etc.)
        - ESG metadata (emission_scopes, frameworks, etc.)

        Args:
        ----
            results: List of Document objects
            metadata_filters: Dict of metadata key-value pairs to filter on

        Returns:
        -------
            Filtered list of Document objects

        """
        filtered = []

        for doc in results:
            metadata = doc.metadata
            match = True

            for key, expected_value in metadata_filters.items():
                # Handle nested ESG metadata (e.g., esg_metadata.emission_scopes)
                value: object
                if "." in key:
                    keys = key.split(".")
                    value = metadata
                    for k in keys:
                        if isinstance(value, dict):
                            value = value.get(k, {})
                        else:
                            value = None
                        if value is None:
                            break
                else:
                    value = metadata.get(key)

                # Support list of expected values (OR logic)
                if isinstance(expected_value, list):
                    # Check if doc value is in expected list
                    # OR if doc value is a list, check for overlap
                    if isinstance(value, list):
                        if not any(v in expected_value for v in value):
                            match = False
                            break
                    elif value not in expected_value:
                        match = False
                        break
                # Single value comparison
                elif isinstance(value, list):
                    # Doc has list, expected is single value
                    if expected_value not in value:
                        match = False
                        break
                elif value != expected_value:
                    match = False
                    break

            if match:
                filtered.append(doc)

        return filtered

    def search_with_lga(
        self,
        query: str,
        lga_name: str,
        lga_code: str,
        state: str,
        k: int = 10,
    ) -> list[Document]:
        """Convenience method for LGA-based search.

        Args:
        ----
            query: User query string
            lga_name: Name of the LGA (e.g., "City of Adelaide")
            lga_code: ABS LGA code (e.g., "40070")
            state: State code (e.g., "SA")
            k: Number of results to return

        Returns:
        -------
            List of Document objects relevant to the LGA

        """
        spatial_query = SpatialQuery(
            location_name=lga_name,
            lga_codes=[lga_code],
            state=state,
        )

        return self.search(query=query, spatial_query=spatial_query, k=k)

    def search_with_esg_filters(
        self,
        query: str,
        emission_scopes: list[str] | None = None,
        frameworks: list[str] | None = None,
        greenhouse_gases: list[str] | None = None,
        consolidation_method: str | None = None,
        methodology_type: str | None = None,
        scope_3_categories: list[str] | None = None,
        regulator: str | None = None,
        activity_types: list[str] | None = None,
        industry_codes: list[str] | None = None,
        k: int = 10,
    ) -> list[Document]:
        """Convenience method for ESG-filtered search.

        Args:
        ----
            query: User query string
            emission_scopes: List of emission scopes (e.g., ["scope_1", "scope_2"])
            frameworks: List of frameworks (e.g., ["NGER", "ISSB", "GHG_Protocol"])
            greenhouse_gases: List of gases (e.g., ["CO2", "CH4", "N2O", "SF6", "HFCs", "PFCs", "NF3"])
            consolidation_method: Consolidation approach (e.g., "operational_control", "equity_share", "financial_control")
            methodology_type: Methodology type (e.g., "calculation", "reporting", "verification")
            scope_3_categories: List of Scope 3 categories (e.g., ["upstream_transport", "business_travel"])
            regulator: Regulator name (e.g., "Clean Energy Regulator", "NSW EPA")
            activity_types: List of activity types (e.g., ["fuel_combustion", "electricity_consumption"])
            industry_codes: List of ANZSIC industry codes (e.g., ["B0600"])
            k: Number of results to return

        Returns:
        -------
            List of Document objects matching ESG criteria

        """
        metadata_filters: dict[str, object] = {}

        if emission_scopes:
            metadata_filters["esg_metadata.emission_scopes"] = emission_scopes

        if frameworks:
            metadata_filters["esg_metadata.frameworks"] = frameworks

        if greenhouse_gases:
            metadata_filters["esg_metadata.greenhouse_gases"] = greenhouse_gases

        if consolidation_method:
            metadata_filters["esg_metadata.consolidation_method"] = consolidation_method

        if methodology_type:
            metadata_filters["esg_metadata.methodology_type"] = methodology_type

        if scope_3_categories:
            metadata_filters["esg_metadata.scope_3_categories"] = scope_3_categories

        if regulator:
            metadata_filters["esg_metadata.regulator"] = regulator

        if activity_types:
            metadata_filters["esg_metadata.activity_types"] = activity_types

        if industry_codes:
            metadata_filters["esg_metadata.industry_codes"] = industry_codes

        return self.search(query=query, metadata_filters=metadata_filters, k=k)

    def search_with_auto_location(self, query: str, k: int = 10) -> list[Document]:
        """Search with automatic location extraction from query text.

        Uses NER to extract LGA codes and states from the query, then
        performs spatial filtering automatically.

        Args:
        ----
            query: User query text (e.g., "What are tree rules in Adelaide?")
            k: Number of results to return

        Returns:
        -------
            List of Document objects matching query and extracted locations

        Example:
        -------
            >>> search_with_auto_location("emission rules in Port Adelaide Enfield", k=5)
            # Automatically extracts LGA code "40280" and state "SA"

        """
        if not self.ner:
            # NER disabled, fall back to regular search
            return self.search(query=query, k=k)

        # Extract locations from query
        locations = self.ner.extract_locations(query)
        lga_codes = [lga["code"] for lga in locations["lgas"]]
        state_codes = locations["states"]

        # Build spatial query if locations found
        if lga_codes or state_codes:
            spatial_query = SpatialQuery(
                location_name=", ".join(locations["raw_locations"]),
                lga_codes=lga_codes,
                state=state_codes[0] if state_codes else None,
            )
            return self.search(query=query, spatial_query=spatial_query, k=k)

        # No locations found, perform regular search
        return self.search(query=query, k=k)

    def search_by_jurisdiction_and_category(
        self,
        query: str,
        jurisdiction: str | None = None,
        category: str | None = None,
        topic: str | None = None,
        region: str | None = None,
        k: int = 10,
    ) -> list[Document]:
        """Search filtered by jurisdiction, category, and topic.

        Args:
        ----
            query: User query string
            jurisdiction: Jurisdiction level (e.g., "federal", "state", "local")
            category: Document category (e.g., "environment", "planning", "legislation")
            topic: Specific topic (e.g., "emissions_reporting", "biodiversity", "tree_management")
            region: Region name (e.g., "South Australia", "New South Wales")
            k: Number of results to return

        Returns:
        -------
            List of Document objects matching criteria

        """
        metadata_filters: dict[str, object] = {}

        if jurisdiction:
            metadata_filters["jurisdiction"] = jurisdiction

        if category:
            metadata_filters["category"] = category

        if topic:
            metadata_filters["topic"] = topic

        if region:
            metadata_filters["region"] = region

        return self.search(query=query, metadata_filters=metadata_filters, k=k)

    def search_nger_compliant(
        self,
        query: str,
        reportable_under_nger: bool = True,
        nger_threshold_tonnes: int | None = None,
        k: int = 10,
    ) -> list[Document]:
        """Search for NGER-compliant documents.

        Args:
        ----
            query: User query string
            reportable_under_nger: Filter for NGER reportability
            nger_threshold_tonnes: Filter by NGER threshold (e.g., 25000, 100000)
            k: Number of results to return

        Returns:
        -------
            List of NGER-compliant Document objects

        """
        metadata_filters: dict[str, object] = {
            "esg_metadata.reportable_under_nger": reportable_under_nger,
        }

        if nger_threshold_tonnes:
            metadata_filters[
                "esg_metadata.nger_threshold_tonnes"
            ] = nger_threshold_tonnes

        return self.search(query=query, metadata_filters=metadata_filters, k=k)

    def search_scope_3(
        self,
        query: str,
        scope_3_categories: list[str] | None = None,
        frameworks: list[str] | None = None,
        include_issb: bool = True,
        k: int = 10,
    ) -> list[Document]:
        """Search for Scope 3 emissions guidance.

        Args:
        ----
            query: User query string
            scope_3_categories: List of Scope 3 categories to filter by:
                - purchased_goods_services (Cat 1)
                - capital_goods (Cat 2)
                - fuel_energy_activities (Cat 3)
                - upstream_transport (Cat 4)
                - waste_generated (Cat 5)
                - business_travel (Cat 6)
                - employee_commuting (Cat 7)
                - upstream_leased_assets (Cat 8)
                - downstream_transport (Cat 9)
                - processing_sold_products (Cat 10)
                - use_of_sold_products (Cat 11)
                - end_of_life_treatment (Cat 12)
                - downstream_leased_assets (Cat 13)
                - franchises (Cat 14)
                - investments (Cat 15)
            frameworks: ESG frameworks (e.g., ["ISSB", "GHG_Protocol", "GRI"])
            include_issb: Whether to include ISSB standards (default: True)
            k: Number of results to return

        Returns:
        -------
            List of Scope 3 Document objects

        """
        metadata_filters: dict[str, object] = {
            "esg_metadata.emission_scopes": ["scope_3"],
        }

        if scope_3_categories:
            metadata_filters["esg_metadata.scope_3_categories"] = scope_3_categories

        if frameworks:
            metadata_filters["esg_metadata.frameworks"] = frameworks
        elif include_issb:
            # Default to ISSB if no frameworks specified
            metadata_filters["esg_metadata.frameworks"] = ["ISSB"]

        return self.search(query=query, metadata_filters=metadata_filters, k=k)

    def search_scope_3_by_type(
        self,
        query: str,
        scope_type: str = "upstream",
        k: int = 10,
    ) -> list[Document]:
        """Search Scope 3 emissions by upstream or downstream type.

        Args:
        ----
            query: User query string
            scope_type: Either "upstream" (categories 1-8) or "downstream" (categories 9-15)
            k: Number of results to return

        Returns:
        -------
            List of Scope 3 Document objects filtered by type

        """
        if scope_type.lower() == "upstream":
            categories = [
                "purchased_goods_services",
                "capital_goods",
                "fuel_energy_activities",
                "upstream_transport",
                "waste_generated",
                "business_travel",
                "employee_commuting",
                "upstream_leased_assets",
            ]
        elif scope_type.lower() == "downstream":
            categories = [
                "downstream_transport",
                "processing_sold_products",
                "use_of_sold_products",
                "end_of_life_treatment",
                "downstream_leased_assets",
                "franchises",
                "investments",
            ]
        else:
            msg = (
                f"Invalid scope_type: {scope_type}. Must be 'upstream' or 'downstream'"
            )
            raise ValueError(
                msg,
            )

        return self.search_scope_3(query=query, scope_3_categories=categories, k=k)

    def advanced_search(
        self,
        query: str,
        # Spatial filters
        lga_codes: list[str] | None = None,
        state: str | None = None,
        # Basic metadata
        jurisdiction: str | None = None,
        category: str | None = None,
        topic: str | None = None,
        # ESG filters
        emission_scopes: list[str] | None = None,
        frameworks: list[str] | None = None,
        greenhouse_gases: list[str] | None = None,
        regulator: str | None = None,
        # Industry filters
        industry_codes: list[str] | None = None,
        facility_types: list[str] | None = None,
        k: int = 10,
    ) -> list[Document]:
        """Advanced search with multiple filter types.

        Combines spatial, metadata, and ESG filters for precise retrieval.

        Args:
        ----
            query: User query string
            lga_codes: List of LGA codes for spatial filtering
            state: State code for spatial filtering
            jurisdiction: Jurisdiction level (federal/state/local)
            category: Document category
            topic: Specific topic
            emission_scopes: List of emission scopes
            frameworks: List of ESG frameworks
            greenhouse_gases: List of greenhouse gases
            regulator: Regulator name
            industry_codes: List of ANZSIC codes
            facility_types: List of facility types
            k: Number of results to return

        Returns:
        -------
            List of filtered and ranked Document objects

        """
        # Build spatial query
        spatial_query = None
        if lga_codes or state:
            spatial_query = SpatialQuery(
                location_name="",
                lga_codes=lga_codes or [],
                state=state,
            )

        # Build metadata filters
        metadata_filters: dict[str, object] = {}

        if jurisdiction:
            metadata_filters["jurisdiction"] = jurisdiction

        if category:
            metadata_filters["category"] = category

        if topic:
            metadata_filters["topic"] = topic

        if emission_scopes:
            metadata_filters["esg_metadata.emission_scopes"] = emission_scopes

        if frameworks:
            metadata_filters["esg_metadata.frameworks"] = frameworks

        if greenhouse_gases:
            metadata_filters["esg_metadata.greenhouse_gases"] = greenhouse_gases

        if regulator:
            metadata_filters["esg_metadata.regulator"] = regulator

        if industry_codes:
            metadata_filters["esg_metadata.industry_codes"] = industry_codes

        if facility_types:
            metadata_filters["esg_metadata.facility_types"] = facility_types

        return self.search(
            query=query,
            spatial_query=spatial_query,
            metadata_filters=metadata_filters or None,
            k=k,
        )


# Example usage
if __name__ == "__main__":
    from green_gov_rag.rag.embeddings import ChunkEmbedder

    # Sample chunks with spatial metadata
    chunks = [
        {
            "content": "NGER requires reporting of CO2, CH4, N2O emissions.",
            "metadata": {
                "title": "CER NGER Guideline",
                "spatial_scope": "federal",
                "esg_metadata": {
                    "frameworks": ["NGER"],
                    "emission_scopes": ["scope_1"],
                    "greenhouse_gases": ["CO2", "CH4", "N2O"],
                },
            },
        },
        {
            "content": "Adelaide Park Lands require heritage approval for development.",
            "metadata": {
                "title": "City of Adelaide Guidelines",
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": ["40070"],
                "lga_names": ["City of Adelaide"],
            },
        },
        {
            "content": "SA Planning and Design Code governs all development in South Australia.",
            "metadata": {
                "title": "SA Planning Code",
                "spatial_scope": "state",
                "state": "SA",
            },
        },
    ]

    # Initialize embeddings and vector store
    embeddings = ChunkEmbedder().embedder
    vector_store = VectorStore(embeddings=embeddings)
    vector_store.build_store(chunks)

    # Initialize hybrid search
    hybrid_search = HybridGeospatialSearch(vector_store)

    # Example 1: Search with LGA filter
    print("=== Search with LGA Filter ===")
    results = hybrid_search.search_with_lga(
        query="What are the development rules?",
        lga_name="City of Adelaide",
        lga_code="40070",
        state="SA",
        k=5,
    )
    for doc in results:
        print(f"- {doc.metadata.get('title')}: {doc.page_content[:60]}...")

    # Example 2: Search with ESG filters
    print("\n=== Search with ESG Filters ===")
    results = hybrid_search.search_with_esg_filters(
        query="What are the emission reporting requirements?",
        frameworks=["NGER"],
        emission_scopes=["scope_1"],
        k=5,
    )
    for doc in results:
        print(f"- {doc.metadata.get('title')}: {doc.page_content[:60]}...")

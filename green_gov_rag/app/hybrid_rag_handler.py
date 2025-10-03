"""Hybrid RAG Handler for GreenGovRAG Streamlit UI.

This module provides a comprehensive search handler that integrates:
1. Hybrid geospatial search (vector + spatial + metadata filtering)
2. ESG/NGER-specific filtering (emissions, frameworks, regulators)
3. Location-based policy retrieval (LGA clicks, state filters)
4. Advanced metadata filtering (jurisdiction, category, topic)

Coordinates between the UI layer and the HybridGeospatialSearch backend.
"""

from typing import Optional

from green_gov_rag.rag.enhanced_response import ResponseFormatter
from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch, SpatialQuery


class GeospatialRAGHandler:
    """Handle geospatial RAG queries from the map UI."""

    def __init__(self, hybrid_search: HybridGeospatialSearch):
        """Initialize with hybrid search instance.

        Args:
            hybrid_search: HybridGeospatialSearch instance
        """
        self.hybrid_search = hybrid_search

    def handle_lga_click(
        self,
        lga_properties: dict,
        user_question: str,
        k: int = 10,
    ) -> list[dict]:
        """Handle LGA click event from map and return relevant policies.

        Args:
            lga_properties: GeoJSON properties from clicked LGA
                Expected keys: LGA_NAME, LGA_CODE, STATE_CODE/STATE
            user_question: User's question about the LGA
            k: Number of results to return

        Returns:
            List of dicts containing document content and metadata
        """
        # Extract LGA information from GeoJSON properties
        lga_name = lga_properties.get("LGA_NAME") or lga_properties.get("NAME", "")
        lga_code = lga_properties.get("LGA_CODE") or lga_properties.get(
            "LGA_CODE25", ""
        )
        state = lga_properties.get("STATE_CODE") or lga_properties.get("STE_NAME", "")

        # Handle state code conversion (e.g., "1" -> "NSW", "4" -> "SA")
        state_mapping = {
            "1": "NSW",
            "2": "VIC",
            "3": "QLD",
            "4": "SA",
            "5": "WA",
            "6": "TAS",
            "7": "NT",
            "8": "ACT",
        }
        if state in state_mapping:
            state = state_mapping[state]

        # Create spatial query
        spatial_query = SpatialQuery(
            location_name=lga_name,
            lga_codes=[lga_code] if lga_code else [],
            state=state,
        )

        # Perform hybrid search
        results = self.hybrid_search.search(
            query=user_question,
            spatial_query=spatial_query,
            k=k,
        )

        # Format results for UI
        formatted_results = []
        for doc in results:
            formatted_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "title": doc.metadata.get("title", "Untitled"),
                    "source_url": doc.metadata.get("source_url", ""),
                    "jurisdiction": doc.metadata.get("jurisdiction", ""),
                    "spatial_scope": doc.metadata.get("spatial_scope", ""),
                }
            )

        return formatted_results

    def search_with_auto_location(
        self,
        query: str,
        k: int = 10,
    ) -> list[dict]:
        """Search with automatic location extraction from query text.

        Uses NER to automatically extract LGA names and state codes from
        the query, then performs location-filtered search.

        Args:
            query: User query text (e.g., "What are tree rules in Adelaide?")
            k: Number of results to return

        Returns:
            List of formatted results with location context

        Example:
            >>> handler.search_with_auto_location(
            ...     "emission reporting in Port Adelaide Enfield"
            ... )
            # Automatically extracts LGA and state, performs spatial search
        """
        results = self.hybrid_search.search_with_auto_location(query=query, k=k)
        return self._format_results(results)

    def search_with_esg_filters(
        self,
        query: str,
        # ESG Framework filters
        frameworks: Optional[list[str]] = None,
        emission_scopes: Optional[list[str]] = None,
        greenhouse_gases: Optional[list[str]] = None,
        consolidation_method: Optional[str] = None,
        methodology_type: Optional[str] = None,
        regulator: Optional[str] = None,
        # Industry filters
        industry_codes: Optional[list[str]] = None,
        activity_types: Optional[list[str]] = None,
        k: int = 10,
    ) -> list[dict]:
        """Search with ESG/NGER-specific filters.

        Args:
            query: User query string
            frameworks: ESG frameworks (e.g., ["NGER", "ISSB", "GHG_Protocol"])
            emission_scopes: Emission scopes (e.g., ["scope_1", "scope_2"])
            greenhouse_gases: Greenhouse gases (e.g., ["CO2", "CH4"])
            consolidation_method: Consolidation approach
            methodology_type: Methodology type (calculation/reporting)
            regulator: Regulator name
            industry_codes: ANZSIC industry codes
            activity_types: Activity types
            k: Number of results

        Returns:
            List of formatted results
        """
        results = self.hybrid_search.search_with_esg_filters(
            query=query,
            frameworks=frameworks,
            emission_scopes=emission_scopes,
            greenhouse_gases=greenhouse_gases,
            consolidation_method=consolidation_method,
            methodology_type=methodology_type,
            regulator=regulator,
            industry_codes=industry_codes,
            activity_types=activity_types,
            k=k,
        )

        return self._format_results(results)

    def search_scope_3(
        self,
        query: str,
        scope_3_categories: Optional[list[str]] = None,
        scope_type: Optional[str] = None,
        frameworks: Optional[list[str]] = None,
        k: int = 10,
    ) -> list[dict]:
        """Search for Scope 3 emissions guidance.

        Args:
            query: User query string
            scope_3_categories: Specific Scope 3 categories to filter by
            scope_type: Filter by "upstream" (1-8) or "downstream" (9-15) categories
            frameworks: ESG frameworks (e.g., ["ISSB", "GHG_Protocol"])
            k: Number of results

        Returns:
            List of formatted Scope 3 results
        """
        if scope_type:
            # Use type-based search (upstream/downstream)
            results = self.hybrid_search.search_scope_3_by_type(
                query=query, scope_type=scope_type, k=k
            )
        else:
            # Use category-based search
            results = self.hybrid_search.search_scope_3(
                query=query,
                scope_3_categories=scope_3_categories,
                frameworks=frameworks,
                k=k,
            )

        return self._format_results(results)

    def _format_results(self, results: list) -> list[dict]:
        """Format Document results for UI display.

        Args:
            results: List of Document objects

        Returns:
            List of formatted result dicts
        """
        formatted_results = []
        for doc in results:
            esg_meta = doc.metadata.get("esg_metadata", {})
            formatted_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "title": doc.metadata.get("title", "Untitled"),
                    "source_url": doc.metadata.get("source_url", ""),
                    "jurisdiction": doc.metadata.get("jurisdiction", ""),
                    "spatial_scope": doc.metadata.get("spatial_scope", ""),
                    "category": doc.metadata.get("category", ""),
                    "topic": doc.metadata.get("topic", ""),
                    # ESG metadata
                    "frameworks": esg_meta.get("frameworks", []),
                    "emission_scopes": esg_meta.get("emission_scopes", []),
                    "greenhouse_gases": esg_meta.get("greenhouse_gases", []),
                    "regulator": esg_meta.get("regulator", ""),
                }
            )

        return formatted_results

    def search_with_location_and_filters(
        self,
        query: str,
        lga_code: Optional[str] = None,
        state: Optional[str] = None,
        jurisdiction: Optional[str] = None,
        category: Optional[str] = None,
        topic: Optional[str] = None,
        k: int = 10,
    ) -> list[dict]:
        """Advanced search with both spatial and metadata filters.

        Args:
            query: User query string
            lga_code: Optional LGA code for spatial filtering
            state: Optional state code for spatial filtering
            jurisdiction: Optional jurisdiction filter (federal/state/local)
            category: Optional category filter (environment/planning/etc.)
            topic: Optional topic filter
            k: Number of results

        Returns:
            List of formatted results
        """
        spatial_query = None
        if lga_code or state:
            spatial_query = SpatialQuery(
                location_name="",
                lga_codes=[lga_code] if lga_code else [],
                state=state,
            )

        metadata_filters = {}
        if jurisdiction:
            metadata_filters["jurisdiction"] = jurisdiction
        if category:
            metadata_filters["category"] = category
        if topic:
            metadata_filters["topic"] = topic

        results = self.hybrid_search.search(
            query=query,
            spatial_query=spatial_query,
            metadata_filters=metadata_filters or None,
            k=k,
        )

        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append(
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "title": doc.metadata.get("title", "Untitled"),
                    "source_url": doc.metadata.get("source_url", ""),
                }
            )

        return formatted_results

    def search_with_enhanced_citations(
        self,
        query: str,
        spatial_query: Optional[SpatialQuery] = None,
        metadata_filters: Optional[dict] = None,
        k: int = 10,
    ) -> dict:
        """Search with enhanced citations and hierarchical section paths.

        Returns formatted response with inline citations, deep links to
        specific PDF pages/sections, and hierarchical breadcrumbs.

        Args:
            query: User query string
            spatial_query: Optional spatial filtering
            metadata_filters: Optional metadata filtering
            k: Number of results

        Returns:
            Dict with answer, citations, and hierarchical context
        """
        # Perform hybrid search
        results = self.hybrid_search.search(
            query=query,
            spatial_query=spatial_query,
            metadata_filters=metadata_filters,
            k=k,
        )

        # Format with hierarchical context
        hierarchical_sources = ResponseFormatter.format_with_hierarchical_context(
            results
        )

        return {
            "query": query,
            "sources": hierarchical_sources,
            "source_count": len(results),
        }


# Example Streamlit integration
"""
# In your Streamlit app (e.g., app/main.py or app/map_page.py):

import streamlit as st
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.vector_store import VectorStore
from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch
from green_gov_rag.app.hybrid_rag_handler import GeospatialRAGHandler

# Initialize components (do this once, cache if possible)
@st.cache_resource
def init_geospatial_rag():
    embeddings = ChunkEmbedder().embedder
    vector_store = VectorStore(embeddings=embeddings, index_path="data/faiss_index")
    hybrid_search = HybridGeospatialSearch(vector_store)
    return GeospatialRAGHandler(hybrid_search)

# In your app
geo_rag = init_geospatial_rag()

# Display map
from green_gov_rag.app.map import create_map
from streamlit_folium import st_folium

st.write("## GreenGovRAG - Interactive Map")
map_obj = create_map()
map_data = st_folium(map_obj, width=700, height=500)

# Handle LGA click
if map_data and map_data.get("last_object_clicked"):
    clicked_lga = map_data["last_object_clicked"]

    if "properties" in clicked_lga:
        lga_props = clicked_lga["properties"]
        lga_name = lga_props.get("LGA_NAME", "Unknown LGA")

        st.write(f"### Selected: {lga_name}")

        # User question input
        user_question = st.text_input(
            "Ask a question about this LGA:",
            placeholder="What are the tree preservation rules?"
        )

        if user_question:
            with st.spinner("Searching policies..."):
                results = geo_rag.handle_lga_click(
                    lga_properties=lga_props,
                    user_question=user_question,
                    k=5
                )

            # Display results
            st.write(f"### Results ({len(results)} documents)")

            for i, result in enumerate(results, 1):
                with st.expander(f"{i}. {result['title']} ({result['spatial_scope']})"):
                    st.write(result['content'])
                    st.write(f"**Jurisdiction:** {result['jurisdiction']}")
                    if result['source_url']:
                        st.write(f"[Source]({result['source_url']})")

# Alternative: Advanced search with filters
st.write("## Advanced Search")

col1, col2, col3 = st.columns(3)
with col1:
    jurisdiction = st.selectbox("Jurisdiction", ["All", "federal", "state", "local"])
with col2:
    category = st.selectbox("Category", ["All", "environment", "planning", "legislation"])
with col3:
    topic = st.selectbox("Topic", ["All", "emissions_reporting", "biodiversity", "tree_management"])

search_query = st.text_input("Search query:", placeholder="NGER reporting requirements")

if search_query:
    results = geo_rag.search_with_location_and_filters(
        query=search_query,
        jurisdiction=None if jurisdiction == "All" else jurisdiction,
        category=None if category == "All" else category,
        topic=None if topic == "All" else topic,
        k=10
    )

    for result in results:
        st.write(f"**{result['title']}**")
        st.write(result['content'][:200] + "...")
        st.write("---")

# ESG-Specific Search Tab
st.write("## ESG / NGER Emissions Search")

col1, col2, col3 = st.columns(3)
with col1:
    frameworks = st.multiselect(
        "Frameworks",
        ["NGER", "ISSB", "GHG_Protocol", "GRI"],
        default=[]
    )
with col2:
    emission_scopes = st.multiselect(
        "Emission Scopes",
        ["scope_1", "scope_2", "scope_3"],
        default=[]
    )
with col3:
    greenhouse_gases = st.multiselect(
        "Greenhouse Gases",
        ["CO2", "CH4", "N2O", "SF6", "HFCs", "PFCs", "NF3"],
        default=[]
    )

col4, col5 = st.columns(2)
with col4:
    consolidation_method = st.selectbox(
        "Consolidation Method",
        ["All", "operational_control", "equity_share", "financial_control"]
    )
with col5:
    regulator = st.selectbox(
        "Regulator",
        ["All", "Clean Energy Regulator", "NSW EPA", "Victorian EPA"]
    )

esg_query = st.text_input("ESG Query:", placeholder="What are Scope 2 calculation methods?")

if esg_query:
    with st.spinner("Searching ESG documents..."):
        esg_results = geo_rag.search_with_esg_filters(
            query=esg_query,
            frameworks=frameworks if frameworks else None,
            emission_scopes=emission_scopes if emission_scopes else None,
            greenhouse_gases=greenhouse_gases if greenhouse_gases else None,
            consolidation_method=None if consolidation_method == "All" else consolidation_method,
            regulator=None if regulator == "All" else regulator,
            k=10
        )

    st.write(f"### ESG Results ({len(esg_results)} documents)")

    for i, result in enumerate(esg_results, 1):
        with st.expander(f"{i}. {result['title']}"):
            st.write(result['content'])

            # Display ESG metadata
            if result.get('frameworks'):
                st.write(f"**Frameworks:** {', '.join(result['frameworks'])}")
            if result.get('emission_scopes'):
                st.write(f"**Emission Scopes:** {', '.join(result['emission_scopes'])}")
            if result.get('greenhouse_gases'):
                st.write(f"**Greenhouse Gases:** {', '.join(result['greenhouse_gases'][:5])}...")
            if result.get('regulator'):
                st.write(f"**Regulator:** {result['regulator']}")

            if result['source_url']:
                st.write(f"[Source]({result['source_url']})")

# Scope 3 Emissions Search Tab
st.write("## Scope 3 Emissions Search")

col1, col2 = st.columns(2)
with col1:
    scope_type = st.selectbox(
        "Scope Type",
        ["All Categories", "Upstream (1-8)", "Downstream (9-15)"]
    )
with col2:
    scope_3_frameworks = st.multiselect(
        "Frameworks",
        ["ISSB", "GHG_Protocol", "GRI"],
        default=["ISSB"]
    )

# Specific category selection (optional, if not using scope_type)
scope_3_categories = st.multiselect(
    "Specific Scope 3 Categories (optional)",
    [
        "purchased_goods_services",      # Cat 1
        "capital_goods",                 # Cat 2
        "fuel_energy_activities",        # Cat 3
        "upstream_transport",            # Cat 4
        "waste_generated",               # Cat 5
        "business_travel",               # Cat 6
        "employee_commuting",            # Cat 7
        "upstream_leased_assets",        # Cat 8
        "downstream_transport",          # Cat 9
        "processing_sold_products",      # Cat 10
        "use_of_sold_products",          # Cat 11
        "end_of_life_treatment",         # Cat 12
        "downstream_leased_assets",      # Cat 13
        "franchises",                    # Cat 14
        "investments",                   # Cat 15
    ],
    default=[]
)

scope_3_query = st.text_input(
    "Scope 3 Query:",
    placeholder="What are upstream transport emission calculation methods?"
)

if scope_3_query:
    with st.spinner("Searching Scope 3 guidance..."):
        # Determine scope type parameter
        scope_type_param = None
        if scope_type == "Upstream (1-8)":
            scope_type_param = "upstream"
        elif scope_type == "Downstream (9-15)":
            scope_type_param = "downstream"

        scope_3_results = geo_rag.search_scope_3(
            query=scope_3_query,
            scope_3_categories=scope_3_categories if scope_3_categories else None,
            scope_type=scope_type_param,
            frameworks=scope_3_frameworks if scope_3_frameworks else None,
            k=10
        )

    st.write(f"### Scope 3 Results ({len(scope_3_results)} documents)")

    for i, result in enumerate(scope_3_results, 1):
        with st.expander(f"{i}. {result['title']}"):
            st.write(result['content'])

            # Display Scope 3 specific metadata
            esg_meta = result.get('metadata', {}).get('esg_metadata', {})

            if esg_meta.get('scope_3_categories'):
                st.write(f"**Scope 3 Categories:** {', '.join(esg_meta['scope_3_categories'])}")

            if result.get('frameworks'):
                st.write(f"**Frameworks:** {', '.join(result['frameworks'])}")

            if esg_meta.get('measurement_standard'):
                st.write(f"**Measurement Standard:** {esg_meta['measurement_standard']}")

            if result['source_url']:
                st.write(f"[Source]({result['source_url']})")
"""

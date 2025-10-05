#!/usr/bin/env python3
"""Example: Named Entity Recognition for Location Extraction.

This script demonstrates how to use the LocationNER module to automatically
extract Australian locations (states, LGAs) from text queries and use them
for geospatial filtering in search.
"""

from green_gov_rag.rag.location_ner import LocationNER, QueryLocationProcessor


def example_1_basic_ner():
    """Example 1: Basic location extraction."""
    print("=" * 70)
    print("Example 1: Basic Location Extraction")
    print("=" * 70)

    # Initialize NER (rule-based only for this example)
    ner = LocationNER(use_llm=False)

    # Test queries
    test_queries = [
        "What are the tree preservation rules in Adelaide?",
        "Show me emissions reporting requirements for Port Adelaide Enfield",
        "What are the planning policies in South Australia?",
        "Tell me about biodiversity offsets in Sydney",
        "What are the NGER requirements in Victoria?",
        "Development rules in Norwood Payneham and St Peters",
        "Tree management in the City of Unley",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")

        locations = ner.extract_locations(query)

        print(f"  States: {locations['states']}")
        print(f"  LGAs: {[lga['name'] for lga in locations['lgas']]}")
        print(f"  LGA Codes: {[lga['code'] for lga in locations['lgas']]}")


def example_2_query_processor():
    """Example 2: Query processing with location enrichment."""
    print("\n" + "=" * 70)
    print("Example 2: Query Location Processor")
    print("=" * 70)

    # Initialize processor
    processor = QueryLocationProcessor()

    # Process queries
    queries = [
        "What are the tree rules in Adelaide, South Australia?",
        "Emission reporting for coal mines in NSW",
        "Urban planning in Port Adelaide Enfield",
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        result = processor.process_query(query)

        print(f"  Has location: {result['has_location']}")
        print(f"  LGA codes: {result['lga_codes']}")
        print(f"  State codes: {result['state_codes']}")
        print(f"  Raw locations: {result['locations']['raw_locations']}")


def example_3_hybrid_search_integration():
    """Example 3: Integration with HybridGeospatialSearch."""
    print("\n" + "=" * 70)
    print("Example 3: Hybrid Search with Auto-Location")
    print("=" * 70)

    from green_gov_rag.rag.embeddings import ChunkEmbedder
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch
    from green_gov_rag.rag.vector_store import VectorStore

    # Sample chunks with spatial metadata
    chunks = [
        {
            "content": "NGER requires reporting of CO2, CH4, N2O emissions from facilities exceeding 25,000 tonnes CO2-e.",
            "metadata": {
                "title": "CER NGER Guideline",
                "spatial_scope": "federal",
                "jurisdiction": "federal",
                "esg_metadata": {
                    "frameworks": ["NGER"],
                    "emission_scopes": ["scope_1"],
                    "greenhouse_gases": ["CO2", "CH4", "N2O"],
                },
            },
        },
        {
            "content": "Adelaide Park Lands are protected heritage areas requiring special approval for any development.",
            "metadata": {
                "title": "City of Adelaide Park Lands Guidelines",
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": ["40070"],
                "lga_names": ["City of Adelaide"],
                "jurisdiction": "local",
            },
        },
        {
            "content": "Port Adelaide Enfield has specific emission reporting requirements for industrial facilities.",
            "metadata": {
                "title": "Port Adelaide Enfield Industrial Guidelines",
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": ["40280"],
                "lga_names": ["Port Adelaide Enfield"],
                "jurisdiction": "local",
            },
        },
        {
            "content": "SA Planning and Design Code governs all development applications across South Australia.",
            "metadata": {
                "title": "SA Planning Code",
                "spatial_scope": "state",
                "state": "SA",
                "jurisdiction": "state",
            },
        },
    ]

    # Initialize embeddings and vector store
    embeddings = ChunkEmbedder().embedder
    vector_store = VectorStore(embeddings=embeddings)
    vector_store.build_store(chunks)

    # Initialize hybrid search with NER enabled
    hybrid_search = HybridGeospatialSearch(vector_store, enable_ner=True)

    # Test auto-location search
    test_queries = [
        "What are the development rules in Adelaide?",
        "Tell me about emissions in Port Adelaide Enfield",
        "What are the planning policies in South Australia?",
    ]

    for query in test_queries:
        print(f"\n--- Query: {query} ---")

        results = hybrid_search.search_with_auto_location(query=query, k=3)

        print(f"Found {len(results)} results:")
        for i, doc in enumerate(results, 1):
            print(f"  {i}. {doc.metadata.get('title')}")
            print(f"     Spatial scope: {doc.metadata.get('spatial_scope')}")
            print(f"     Content: {doc.page_content[:100]}...")


def example_4_add_custom_lga():
    """Example 4: Adding custom LGA mappings."""
    print("\n" + "=" * 70)
    print("Example 4: Adding Custom LGA Mappings")
    print("=" * 70)

    # Initialize NER
    ner = LocationNER(use_llm=False)

    # Add custom LGA (e.g., a new council)
    ner.add_lga_mapping(
        name="campbelltown",
        lga_code="40750",
        state="SA",
        official_name="City of Campbelltown",
    )

    print("Added custom LGA: City of Campbelltown")

    # Test extraction
    query = "What are the planning rules in Campbelltown?"
    locations = ner.extract_locations(query)

    print(f"\nQuery: {query}")
    print(f"LGAs found: {[lga['name'] for lga in locations['lgas']]}")
    print(f"LGA codes: {[lga['code'] for lga in locations['lgas']]}")


def example_5_convenience_methods():
    """Example 5: Using convenience methods."""
    print("\n" + "=" * 70)
    print("Example 5: Convenience Methods")
    print("=" * 70)

    ner = LocationNER(use_llm=False)

    queries = [
        "Adelaide tree preservation rules",
        "NSW emissions reporting",
        "Port Adelaide Enfield development",
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        # Extract just LGA codes
        lga_codes = ner.extract_lga_codes(query)
        print(f"  LGA codes: {lga_codes}")

        # Extract just state codes
        state_codes = ner.extract_state_codes(query)
        print(f"  State codes: {state_codes}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("GreenGovRAG - Named Entity Recognition for Locations")
    print("=" * 70)

    # Example 1: Basic extraction
    example_1_basic_ner()

    # Example 2: Query processor
    example_2_query_processor()

    # Example 3: Hybrid search integration
    example_3_hybrid_search_integration()

    # Example 4: Custom LGA mappings
    example_4_add_custom_lga()

    # Example 5: Convenience methods
    example_5_convenience_methods()

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nKey Features:")
    print("  ✓ Automatic location extraction from text queries")
    print("  ✓ Support for Australian states and LGAs")
    print("  ✓ Integration with HybridGeospatialSearch")
    print("  ✓ Custom LGA mapping support")
    print("  ✓ Query enrichment with location metadata")


if __name__ == "__main__":
    main()
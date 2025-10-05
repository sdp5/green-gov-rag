#!/usr/bin/env python3
"""Example: Enhanced GreenGovRAG Features Demo.

This script demonstrates the advanced features implemented:
1. Scope 3 category tagging (15 ISSB categories)
2. LangChain OpenAIMetadataTagger for automation
3. Enhanced citation response with deep links
4. Hierarchical section paths in responses
5. Named Entity Recognition for location extraction
"""

import json


def example_1_scope_3_tagging():
    """Example 1: Scope 3 category tagging with all 15 ISSB categories."""
    print("=" * 70)
    print("Example 1: Scope 3 Category Tagging")
    print("=" * 70)

    from langchain.docstore.document import Document

    from green_gov_rag.etl.metadata_tagger import CustomPromptTagger

    # Sample Scope 3 text
    sample_text = """
    This guidance covers Scope 3 emissions across multiple categories:

    Upstream emissions include:
    - Category 1: Purchased goods and services
    - Category 4: Upstream transportation and distribution
    - Category 6: Business travel
    - Category 7: Employee commuting

    Downstream emissions include:
    - Category 9: Downstream transportation
    - Category 11: Use of sold products
    - Category 15: Investments
    """

    # Initialize tagger
    tagger = CustomPromptTagger()

    # Extract Scope 3 categories
    print("\nExtracting Scope 3 categories from text...")
    categories = tagger.extract_scope_3_categories(sample_text)

    print(f"\nDetected {len(categories)} Scope 3 categories:")
    for cat in categories:
        print(f"  - {cat}")


def example_2_automated_metadata_tagging():
    """Example 2: Automated metadata tagging with LangChain."""
    print("\n" + "=" * 70)
    print("Example 2: Automated Metadata Tagging")
    print("=" * 70)

    from langchain.docstore.document import Document

    from green_gov_rag.etl.metadata_tagger import MetadataTagger

    # Sample NGER document
    sample_doc = Document(
        page_content="""
        The National Greenhouse and Energy Reporting (NGER) Act requires facilities
        that emit 25,000 tonnes or more of CO2-e annually to report their Scope 1
        emissions to the Clean Energy Regulator. This includes direct emissions from
        fuel combustion, fugitive methane emissions from coal mining, and other
        greenhouse gases including CH4, N2O, and SF6.
        """,
        metadata={"title": "NGER Reporting Guidelines"},
    )

    # Initialize tagger
    print("\nInitializing metadata tagger...")
    tagger = MetadataTagger(model_name="gpt-4")

    # Tag document
    print("Tagging document with ESG metadata...")
    tagged_doc = tagger.tag_document(sample_doc, include_esg=True)

    print("\nExtracted Metadata:")
    print(json.dumps(tagged_doc.metadata, indent=2, default=str))


def example_3_enhanced_citations():
    """Example 3: Enhanced citations with deep links."""
    print("\n" + "=" * 70)
    print("Example 3: Enhanced Citations with Deep Links")
    print("=" * 70)

    from langchain.docstore.document import Document

    from green_gov_rag.rag.enhanced_response import ResponseFormatter

    # Sample documents with hierarchical metadata
    sources = [
        Document(
            page_content="NGER requires reporting of Scope 1 emissions exceeding 25,000 tonnes CO2-e annually.",
            metadata={
                "title": "NGER Act Explanatory Guide",
                "source_url": "https://www.cleanenergyregulator.gov.au/nger/guide.pdf",
                "page": 15,
                "section_number": "2.1.3",
                "section_title": "Scope 1 Emissions Thresholds",
                "section_path": "Part 2: Reporting Requirements > Section 2.1: Thresholds > 2.1.3 Scope 1",
                "section_level": 3,
            },
        ),
        Document(
            page_content="Adelaide Park Lands require heritage approval for significant development.",
            metadata={
                "title": "City of Adelaide Development Plan",
                "source_url": "https://www.cityofadelaide.com.au/development-plan.pdf",
                "page": 42,
                "section_number": "3.2",
                "section_title": "Park Lands Heritage",
                "section_path": "Chapter 3: Heritage > 3.2 Park Lands Protection",
                "section_level": 2,
            },
        ),
    ]

    # Format with hierarchical context
    print("\nFormatting sources with hierarchical context...")
    formatted_sources = ResponseFormatter.format_with_hierarchical_context(sources)

    print(f"\n{len(formatted_sources)} sources formatted:")
    for source in formatted_sources:
        print(f"\n[{source['citation_number']}] {source['title']}")
        print(f"   Deep Link: {source['deep_link']}")
        print(f"   Breadcrumb: {source['breadcrumb']}")
        print(f"   Hierarchy: {source['hierarchy']['section_path']}")


def example_4_location_ner_integration():
    """Example 4: Location NER with hybrid search."""
    print("\n" + "=" * 70)
    print("Example 4: Location NER with Hybrid Search")
    print("=" * 70)

    from green_gov_rag.rag.location_ner import LocationNER

    # Initialize NER
    ner = LocationNER(use_llm=False)

    # Test queries
    test_queries = [
        "What are emission reporting rules in Port Adelaide Enfield?",
        "Tree management policies in Adelaide, South Australia",
        "NGER requirements for Victoria",
        "Development rules in Norwood Payneham and St Peters",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")

        # Extract locations
        locations = ner.extract_locations(query)

        # Display extracted information
        if locations["states"]:
            print(f"  States: {locations['states']}")
        if locations["lgas"]:
            print(f"  LGAs: {[lga['name'] for lga in locations['lgas']]}")
            print(f"  LGA Codes: {[lga['code'] for lga in locations['lgas']]}")


def example_5_full_pipeline():
    """Example 5: Full pipeline with all features."""
    print("\n" + "=" * 70)
    print("Example 5: Full Pipeline Integration")
    print("=" * 70)

    from green_gov_rag.rag.embeddings import ChunkEmbedder
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch
    from green_gov_rag.rag.vector_store import VectorStore

    # Sample chunks with complete metadata
    chunks = [
        {
            "content": "NGER requires Scope 1 emissions reporting for facilities exceeding 25,000 tonnes CO2-e.",
            "metadata": {
                "title": "CER NGER Guidelines",
                "source_url": "https://www.cleanenergyregulator.gov.au/nger.pdf",
                "page": 10,
                "section_path": "Chapter 2: Reporting > 2.1 Thresholds",
                "spatial_scope": "federal",
                "jurisdiction": "federal",
                "esg_metadata": {
                    "frameworks": ["NGER"],
                    "emission_scopes": ["scope_1"],
                    "greenhouse_gases": ["CO2", "CH4", "N2O"],
                    "regulator": "Clean Energy Regulator",
                },
            },
        },
        {
            "content": "Adelaide Park Lands development requires special heritage approval and environmental assessment.",
            "metadata": {
                "title": "City of Adelaide Development Guidelines",
                "source_url": "https://www.cityofadelaide.com.au/guidelines.pdf",
                "page": 25,
                "section_path": "Part 3: Heritage Areas > 3.2 Park Lands",
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": ["40070"],
                "jurisdiction": "local",
            },
        },
        {
            "content": "Scope 3 Category 4 covers upstream transportation of purchased goods and materials.",
            "metadata": {
                "title": "ISSB Scope 3 Standard",
                "source_url": "https://www.ifrs.org/scope3.pdf",
                "page": 52,
                "section_path": "Part 2: Upstream Categories > Section 4: Transport",
                "spatial_scope": "federal",
                "jurisdiction": "federal",
                "esg_metadata": {
                    "frameworks": ["ISSB", "GHG_Protocol"],
                    "emission_scopes": ["scope_3"],
                    "scope_3_categories": ["upstream_transport"],
                },
            },
        },
    ]

    # Initialize components
    print("\nInitializing RAG components...")
    embeddings = ChunkEmbedder().embedder
    vector_store = VectorStore(embeddings=embeddings)
    vector_store.build_store(chunks)

    hybrid_search = HybridGeospatialSearch(vector_store, enable_ner=True)

    # Test 1: Simple hybrid search
    print("\n--- Test 1: Hybrid Search with NER ---")
    query1 = "What are the development rules in Adelaide?"
    print(f"Query: {query1}")

    results1 = hybrid_search.search(query1, k=2)
    print(f"Found {len(results1)} results")
    for result in results1:
        print(f"  - {result.get('metadata', {}).get('title', 'Unknown')} ({result.get('metadata', {}).get('spatial_scope', 'Unknown')})")

    # Test 2: Search with metadata filters
    print("\n--- Test 2: Search with Metadata Filters ---")
    query2 = "What are NGER reporting requirements?"
    print(f"Query: {query2}")

    results2 = hybrid_search.search(
        query2, frameworks=["NGER"], emission_scopes=["scope_1"], k=2
    )
    print(f"Found {len(results2)} NGER Scope 1 results")
    for result in results2:
        metadata = result.get('metadata', {})
        print(f"  - {metadata.get('title', 'Unknown')}")
        print(f"    Frameworks: {metadata.get('esg_metadata', {}).get('frameworks', [])}")

    # Test 3: Demonstration complete
    print("\n--- Pipeline Integration Complete ---")
    print("Demonstrated:")
    print("  ✓ Vector store with enhanced metadata")
    print("  ✓ Hybrid search with NER")
    print("  ✓ ESG framework filtering")
    print("  ✓ Location-aware search")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("GreenGovRAG - Enhanced Features Demonstration")
    print("=" * 70)
    print("\nDemonstrating:")
    print("  1. Scope 3 category tagging (15 ISSB categories)")
    print("  2. Automated metadata tagging with LangChain")
    print("  3. Enhanced citations with deep links")
    print("  4. Hierarchical section paths")
    print("  5. Named Entity Recognition for locations")
    print("\n")

    # Example 1: Scope 3 tagging
    # Note: Requires OpenAI API key
    # example_1_scope_3_tagging()

    # Example 2: Automated metadata tagging
    # Note: Requires OpenAI API key
    # example_2_automated_metadata_tagging()

    # Example 3: Enhanced citations
    example_3_enhanced_citations()

    # Example 4: Location NER
    example_4_location_ner_integration()

    # Example 5: Full pipeline
    example_5_full_pipeline()

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nKey Features Demonstrated:")
    print("  ✓ Scope 3 category detection (15 ISSB categories)")
    print("  ✓ Automated ESG metadata extraction")
    print("  ✓ Citations with PDF deep links (#page=N)")
    print("  ✓ Hierarchical section paths and breadcrumbs")
    print("  ✓ Automatic location extraction from queries")
    print("  ✓ Hybrid search with spatial + metadata filtering")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Example: ETL Pipeline with Automated Metadata Tagging.

This script demonstrates how to use the enhanced ETL pipeline
with automated ESG/NGER metadata extraction.
"""

import json
from pathlib import Path

from langchain.docstore.document import Document

from green_gov_rag.etl.metadata_tagger import ESGOpenAITagger
from green_gov_rag.etl.pipeline import EnhancedETLPipeline, process_pdf_with_tagging


def example_1_full_pipeline():
    """Example 1: Run full ETL pipeline with auto-tagging."""
    print("=" * 70)
    print("Example 1: Full ETL Pipeline with Auto-Tagging")
    print("=" * 70)

    # Initialize pipeline with auto-tagging enabled
    pipeline = EnhancedETLPipeline(
        enable_auto_tagging=True,  # Enable auto-tagging
        chunk_size=1000,
        chunk_overlap=100,
    )

    # Run pipeline
    chunks = pipeline.run(
        config_path="configs/documents_config.yml",
        output_path="data/processed/auto_tagged_chunks.json",
    )

    # Display sample chunk with metadata
    if chunks:
        sample = chunks[0]
        print(f"\nSample chunk metadata:")
        print(json.dumps(sample["metadata"], indent=2))


def example_2_manual_tagging():
    """Example 2: Manually tag specific documents."""
    print("\n" + "=" * 70)
    print("Example 2: Manual Document Tagging")
    print("=" * 70)

    # Create sample documents
    documents = [
        Document(
            page_content="""
            This guideline covers Scope 1 emissions from coal mining operations,
            including fugitive methane (CH4) and carbon dioxide (CO2) emissions.
            Facilities exceeding 25,000 tonnes CO2-e annually must report under NGER.
            The Clean Energy Regulator enforces these requirements.
            """,
            metadata={"title": "NGER Coal Mining Guideline", "jurisdiction": "federal"},
        ),
        Document(
            page_content="""
            ISSB requires disclosure of Scope 3 emissions across all 15 categories.
            This includes upstream transport (Category 4), business travel (Category 6),
            and employee commuting (Category 7). Companies must use equity share
            or operational control consolidation approaches.
            """,
            metadata={"title": "ISSB Scope 3 Requirements", "jurisdiction": "federal"},
        ),
    ]

    # Initialize tagger
    tagger = ESGOpenAITagger()

    # Tag documents
    print("\nTagging documents with ESG metadata...")
    tagged_docs = tagger.tag_all(documents)

    # Display results
    for i, doc in enumerate(tagged_docs, 1):
        print(f"\nDocument {i}: {doc.metadata.get('title')}")
        print("ESG Metadata:")

        # Extract ESG metadata
        esg_meta = doc.metadata

        if "emission_scope" in esg_meta:
            print(f"  - Emission Scope: {esg_meta['emission_scope']}")

        if "scope_3_categories" in esg_meta:
            print(f"  - Scope 3 Categories: {esg_meta['scope_3_categories']}")

        if "greenhouse_gases" in esg_meta:
            print(f"  - Greenhouse Gases: {esg_meta['greenhouse_gases']}")

        if "frameworks" in esg_meta:
            print(f"  - Frameworks: {esg_meta['frameworks']}")

        if "regulatory_authority" in esg_meta:
            print(f"  - Regulatory Authority: {esg_meta['regulatory_authority']}")


def example_3_single_pdf_processing():
    """Example 3: Process single PDF with auto-tagging."""
    print("\n" + "=" * 70)
    print("Example 3: Single PDF Processing with Auto-Tagging")
    print("=" * 70)

    # Define base metadata from documents_config.yml
    base_metadata = {
        "title": "Clean Energy Regulator - Scope 1 Coal Mining Guideline",
        "jurisdiction": "federal",
        "category": "environment",
        "topic": "emissions_reporting",
        "esg_metadata": {
            "frameworks": ["NGER", "GHG_Protocol"],
            "emission_scopes": ["scope_1"],
            "greenhouse_gases": ["CO2", "CH4", "N2O"],
            "regulator": "Clean Energy Regulator",
        },
    }

    # Note: This is a hypothetical example
    # In practice, you'd provide an actual PDF path
    pdf_path = "data/raw/federal/environment/emissions_reporting/nger_coal_mining.pdf"

    if Path(pdf_path).exists():
        print(f"\nProcessing PDF: {pdf_path}")

        # Process with auto-tagging
        chunks = process_pdf_with_tagging(
            pdf_path=pdf_path, base_metadata=base_metadata, auto_tag=True
        )

        print(f"Created {len(chunks)} chunks with enriched metadata")

        # Show sample
        if chunks:
            sample = chunks[0]
            print(f"\nSample chunk:")
            print(f"Content: {sample['content'][:200]}...")
            print(f"Metadata: {json.dumps(sample['metadata'], indent=2)}")
    else:
        print(f"\nPDF not found: {pdf_path}")
        print("Skipping PDF processing example")


def example_4_config_based_tagging():
    """Example 4: Load config and enrich with auto-tagging."""
    print("\n" + "=" * 70)
    print("Example 4: Config-Based Auto-Tagging")
    print("=" * 70)

    from green_gov_rag.etl.loader import load_documents_config

    # Load documents from config
    docs = load_documents_config("configs/documents_config.yml")

    # Filter for NGER documents
    nger_docs = [doc for doc in docs if "NGER" in doc.get("esg_metadata", {}).get("frameworks", [])]

    print(f"\nFound {len(nger_docs)} NGER documents in config")

    # Create Document objects with config metadata
    documents = []
    for doc in nger_docs[:3]:  # Process first 3 for demo
        documents.append(
            Document(
                page_content=f"Sample content from {doc.get('title')}",
                metadata={
                    "title": doc.get("title"),
                    "jurisdiction": doc.get("jurisdiction"),
                    "esg_metadata": doc.get("esg_metadata", {}),
                },
            )
        )

    # Auto-tag to enrich metadata
    tagger = ESGOpenAITagger()
    tagged_docs = tagger.tag_all(documents)

    print(f"\nEnriched {len(tagged_docs)} documents with auto-tagging")

    # Compare original vs enriched
    for i, (original, tagged) in enumerate(zip(docs[:3], tagged_docs), 1):
        print(f"\nDocument {i}: {original.get('title')}")
        print(f"  Original frameworks: {original.get('esg_metadata', {}).get('frameworks', [])}")
        print(f"  Enriched metadata keys: {list(tagged.metadata.keys())}")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("GreenGovRAG - ETL Pipeline with Auto-Tagging Examples")
    print("=" * 70)

    # Example 1: Full pipeline
    # example_1_full_pipeline()

    # Example 2: Manual tagging
    example_2_manual_tagging()

    # Example 3: Single PDF
    example_3_single_pdf_processing()

    # Example 4: Config-based
    example_4_config_based_tagging()

    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
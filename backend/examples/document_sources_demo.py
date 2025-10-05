#!/usr/bin/env python3
"""Demonstration of the document source plugin architecture.

This example shows how to use the new plugin-based system for loading
and processing government documents.
"""

from green_gov_rag.etl.loader import (
    get_document_sources_by_jurisdiction,
    get_document_sources_by_type,
    load_document_sources,
)


def demo_basic_loading():
    """Demo: Basic document loading."""
    print("=" * 80)
    print("DEMO 1: Basic Document Loading")
    print("=" * 80)

    sources = load_document_sources()
    print(f"\n✅ Loaded {len(sources)} document sources")

    # Show first 3 sources
    for i, source in enumerate(sources[:3], 1):
        metadata = source.get_metadata()
        print(f"\n{i}. {metadata.get('title', 'Unknown')}")
        print(f"   Type: {source.get_source_type()}")
        print(f"   Jurisdiction: {metadata.get('jurisdiction')}")
        print(f"   Category: {metadata.get('category')}")


def demo_validation():
    """Demo: Validating document configurations."""
    print("\n" + "=" * 80)
    print("DEMO 2: Document Validation")
    print("=" * 80)

    sources = load_document_sources()

    valid_count = 0
    invalid_count = 0
    warnings_count = 0

    for source in sources:
        validation = source.validate()

        if validation.is_valid:
            valid_count += 1
            if validation.warnings:
                warnings_count += 1
        else:
            invalid_count += 1
            metadata = source.get_metadata()
            print(f"\n❌ INVALID: {metadata.get('title', 'Unknown')}")
            for error in validation.errors:
                print(f"   Error: {error}")

    print(f"\n📊 Validation Summary:")
    print(f"   ✅ Valid: {valid_count}")
    print(f"   ⚠️  Valid with warnings: {warnings_count}")
    print(f"   ❌ Invalid: {invalid_count}")


def demo_filter_by_type():
    """Demo: Filter documents by source type."""
    print("\n" + "=" * 80)
    print("DEMO 3: Filter by Source Type")
    print("=" * 80)

    # Get federal legislation
    federal_sources = get_document_sources_by_type("federal_legislation")
    print(f"\n📜 Federal Legislation Sources: {len(federal_sources)}")
    for source in federal_sources[:3]:
        metadata = source.get_metadata()
        print(f"   • {metadata.get('title')}")

    # Get emissions reporting
    emissions_sources = get_document_sources_by_type("emissions_reporting")
    print(f"\n🌍 Emissions Reporting Sources: {len(emissions_sources)}")
    for source in emissions_sources[:3]:
        metadata = source.get_metadata()
        esg = source.get_esg_metadata() if hasattr(source, "get_esg_metadata") else {}
        scopes = esg.get("emission_scopes", [])
        print(f"   • {metadata.get('title')}")
        if scopes:
            print(f"     Scopes: {', '.join(scopes)}")

    # Get local government
    local_sources = get_document_sources_by_type("local_government")
    print(f"\n🏛️  Local Government Sources: {len(local_sources)}")
    for source in local_sources[:3]:
        metadata = source.get_metadata()
        lga_names = source.get_lga_names() if hasattr(source, "get_lga_names") else []
        print(f"   • {metadata.get('title')}")
        if lga_names:
            print(f"     LGAs: {', '.join(lga_names)}")


def demo_filter_by_jurisdiction():
    """Demo: Filter documents by jurisdiction."""
    print("\n" + "=" * 80)
    print("DEMO 4: Filter by Jurisdiction")
    print("=" * 80)

    for jurisdiction in ["federal", "state", "local"]:
        sources = get_document_sources_by_jurisdiction(jurisdiction)
        print(f"\n{jurisdiction.upper()} documents: {len(sources)}")


def demo_download_urls():
    """Demo: Extract download URLs."""
    print("\n" + "=" * 80)
    print("DEMO 5: Extract Download URLs")
    print("=" * 80)

    sources = load_document_sources()

    total_urls = 0
    for source in sources[:5]:
        metadata = source.get_metadata()
        urls = source.get_download_urls()
        if urls:
            print(f"\n📥 {metadata.get('title', 'Unknown')}")
            for url in urls[:2]:  # Show first 2 URLs
                print(f"   • {url}")
            if len(urls) > 2:
                print(f"   ... and {len(urls) - 2} more")
            total_urls += len(urls)

    print(f"\n📊 Total download URLs: {total_urls}")


def demo_scope_3_analysis():
    """Demo: Analyze Scope 3 emissions documents."""
    print("\n" + "=" * 80)
    print("DEMO 6: Scope 3 Emissions Analysis")
    print("=" * 80)

    emissions_sources = get_document_sources_by_type("emissions_reporting")

    scope_3_docs = []
    for source in emissions_sources:
        if hasattr(source, "get_emission_scopes"):
            scopes = source.get_emission_scopes()
            if "scope_3" in scopes:
                scope_3_docs.append(source)

    print(f"\n🌍 Found {len(scope_3_docs)} Scope 3 documents")

    for source in scope_3_docs:
        metadata = source.get_metadata()
        categories = source.get_scope_3_categories()
        print(f"\n📄 {metadata.get('title')}")
        if categories:
            print(f"   Categories covered: {len(categories)}")
            print(f"   {', '.join(categories[:3])}" + (", ..." if len(categories) > 3 else ""))


def demo_spatial_filtering():
    """Demo: Filter by spatial metadata."""
    print("\n" + "=" * 80)
    print("DEMO 7: Spatial Filtering (South Australia)")
    print("=" * 80)

    sources = load_document_sources()

    sa_sources = []
    for source in sources:
        metadata = source.get_metadata()
        spatial = metadata.get("spatial_metadata", {})

        # Check if document applies to SA
        if spatial.get("state") == "SA" or metadata.get("jurisdiction") == "federal":
            sa_sources.append(source)

    print(f"\n📍 Documents applicable to South Australia: {len(sa_sources)}")

    # Show state-level SA docs
    state_sa = [s for s in sa_sources if s.get_metadata().get("jurisdiction") == "state"]
    print(f"\n📜 SA State Documents: {len(state_sa)}")
    for source in state_sa[:3]:
        metadata = source.get_metadata()
        print(f"   • {metadata.get('title')}")

    # Show local SA docs
    local_sa = [s for s in sa_sources if s.get_metadata().get("jurisdiction") == "local"]
    print(f"\n🏛️  SA Local Government Documents: {len(local_sa)}")
    for source in local_sa[:3]:
        metadata = source.get_metadata()
        print(f"   • {metadata.get('title')}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DOCUMENT SOURCE PLUGIN DEMO" + " " * 31 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        demo_basic_loading()
        demo_validation()
        demo_filter_by_type()
        demo_filter_by_jurisdiction()
        demo_download_urls()
        demo_scope_3_analysis()
        demo_spatial_filtering()

        print("\n" + "=" * 80)
        print("✅ Demo completed successfully!")
        print("=" * 80)
        print("\nNext steps:")
        print("  • Check docs/CONTRIBUTING_DOCUMENT_SOURCES.md for contribution guide")
        print("  • Add new documents to configs/documents_config.yml")
        print("  • Create custom plugins in green_gov_rag/etl/sources/")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

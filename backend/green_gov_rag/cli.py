"""CLI commands for GreenGovRAG.

A comprehensive command-line interface for managing ETL pipelines,
RAG operations, and metadata tagging for Australian ESG/NGER documents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help="GreenGovRAG CLI: AI Assistant for Australian Environmental & Planning Regulations",
    no_args_is_help=True,
)

# Create sub-applications for better organization
etl_app = typer.Typer(
    help="ETL Pipeline: Document ingestion, parsing, and processing",
    no_args_is_help=True,
)
rag_app = typer.Typer(
    help="RAG Operations: Query, search, and retrieval",
    no_args_is_help=True,
)

app.add_typer(etl_app, name="etl")
app.add_typer(rag_app, name="rag")

console = Console()


# ============================================================================
# ETL Commands
# ============================================================================


@etl_app.command("ingest")
def etl_ingest(
    config_path: str = typer.Option(
        "configs/documents_config.yml",
        "--config",
        "-c",
        help="Path to documents configuration YAML file",
    ),
    output_dir: str = typer.Option(
        "data/raw",
        "--output",
        "-o",
        help="Output directory for downloaded documents",
    ),
) -> None:
    """Download documents listed in the configuration file.

    Fetches ESG/NGER documents from URLs specified in the config and saves
    them to the output directory with appropriate metadata.

    Example:
    -------
        green-gov-rag-cli etl ingest --config configs/my_docs.yml

    """
    from green_gov_rag.etl import ingest, loader

    console.print(f"[bold blue]Loading config from {config_path}...[/bold blue]")
    docs = loader.load_documents_config(config_path)
    console.print(f"Found {len(docs)} documents to download")

    ingest.download_documents(docs, output_dir)
    console.print(
        f"[bold green]✓ Downloaded {len(docs)} documents to {output_dir}[/bold green]",
    )


@etl_app.command("parse")
def etl_parse(
    input_dir: str = typer.Option(
        "data/raw",
        "--input",
        "-i",
        help="Directory containing raw documents",
    ),
    output_dir: str = typer.Option(
        "data/processed",
        "--output",
        "-o",
        help="Output directory for parsed text files",
    ),
    parser_type: str = typer.Option(
        "auto",
        "--parser",
        "-p",
        help="Parser type: auto, pdf, html (auto detects from extension)",
    ),
) -> None:
    """Parse PDFs and HTML files into plain text.

    Extracts text content from various document formats while preserving
    structure and metadata. Supports PDF (including layout-aware parsing)
    and HTML documents.

    Example:
    -------
        green-gov-rag-cli etl parse --input data/raw --output data/processed

    """
    from green_gov_rag.etl.parsers import get_parser

    console.print(f"[bold blue]Parsing documents from {input_dir}...[/bold blue]")

    parsed_count = 0
    for doc_file in Path(input_dir).rglob("*"):
        if doc_file.is_file() and doc_file.suffix in [".pdf", ".html", ".htm"]:
            try:
                parser = get_parser(str(doc_file))
                text = parser(str(doc_file))

                out_file = Path(output_dir) / (doc_file.stem + ".txt")
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(text, encoding="utf-8")

                parsed_count += 1
                console.print(f"  ✓ Parsed: {doc_file.name}")
            except Exception as e:
                console.print(f"  ✗ Failed to parse {doc_file.name}: {e}", style="red")

    console.print(
        f"[bold green]✓ Parsed {parsed_count} documents to {output_dir}[/bold green]",
    )


@etl_app.command("chunk")
def etl_chunk(
    input_dir: str = typer.Option(
        "data/processed",
        "--input",
        "-i",
        help="Directory containing parsed text files",
    ),
    output_dir: str = typer.Option(
        "data/chunks",
        "--output",
        "-o",
        help="Output directory for chunked documents",
    ),
    chunk_size: int = typer.Option(
        1000,
        "--chunk-size",
        "-s",
        help="Size of text chunks in characters",
    ),
    chunk_overlap: int = typer.Option(
        100,
        "--overlap",
        help="Overlap between chunks in characters",
    ),
) -> None:
    """Chunk parsed documents into smaller text segments.

    Splits documents into manageable chunks for embedding and retrieval,
    preserving context through overlapping windows.

    Example:
    -------
        green-gov-rag-cli etl chunk --chunk-size 1000 --overlap 100

    """
    from green_gov_rag.etl.chunker import TextChunker

    console.print(f"[bold blue]Chunking documents from {input_dir}...[/bold blue]")
    console.print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")

    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunked_count = 0

    for txt_file in Path(input_dir).rglob("*.txt"):
        try:
            text = txt_file.read_text(encoding="utf-8")
            chunks = chunker.chunk_text(text)

            out_file = Path(output_dir) / (txt_file.stem + "_chunks.json")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)

            chunked_count += 1
            console.print(f"  ✓ Chunked: {txt_file.name} ({len(chunks)} chunks)")
        except Exception as e:
            console.print(f"  ✗ Failed to chunk {txt_file.name}: {e}", style="red")

    console.print(
        f"[bold green]✓ Chunked {chunked_count} documents to {output_dir}[/bold green]",
    )


@etl_app.command("tag-metadata")
def etl_tag_metadata(
    input_dir: str = typer.Option(
        "data/processed",
        "--input",
        "-i",
        help="Directory containing documents to tag",
    ),
    output_dir: str = typer.Option(
        "data/tagged",
        "--output",
        "-o",
        help="Output directory for tagged documents",
    ),
    model: str = typer.Option(
        "gpt-4",
        "--model",
        "-m",
        help="LLM model for metadata extraction",
    ),
) -> None:
    """Auto-tag documents with ESG/NGER metadata using LLM.

    Automatically extracts and tags documents with relevant ESG metadata
    including emission scopes, frameworks, and regulatory information.

    Example:
    -------
        green-gov-rag-cli etl tag-metadata --model gpt-4

    """
    from green_gov_rag.etl.metadata_tagger import MetadataTagger

    console.print(f"[bold blue]Auto-tagging documents from {input_dir}...[/bold blue]")
    console.print(f"Using model: {model}")

    tagger = MetadataTagger(model_name=model)
    tagged_count = 0

    for txt_file in Path(input_dir).rglob("*.txt"):
        try:
            text = txt_file.read_text(encoding="utf-8")

            # Extract metadata
            esg_metadata = tagger.tag_esg_metadata(text[:2000])  # First 2k chars
            doc_metadata = tagger.tag_document_metadata(text[:2000])

            # Combine metadata
            combined_metadata = {
                "file": txt_file.name,
                "esg": esg_metadata,
                "document": doc_metadata,
            }

            out_file = Path(output_dir) / (txt_file.stem + "_metadata.json")
            out_file.parent.mkdir(parents=True, exist_ok=True)

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(combined_metadata, f, indent=2)

            tagged_count += 1
            console.print(f"  ✓ Tagged: {txt_file.name}")
        except Exception as e:
            console.print(f"  ✗ Failed to tag {txt_file.name}: {e}", style="red")

    console.print(
        f"[bold green]✓ Tagged {tagged_count} documents to {output_dir}[/bold green]",
    )


@etl_app.command("monitor")
def etl_monitor(
    output_format: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format: json, table, or summary",
    ),
    trigger_etl: bool = typer.Option(
        False,
        "--trigger-etl/--no-trigger",
        help="Automatically trigger ETL pipeline if changes detected",
    ),
) -> None:
    """Monitor document sources for new or updated documents.

    Checks all registered document sources for changes and reports
    discovered documents. Can optionally trigger ETL pipeline automatically.

    Example:
    -------
        greengovrag etl monitor --format table
        greengovrag etl monitor --trigger-etl

    """
    import asyncio

    from green_gov_rag.api.services.monitoring_service import MonitoringService

    console.print("[bold blue]Monitoring document sources...[/bold blue]")

    # Run monitoring service
    service = MonitoringService()
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(service.monitor_all_sources())

    # Display results based on format
    if output_format == "json":
        console.print(json.dumps(results, indent=2))
    elif output_format == "table":
        # Create summary table
        table = Table(title="Document Monitoring Results")
        table.add_column("Source", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Discovered", style="green")
        table.add_column("Updated", style="yellow")
        table.add_column("Unchanged", style="dim")
        table.add_column("Duration", style="blue")

        for source_result in results.get("source_results", []):
            table.add_row(
                source_result.get("source_type", "Unknown"),
                source_result.get("status", "unknown"),
                str(source_result.get("documents_discovered", 0)),
                str(source_result.get("documents_updated", 0)),
                str(source_result.get("documents_unchanged", 0)),
                f"{source_result.get('duration_seconds', 0):.2f}s",
            )

        console.print(table)
    else:  # summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Sources checked: {results.get('sources_checked', 0)}")
        console.print(f"  Sources failed: {results.get('sources_failed', 0)}")
        console.print(
            f"  Documents discovered: [green]{results.get('total_discovered', 0)}[/green]"
        )
        console.print(
            f"  Documents updated: [yellow]{results.get('total_updated', 0)}[/yellow]"
        )
        console.print(
            f"  Documents unchanged: [dim]{results.get('total_unchanged', 0)}[/dim]"
        )

    # Check if changes detected
    total_changes = results.get("total_discovered", 0) + results.get("total_updated", 0)

    if total_changes > 0:
        console.print(
            f"\n[bold green]✓ Found {total_changes} document changes[/bold green]"
        )

        if trigger_etl:
            console.print("\n[bold blue]Triggering ETL pipeline...[/bold blue]")
            # Import and run the pipeline command
            from green_gov_rag.etl.pipeline import EnhancedETLPipeline

            pipeline = EnhancedETLPipeline(enable_auto_tagging=True)
            config_path = "configs/documents_config.yml"

            console.print("Step 1: Loading and parsing documents...")
            documents = pipeline.load_and_parse_documents(config_path)
            console.print(f"  ✓ Loaded {len(documents)} documents")

            console.print("Step 2: Auto-tagging with ESG metadata...")
            documents = pipeline.auto_tag_documents(documents)
            console.print(f"  ✓ Tagged {len(documents)} documents")

            console.print("Step 3: Chunking documents...")
            chunks = pipeline.chunk_documents(documents)
            console.print(f"  ✓ Created {len(chunks)} chunks")

            console.print("[bold green]✓ ETL Pipeline completed![/bold green]")
        else:
            console.print(
                "\n[dim]Tip: Use --trigger-etl to automatically run ETL pipeline[/dim]"
            )
    else:
        console.print("\n[dim]No changes detected[/dim]")


@etl_app.command("pipeline")
def etl_pipeline(
    config_path: str = typer.Option(
        "configs/etl_config.yml",
        "--config",
        "-c",
        help="Path to ETL pipeline configuration",
    ),
    enable_tagging: bool = typer.Option(
        True,
        "--tag/--no-tag",
        help="Enable automated metadata tagging",
    ),
) -> None:
    """Run the complete ETL pipeline end-to-end.

    Executes all ETL stages: document loading, parsing, metadata tagging,
    chunking, and embedding generation.

    Example:
    -------
        green-gov-rag-cli etl pipeline --config configs/etl_config.yml

    """
    from green_gov_rag.etl.pipeline import EnhancedETLPipeline

    console.print("[bold blue]Starting ETL pipeline...[/bold blue]")

    pipeline = EnhancedETLPipeline(enable_auto_tagging=enable_tagging)

    console.print("Step 1: Loading and parsing documents...")
    documents = pipeline.load_and_parse_documents(config_path)
    console.print(f"  ✓ Loaded {len(documents)} documents")

    if enable_tagging:
        console.print("Step 2: Auto-tagging with ESG metadata...")
        documents = pipeline.auto_tag_documents(documents)
        console.print(f"  ✓ Tagged {len(documents)} documents")

    console.print("Step 3: Chunking documents...")
    chunks = pipeline.chunk_documents(documents)
    console.print(f"  ✓ Created {len(chunks)} chunks")

    console.print("[bold green]✓ ETL Pipeline completed successfully![/bold green]")


# ============================================================================
# RAG Commands
# ============================================================================


@rag_app.command("build-index")
def rag_build_index(
    chunks_dir: str = typer.Option(
        "data/chunks",
        "--chunks",
        "-c",
        help="Directory containing chunked documents",
    ),
    index_path: str = typer.Option(
        "data/vector_store/faiss.index",
        "--output",
        "-o",
        help="Output path for vector store index",
    ),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2",
        "--model",
        "-m",
        help="Embedding model to use",
    ),
) -> None:
    """Build vector search index from document chunks.

    Creates a vector store (FAISS) from chunked documents with embeddings
    for semantic similarity search.

    Example:
    -------
        green-gov-rag-cli rag build-index --chunks data/chunks

    """
    from green_gov_rag.rag.embeddings import ChunkEmbedder
    from green_gov_rag.rag.vector_store import VectorStore

    console.print("[bold blue]Building vector search index...[/bold blue]")
    console.print(f"Embedding model: {embedding_model}")

    # Load chunks
    all_chunks = []
    for chunk_file in Path(chunks_dir).rglob("*_chunks.json"):
        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)

    console.print(f"Loaded {len(all_chunks)} chunks")

    # Create embeddings
    console.print("Generating embeddings...")
    embedder = ChunkEmbedder(provider="huggingface", model_name=embedding_model)

    # Build vector store
    console.print("Building vector store...")
    vector_store = VectorStore(embeddings=embedder.embedder)
    vector_store.build_store(all_chunks)

    # Save index
    Path(index_path).parent.mkdir(parents=True, exist_ok=True)
    vector_store.persist(index_path)

    console.print(
        f"[bold green]✓ Vector index built and saved to {index_path}[/bold green]",
    )


@rag_app.command("query")
def rag_query(
    query: str = typer.Argument(..., help="Query string to search for"),
    index_path: str = typer.Option(
        "data/vector_store/faiss.index",
        "--index",
        "-i",
        help="Path to vector store index",
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
    jurisdiction: Optional[str] = typer.Option(
        None,
        "--jurisdiction",
        "-j",
        help="Filter by jurisdiction (federal/state/local)",
    ),
    region: Optional[str] = typer.Option(
        None,
        "--region",
        "-r",
        help="Filter by region/state (e.g., SA, NSW)",
    ),
    topic: Optional[str] = typer.Option(
        None,
        "--topic",
        "-t",
        help="Filter by topic (e.g., emissions_reporting)",
    ),
) -> None:
    """Query the RAG system with semantic search.

    Performs hybrid search combining vector similarity with metadata filtering
    for precise, context-aware document retrieval.

    Example:
    -------
        green-gov-rag-cli rag query "What are NGER reporting requirements?" --region SA

    """
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch
    from green_gov_rag.rag.vector_store import VectorStore

    console.print(f"[bold blue]Searching for:[/bold blue] {query}")

    # Initialize embeddings and load vector store
    from green_gov_rag.rag.embeddings import ChunkEmbedder

    embedder = ChunkEmbedder(provider="huggingface")
    vector_store = VectorStore(embeddings=embedder.embedder, index_path=index_path)

    # Build metadata filters
    metadata_filters = {}
    if jurisdiction:
        metadata_filters["jurisdiction"] = jurisdiction
    if region:
        metadata_filters["region"] = region
    if topic:
        metadata_filters["topic"] = topic

    # Perform search
    search_engine = HybridGeospatialSearch(vector_store)
    results = search_engine.search(
        query=query,
        metadata_filters=metadata_filters or None,
        k=top_k,
    )

    # Display results
    console.print(f"\n[bold green]Found {len(results)} results:[/bold green]\n")

    for i, doc in enumerate(results, 1):
        console.print(f"[bold cyan]Result {i}:[/bold cyan]")
        console.print(f"  Content: {doc.page_content[:200]}...")
        console.print(f"  Metadata: {doc.metadata}")
        console.print()


@rag_app.command("geospatial-search")
def rag_geospatial_search(
    query: str = typer.Argument(..., help="Query string to search for"),
    location: str = typer.Option(
        ...,
        "--location",
        "-l",
        help="Location name (e.g., 'Adelaide', 'Port Adelaide')",
    ),
    index_path: str = typer.Option(
        "data/vector_store/faiss.index",
        "--index",
        "-i",
        help="Path to vector store index",
    ),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results to return"),
) -> None:
    """Perform geospatial search with location-based filtering.

    Combines semantic search with automatic location extraction and
    hierarchical spatial filtering (federal → state → local).

    Example:
    -------
        green-gov-rag-cli rag geospatial-search "tree preservation rules" --location Adelaide

    """
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch, SpatialQuery
    from green_gov_rag.rag.location_ner import LocationNER
    from green_gov_rag.rag.vector_store import VectorStore

    console.print(f"[bold blue]Geospatial search:[/bold blue] {query}")
    console.print(f"[bold blue]Location:[/bold blue] {location}")

    # Extract location information
    ner = LocationNER(use_llm=False)
    locations = ner.extract_locations(location)

    console.print(f"Detected LGAs: {[lga['name'] for lga in locations['lgas']]}")
    console.print(f"Detected States: {locations['states']}")

    # Create spatial query
    if locations["lgas"]:
        lga_codes = [lga["code"] for lga in locations["lgas"]]
        state = locations["lgas"][0]["state"] if locations["lgas"] else None
        spatial_query = SpatialQuery(
            location_name=location,
            lga_codes=lga_codes,
            state=state,
        )
    else:
        console.print("[yellow]⚠ No LGA codes found for location[/yellow]")
        spatial_query = None

    # Load vector store and search
    from green_gov_rag.rag.embeddings import ChunkEmbedder

    embedder = ChunkEmbedder(provider="huggingface")
    vector_store = VectorStore(embeddings=embedder.embedder, index_path=index_path)

    search_engine = HybridGeospatialSearch(vector_store)
    results = search_engine.search(
        query=query,
        spatial_query=spatial_query,
        k=top_k,
    )

    # Display results
    console.print(f"\n[bold green]Found {len(results)} results:[/bold green]\n")

    for i, doc in enumerate(results, 1):
        console.print(f"[bold cyan]Result {i}:[/bold cyan]")
        console.print(f"  Content: {doc.page_content[:200]}...")
        console.print(f"  Region: {doc.metadata.get('region', 'N/A')}")
        console.print(f"  Jurisdiction: {doc.metadata.get('jurisdiction', 'N/A')}")
        console.print()


@rag_app.command("list-locations")
def rag_list_locations() -> None:
    """List all known LGA (Local Government Area) locations.

    Displays the built-in database of Australian LGAs with their codes
    and state assignments.

    Example:
    -------
        green-gov-rag-cli rag list-locations

    """
    from green_gov_rag.types import get_lga_mappings

    lga_mappings = get_lga_mappings()

    console.print("[bold blue]Known LGA Locations:[/bold blue]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("LGA Name", style="cyan")
    table.add_column("Official Name", style="green")
    table.add_column("LGA Code", style="yellow")
    table.add_column("State", style="blue")

    for lga_name, lga_info in sorted(lga_mappings.items()):
        table.add_row(
            lga_name,
            lga_info.name,
            lga_info.code,
            lga_info.state.value,
        )

    console.print(table)
    console.print(f"\n[bold green]Total: {len(lga_mappings)} LGA entries[/bold green]")


# ============================================================================
# Utility Commands
# ============================================================================


@app.command("version")
def show_version() -> None:
    """Display GreenGovRAG version information."""
    try:
        from green_gov_rag._version import version

        console.print(f"[bold green]GreenGovRAG version {version}[/bold green]")
    except ImportError:
        console.print("[yellow]Version information not available[/yellow]")


@app.command("info")
def show_info() -> None:
    """Display system information and available commands."""
    console.print(
        "[bold cyan]GreenGovRAG - AI Assistant for Australian Environmental & "
        "Planning Regulations[/bold cyan]\n",
    )

    console.print("[bold]Available command groups:[/bold]")
    console.print("  • [cyan]etl[/cyan]  - ETL Pipeline operations")
    console.print("  • [cyan]rag[/cyan]  - RAG query and search operations\n")

    console.print("[bold]Quick start:[/bold]")
    console.print("  1. green-gov-rag-cli etl ingest")
    console.print("  2. green-gov-rag-cli etl parse")
    console.print("  3. green-gov-rag-cli rag build-index")
    console.print("  4. green-gov-rag-cli rag query 'your question here'\n")

    console.print("Use --help with any command for more details")


if __name__ == "__main__":
    app()

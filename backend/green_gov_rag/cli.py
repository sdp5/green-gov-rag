"""CLI commands for GreenGovRAG.

A comprehensive command-line interface for managing ETL pipelines,
RAG operations, and metadata tagging for Australian ESG/NGER documents.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from sqlmodel import Session, select

# Import all required modules at the top
from green_gov_rag.api.services.monitoring_service import MonitoringService
from green_gov_rag.config import settings
from green_gov_rag.etl import ingest
from green_gov_rag.etl.chunker import TextChunker
from green_gov_rag.etl.db_writer import (
    save_chunk,
    save_document_file,
    save_document_source,
    save_document_version,
    update_document_file_status,
    update_document_source_status,
)
from green_gov_rag.etl.metadata_tagger import MetadataTagger
from green_gov_rag.etl.parsers import parse_file
from green_gov_rag.etl.parsers.layout_parser import HierarchicalPDFParser
from green_gov_rag.etl.parsers.unstructured_parser import UnstructuredPDFParser
from green_gov_rag.etl.pipeline import EnhancedETLPipeline
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter
from green_gov_rag.models.base import engine
from green_gov_rag.models.document_version import DocumentVersion
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch, SpatialQuery
from green_gov_rag.rag.location_ner import LocationNER
from green_gov_rag.rag.vector_store import VectorStore
from green_gov_rag.rag.vector_store_factory import create_vector_store
from green_gov_rag.types import PDFParserStrategy, get_lga_mappings

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
db_app = typer.Typer(
    help="Database Operations: Load and manage documents and chunks",
    no_args_is_help=True,
)

app.add_typer(etl_app, name="etl")
app.add_typer(rag_app, name="rag")
app.add_typer(db_app, name="db")

console = Console()


# ============================================================================
# Helper Functions
# ============================================================================


def _use_cloud_storage() -> bool:
    """Determine if cloud storage should be used based on settings.

    Returns:
        True if cloud storage is configured (not 'local'), False otherwise.
    """
    return settings.cloud_provider != "local"


def _get_storage_adapter() -> "ETLStorageAdapter | None":
    """Get ETL storage adapter if cloud storage is enabled.

    Returns:
        ETLStorageAdapter instance if cloud enabled, None for local mode.
    """
    if _use_cloud_storage():
        from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

        return ETLStorageAdapter()
    return None


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
) -> None:
    """Download documents listed in the configuration file.

    Fetches ESG/NGER documents from URLs specified in the config and saves
    them to a hierarchical directory structure organized by jurisdiction,
    category, and topic.

    Documents are saved to: data/raw/{jurisdiction}/{category}/{topic}/

    Example:
    -------
        greengovrag-cli etl ingest --config configs/my_docs.yml

    """
    console.print(f"[bold blue]Loading config from {config_path}...[/bold blue]")

    # Use ingest_documents() which creates hierarchical structure
    # Automatically uses cloud storage if CLOUD_PROVIDER env var is set (not 'local')
    ingest.ingest_documents(use_cloud=None, config_path=config_path)

    console.print(
        "[bold green]✓ Ingestion complete. Documents saved to configured storage.[/bold green]",
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
        greengovrag-cli etl parse --input data/raw --output data/processed

    """
    console.print(f"[bold blue]Parsing documents from {input_dir}...[/bold blue]")

    parsed_count = 0
    for doc_file in Path(input_dir).rglob("*"):
        if doc_file.is_file() and doc_file.suffix in [".pdf", ".html", ".htm"]:
            try:
                text = parse_file(str(doc_file))

                out_file = Path(output_dir) / (doc_file.stem + ".txt")
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(text, encoding="utf-8")

                # Copy metadata file if it exists
                metadata_file = doc_file.with_suffix(doc_file.suffix + ".metadata.json")
                if metadata_file.exists():
                    out_metadata = out_file.with_suffix(".metadata.json")
                    shutil.copy2(metadata_file, out_metadata)
                    console.print(f"    → Copied metadata: {metadata_file.name}")

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
        "--chunk-overlap",
        help="Overlap between chunks in characters",
    ),
    raw_dir: str = typer.Option(
        "data/raw",
        "--raw-dir",
        help="Directory containing original PDF files for citation extraction",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        "-m",
        help="Chunking mode: 'full' (process all), 'delta' (skip existing), 'auto' (use delta if output exists)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force re-chunking even if output exists (overrides delta mode)",
    ),
    use_fast_strategy: bool = typer.Option(
        True,
        "--fast/--accurate",
        help="Use fast parsing strategy (10x faster, slightly lower accuracy) vs accurate (slower, higher accuracy)",
    ),
) -> None:
    """Chunk parsed documents into smaller text segments.

    Splits documents into manageable chunks for embedding and retrieval,
    preserving context through overlapping windows. For PDFs, extracts
    citation metadata (page numbers, section hierarchy, clause references).

    Modes:
    - full: Process all files (ignores existing chunks)
    - delta: Skip files with existing chunk output
    - auto: Use delta mode by default (recommended)

    Example:
    -------
        # Fast delta processing (default, recommended)
        greengovrag-cli etl chunk

        # Full re-processing with accurate mode
        greengovrag-cli etl chunk --mode full --accurate

        # Force re-chunk specific files
        greengovrag-cli etl chunk --force

    """
    # Validate mode
    if mode not in ["full", "delta", "auto"]:
        console.print(f"[red]Error: Invalid mode '{mode}'[/red]")
        console.print("Valid modes: full, delta, auto")
        raise typer.Exit(1)

    # Determine effective mode
    effective_mode = mode
    if mode == "auto":
        effective_mode = "delta"  # Default to delta for auto mode

    if force:
        effective_mode = "full"  # Force overrides mode

    console.print(f"[bold blue]Chunking documents from {input_dir}...[/bold blue]")
    console.print(f"Chunk size: {chunk_size}, Overlap: {chunk_overlap}")
    console.print(
        f"Mode: {effective_mode}, Strategy: {'fast' if use_fast_strategy else 'accurate'}"
    )

    chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    # Initialize parser with strategy
    hierarchical_parser = HierarchicalPDFParser()
    if use_fast_strategy:
        # Pre-initialize with fast strategy
        fast_parser: UnstructuredPDFParser = UnstructuredPDFParser(
            strategy=PDFParserStrategy.FAST.value
        )
        hierarchical_parser._unstructured_parser = fast_parser

    chunked_count = 0
    skipped_count = 0

    for txt_file in Path(input_dir).rglob("*.txt"):
        try:
            # Check if output already exists (delta mode)
            out_file = Path(output_dir) / (txt_file.stem + "_chunks.json")

            if effective_mode == "delta" and out_file.exists():
                skipped_count += 1
                console.print(f"  ⊘ Skipped: {txt_file.name} (already chunked)")
                continue

            # Look for corresponding metadata file from ingestion
            metadata_file = txt_file.parent / (txt_file.stem + ".metadata.json")
            base_metadata = {}
            if metadata_file.exists():
                with open(metadata_file) as f:
                    base_metadata = json.load(f)

            # Try to find original PDF in raw directory for citation extraction
            pdf_file = None
            for pdf_path in Path(raw_dir).rglob(f"{txt_file.stem}.pdf"):
                pdf_file = pdf_path
                break

            chunks = []

            if pdf_file and pdf_file.exists() and hierarchical_parser:
                # Use hierarchical parser for PDFs to extract citation metadata
                try:
                    hierarchical_chunks = hierarchical_parser.parse_with_structure(
                        pdf_file, base_metadata=base_metadata
                    )
                    # Further chunk if needed (preserving citation metadata)
                    chunks = chunker.chunk_with_hierarchy(hierarchical_chunks)
                    console.print(
                        f"  → Extracted citation metadata from PDF: {pdf_file.name}"
                    )
                except Exception as e:
                    console.print(
                        f"  [yellow]Warning: Failed to extract citations from PDF, "
                        f"falling back to text chunking: {e}[/yellow]"
                    )
                    pdf_file = None  # Fall back to text chunking

            # Fallback: simple text chunking without citation metadata
            if not pdf_file or not chunks:
                text = txt_file.read_text(encoding="utf-8")
                text_chunks = chunker.chunk_text(text)

                for i, chunk_text in enumerate(text_chunks):
                    chunk_obj = {
                        "content": chunk_text,
                        "metadata": {
                            **base_metadata,  # Include document-level metadata
                            "chunk_index": i,  # Sequential index within document
                            "source_file": txt_file.stem,
                        },
                    }
                    chunks.append(chunk_obj)

            out_file.parent.mkdir(parents=True, exist_ok=True)

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)

            chunked_count += 1
            console.print(f"  ✓ Chunked: {txt_file.name} ({len(chunks)} chunks)")
        except Exception as e:
            console.print(f"  ✗ Failed to chunk {txt_file.name}: {e}", style="red")

    # Summary
    console.print(
        f"[bold green]✓ Chunked {chunked_count} documents to {output_dir}[/bold green]",
    )
    if skipped_count > 0:
        console.print(
            f"[dim]Delta mode: Skipped {skipped_count} already-chunked files[/dim]"
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
        "gpt-5-mini",
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
        greengovrag-cli etl tag-metadata --model gpt-5-mini

    """
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
        greengovrag-cli etl monitor --format table
        greengovrag-cli etl monitor --trigger-etl

    """
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

            # Step 4: Delete stale vectors and re-index changed documents
            # Collect changed document IDs from monitoring results
            changed_doc_ids: set[str] = set()
            for source_result in results.get("source_results", []):
                for doc in source_result.get("changed_documents", []):
                    doc_id = doc.get("document_id") or doc.get("id")
                    if doc_id:
                        changed_doc_ids.add(str(doc_id))

            # Also capture IDs reported at the top level
            for doc_id in results.get("changed_document_ids", []):
                changed_doc_ids.add(str(doc_id))

            vector_store_type = settings.vector_store_type.value
            console.print(
                f"Step 4: Updating vector index ({vector_store_type}, delta mode)..."
            )

            if vector_store_type == "faiss":
                console.print(
                    "[yellow]⚠ FAISS does not support deletion. "
                    "Run 'greengovrag-cli rag index --mode full' to rebuild the index.[/yellow]"
                )
            else:
                store_kwargs: dict = {}
                if vector_store_type == "qdrant":
                    store_kwargs["collection_name"] = "greengovrag"
                    if settings.qdrant_url:
                        store_kwargs["url"] = settings.qdrant_url
                    if settings.qdrant_api_key:
                        store_kwargs["api_key"] = settings.qdrant_api_key

                try:
                    embedder = ChunkEmbedder(
                        provider="huggingface", model_name=settings.embedding_model
                    )
                    vs = create_vector_store(
                        embeddings=embedder.embedder,
                        store_type=vector_store_type,
                        **store_kwargs,
                    )

                    if changed_doc_ids:
                        console.print(
                            f"  [dim]Deleting old vectors for {len(changed_doc_ids)} changed document(s)...[/dim]"
                        )
                        total_deleted = 0
                        failed_deletions = []
                        for doc_id in changed_doc_ids:
                            try:
                                deleted = vs.delete_by_metadata({"document_id": doc_id})
                                total_deleted += deleted
                            except Exception as e:
                                failed_deletions.append(doc_id)
                                console.print(
                                    f"  [yellow]⚠ Failed to delete vectors for {doc_id}: {e}[/yellow]"
                                )

                        console.print(f"  ✓ Deleted {total_deleted} stale chunks")

                        if failed_deletions:
                            console.print(
                                f"  [yellow]⚠ {len(failed_deletions)} document(s) had deletion errors — "
                                f"run 'greengovrag-cli rag index --mode full' to ensure a clean index[/yellow]"
                            )
                    else:
                        console.print(
                            "  [dim]No changed document IDs in monitoring results — skipping deletion[/dim]"
                        )

                    console.print(
                        "  [dim]Adding updated chunks to vector store...[/dim]"
                    )
                    vs.add_chunks(chunks)
                    console.print(f"  ✓ Indexed {len(chunks)} chunks")

                except Exception as e:
                    console.print(f"  [red]✗ Vector index update failed: {e}[/red]")
                    console.print(
                        "  [dim]Tip: Run 'greengovrag-cli rag index --mode full' to rebuild manually[/dim]"
                    )

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
        greengovrag-cli etl pipeline --config configs/etl_config.yml

    """
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


@rag_app.command("index")
def rag_index(
    chunks_dir: str = typer.Option(
        "data/chunks",
        "--chunks",
        "-c",
        help="Directory containing chunked documents",
    ),
    vector_store: str = typer.Option(
        "faiss",
        "--vector-store",
        "-v",
        help="Vector store type: faiss or qdrant (chromadb coming soon)",
    ),
    collection: str = typer.Option(
        settings.collection_name,
        "--collection",
        help="Collection/index name (for qdrant/chromadb)",
    ),
    output_path: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for index (FAISS only, default: data/vector_store/<store_type>)",
    ),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2",
        "--model",
        "-m",
        help="Embedding model to use",
    ),
    changed_files: Optional[str] = typer.Option(
        None,
        "--changed-files",
        help="JSON file with list of changed document IDs (for delta/incremental indexing)",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        help="Indexing mode: 'full' (rebuild entire index), 'delta' (update only changed), 'auto' (default, use delta if changed_files provided)",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="Number of chunks to process per batch (default: 100, recommended: 50-200)",
    ),
) -> None:
    """Build vector search index from document chunks.

    Supports FAISS (local) and Qdrant (server-based). ChromaDB support coming soon.

    Indexing modes:
    - Full: Rebuild entire index from all chunks (default when no --changed-files)
    - Delta: Update only changed documents (use with --changed-files)
    - Auto: Automatically use delta if --changed-files provided, otherwise full

    Examples:
    --------
        # Full indexing - FAISS (local, file-based - recommended for development)
        greengovrag-cli rag index --chunks data/chunks --vector-store faiss

        # Full indexing - Qdrant (server-based - recommended for production)
        greengovrag-cli rag index --chunks data/chunks --vector-store qdrant --collection greengovrag

        # Delta indexing - Only index changed documents (incremental update)
        greengovrag-cli rag index --chunks data/chunks --vector-store qdrant \\
            --collection greengovrag --changed-files changed_docs.json --mode delta

    Changed files format (JSON):
    --------
        {
            "changed_document_ids": ["doc_id_1", "doc_id_2", ...],
            "total_changed": 5
        }

    """
    # Validate vector store type
    valid_stores = ["faiss", "qdrant"]
    available_stores = ["faiss", "qdrant", "chromadb (coming soon)"]
    if vector_store.lower() not in valid_stores:
        console.print(
            f"[red]✗ Invalid vector store: {vector_store}[/red]",
            style="bold",
        )
        console.print(f"Available options: {', '.join(available_stores)}")
        raise typer.Exit(1)

    # Auto-detect changed files for smart indexing
    if mode == "auto" and not changed_files:
        # Try to find changed_docs.json generated by db load-chunks
        auto_changed_files = Path(chunks_dir) / "changed_docs.json"
        if auto_changed_files.exists():
            changed_files = str(auto_changed_files)
            console.print(
                f"[dim]Auto-detected changed documents file: {changed_files}[/dim]"
            )
        else:
            # No changed_docs.json found - check if this is first run or no changes
            # For Qdrant, check if collection exists
            # For FAISS, check if index file exists
            index_exists = False

            if vector_store == "qdrant":
                # Check if Qdrant collection exists (will check later)
                index_exists = True  # Assume exists, will verify during indexing
            elif vector_store == "faiss":
                # Check if FAISS index file exists
                index_path = (
                    output_path
                    if output_path
                    else f"data/vector_store/{vector_store}.index"
                )
                index_exists = Path(index_path).exists()

            if index_exists:
                console.print(
                    "[yellow]⚠ No document changes detected. Skipping indexing.[/yellow]"
                )
                console.print(
                    "[dim]Tip: If you want to force re-indexing, use --mode full[/dim]"
                )
                return  # Exit early, no indexing needed

    # Determine indexing mode
    if mode == "auto":
        indexing_mode = "delta" if changed_files else "full"
    else:
        indexing_mode = mode

    # Validate mode
    if indexing_mode not in ["full", "delta"]:
        console.print(
            f"[red]✗ Invalid mode: {indexing_mode}[/red]",
            style="bold",
        )
        console.print("Valid modes: full, delta, auto")
        raise typer.Exit(1)

    # Validate delta mode requires changed_files
    if indexing_mode == "delta" and not changed_files:
        console.print(
            "[red]✗ Delta mode requires --changed-files parameter[/red]",
            style="bold",
        )
        console.print(
            "Tip: Use --mode auto (or omit --mode) to automatically detect delta vs full indexing"
        )
        raise typer.Exit(1)

    # Load changed document IDs if provided
    changed_doc_ids = set()
    if changed_files:
        if not Path(changed_files).exists():
            console.print(
                f"[red]✗ Changed files JSON not found: {changed_files}[/red]",
                style="bold",
            )
            raise typer.Exit(1)

        with open(changed_files, encoding="utf-8") as f:
            changed_data = json.load(f)
            changed_doc_ids = set(changed_data.get("changed_document_ids", []))

        console.print(
            f"[dim]Loaded {len(changed_doc_ids)} changed document IDs from {changed_files}[/dim]"
        )

    console.print("[bold blue]Building vector search index...[/bold blue]")
    console.print(f"Vector store: {vector_store}")
    console.print(f"Embedding model: {embedding_model}")
    console.print(f"Indexing mode: {indexing_mode}")
    console.print(f"Batch size: {batch_size}")

    # Load chunks
    all_chunks = []
    skipped_files = 0
    processed_files = 0

    for chunk_file in Path(chunks_dir).rglob("*_chunks.json"):
        # In delta mode, check if we should skip this file
        if indexing_mode == "delta" and changed_doc_ids:
            # Try to get file_id from chunk metadata to check if it's in changed set
            with open(chunk_file, encoding="utf-8") as f:
                temp_chunks = json.load(f)
                if temp_chunks and isinstance(temp_chunks[0], dict):
                    file_id_in_chunks = (
                        temp_chunks[0].get("metadata", {}).get("file_id")
                    )
                    if file_id_in_chunks and file_id_in_chunks not in changed_doc_ids:
                        skipped_files += 1
                        continue

        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)

            # Normalize chunks to dict format
            # file_id, source_id, and source_pdf_url should already be in metadata
            # from the load-chunks command
            normalized_chunks = []
            for i, chunk in enumerate(chunks):
                if isinstance(chunk, str):
                    # Legacy format - convert string chunks to dict format
                    chunk_metadata = {
                        "source": str(chunk_file.stem),
                        "chunk_index": i,
                    }
                    normalized_chunks.append(
                        {
                            "content": chunk,
                            "metadata": chunk_metadata,
                        }
                    )
                elif isinstance(chunk, dict):
                    # Modern format - metadata should already contain file_id, source_id, etc.
                    # Just pass through as-is
                    normalized_chunks.append(chunk)
                else:
                    console.print(
                        f"[yellow]⚠ Skipping invalid chunk type: {type(chunk)}[/yellow]"
                    )

            all_chunks.extend(normalized_chunks)
            processed_files += 1

    if indexing_mode == "delta":
        console.print(
            f"[dim]Delta mode: Processed {processed_files} changed files, skipped {skipped_files} unchanged files[/dim]"
        )

    if not all_chunks:
        console.print(f"[red]✗ No chunks found in {chunks_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"Loaded {len(all_chunks)} chunks")

    # Create embeddings
    console.print("Generating embeddings...")
    console.print(
        f"[dim]Note: This may take 20-60 minutes for {len(all_chunks)} chunks on CPU[/dim]"
    )

    # Configure logging to show progress from vector stores
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        force=True,
    )

    embedder = ChunkEmbedder(provider="huggingface", model_name=embedding_model)

    # Build vector store
    console.print(f"Building {vector_store} vector store...")
    console.print(
        f"[dim]Processing {len(all_chunks)} chunks in batches of {batch_size}...[/dim]"
    )

    # Determine output path
    if output_path is None:
        output_path = f"data/vector_store/{vector_store}"
        if vector_store == "faiss":
            output_path += ".index"

    store_kwargs = {}
    if vector_store == "qdrant":
        store_kwargs["collection_name"] = collection
    elif vector_store == "chromadb":
        store_kwargs["collection_name"] = collection
        store_kwargs["persist_directory"] = output_path
    elif vector_store == "faiss":
        store_kwargs["index_path"] = output_path

    try:
        vs = create_vector_store(
            embeddings=embedder.embedder,
            store_type=vector_store,
            **store_kwargs,
        )

        # Handle delta vs full indexing
        if indexing_mode == "delta" and changed_doc_ids:
            # Delta mode: Delete old versions of changed docs, then add new versions
            console.print(
                "[dim]Delta mode: Deleting old versions of changed documents...[/dim]"
            )

            total_deleted = 0
            for doc_id in changed_doc_ids:
                try:
                    deleted = vs.delete_by_metadata({"document_id": doc_id})
                    total_deleted += deleted
                except Exception as e:
                    console.print(
                        f"[yellow]⚠ Failed to delete old version of {doc_id}: {e}[/yellow]"
                    )

            console.print(f"[dim]Deleted {total_deleted} old chunks[/dim]")

            # Add new chunks (only for changed documents)
            console.print("[dim]Adding updated chunks...[/dim]")
            vs.add_chunks(all_chunks)

        else:
            # Full mode: Rebuild entire index
            vs.build_store(all_chunks)

        # Persist for file-based stores
        if vector_store in ["faiss", "chromadb"]:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            vs.persist(output_path)
            console.print(
                f"[bold green]✓ Vector index built and saved to {output_path}[/bold green]",
            )
        else:
            mode_str = f" ({indexing_mode} mode)" if indexing_mode == "delta" else ""
            console.print(
                f"[bold green]✓ Vector index built in {vector_store} collection: {collection}{mode_str}[/bold green]",
            )

    except Exception as e:
        console.print(f"[red]✗ Failed to build vector store: {e}[/red]")
        raise typer.Exit(1)


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
        greengovrag-cli rag query "What are NGER reporting requirements?" --region SA

    """
    console.print(f"[bold blue]Searching for:[/bold blue] {query}")

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
        greengovrag-cli rag geospatial-search "tree preservation rules" --location Adelaide

    """
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
        greengovrag-cli rag list-locations

    """
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


# ============================================================================
# Database Commands
# ============================================================================


def _build_citation(title: str, metadata: dict) -> str:
    """Build formatted citation string from chunk metadata.

    Format: "{Title} {clause_ref}, pp.{page_range}"
    Example: "NGER Act 2007 (Cth) s.10.2, pp.42-45"

    Args:
    ----
        title: Document title
        metadata: Chunk metadata dict

    Returns:
    -------
        Formatted citation string

    """
    parts = [title]

    # Add clause reference if available (e.g., "s.3.2.1")
    clause_ref = metadata.get("clause_reference")
    if clause_ref:
        parts.append(clause_ref)

    # Add page information
    page_range = metadata.get("page_range")
    page_number = metadata.get("page_number")

    if page_range and len(page_range) == 2:
        start, end = page_range
        if start == end:
            parts.append(f"p.{start}")
        else:
            parts.append(f"pp.{start}-{end}")
    elif page_number:
        parts.append(f"p.{page_number}")

    return " ".join(parts)


@db_app.command("load-chunks")
def load_chunks(
    chunks_dir: Path = typer.Option(
        Path("data/chunks"),
        "--chunks-dir",
        "-c",
        help="Directory containing chunk JSON files",
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        "-b",
        help="Number of chunks to insert per batch",
    ),
) -> None:
    """Load chunk files into PostgreSQL database with metadata.

    This command loads processed chunks from JSON files into the database,
    populating the document_sources, document_files, and document_chunks tables
    with all metadata including jurisdiction, category, topic, region, etc.

    Example:
        greengovrag-cli db load-chunks --chunks-dir data/chunks
    """
    console.print(f"[bold]Loading chunks from {chunks_dir}...[/bold]")

    if not chunks_dir.exists():
        console.print(f"[red]Error: Chunks directory not found: {chunks_dir}[/red]")
        raise typer.Exit(1)

    # Get all chunk JSON files
    chunk_files = list(chunks_dir.glob("*_chunks.json"))

    if not chunk_files:
        console.print(f"[red]No chunk files found in {chunks_dir}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Found {len(chunk_files)} chunk files[/dim]")

    total_documents = 0
    total_chunks = 0
    changed_file_ids = []  # Track changed document file IDs for delta indexing

    for chunk_file in chunk_files:
        try:
            with open(chunk_file) as f:
                data = json.load(f)

            # Extract document metadata from first chunk
            if not data:
                console.print(
                    f"[yellow]Skipping empty file: {chunk_file.name}[/yellow]"
                )
                continue

            # Validate chunk format
            first_chunk = data[0]
            if isinstance(first_chunk, str):
                console.print(
                    f"[yellow]Warning: {chunk_file.name} contains legacy string format. "
                    f"Please re-run chunking to generate proper metadata.[/yellow]"
                )
                continue

            # Extract document-level metadata from first chunk
            metadata = first_chunk.get("metadata", {})
            title = metadata.get("title", chunk_file.stem.replace("_chunks", ""))

            # Save document source record
            source = save_document_source(
                title=title,
                source_url=metadata.get("source_url", ""),
                jurisdiction=metadata.get("jurisdiction", "unknown"),
                topic=metadata.get("topic", "general"),
                region=metadata.get("region"),
                category=metadata.get("category"),
                esg_metadata=metadata.get("esg_metadata"),
                spatial_metadata=metadata.get("spatial_metadata"),
                metadata=metadata,
                status="completed",
            )

            # Create a document file entry
            # Note: chunk metadata may contain filename if available
            filename = metadata.get("filename", f"{chunk_file.stem}.pdf")
            source_pdf_url = metadata.get("source_pdf_url", "")

            # Calculate content hash from chunk data (simplified approach)
            content_for_hash = "".join([c.get("content", "") for c in data])
            content_hash = hashlib.sha256(content_for_hash.encode()).hexdigest()

            doc_file = save_document_file(
                source_id=source.id,
                filename=filename,
                file_url=source_pdf_url,
                content_hash=content_hash,
                status="completed",
            )

            # Create document version record for citation verification
            # Only create version if content has changed or no version exists
            content_has_changed = True  # Default to True for safety
            try:
                with Session(engine) as session:
                    # Check if a version with this content_hash already exists
                    latest_version = session.exec(
                        select(DocumentVersion)
                        .where(DocumentVersion.file_id == doc_file.id)
                        .order_by(DocumentVersion.version_number.desc())  # type: ignore[attr-defined]
                    ).first()

                    # Create version only if no existing version OR content has changed
                    if (
                        not latest_version
                        or latest_version.content_hash != content_hash
                    ):
                        change_type = "new" if not latest_version else "updated"
                        save_document_version(
                            file_id=doc_file.id,
                            source_id=source.id,
                            content_hash=content_hash,
                            source_url=source_pdf_url,
                            file_size_bytes=None,  # Not available from chunk data
                            change_type=change_type,
                            metadata={
                                "note": "Version from load-chunks command",
                                "filename": filename,
                            },
                        )
                        console.print(
                            f"[dim]  Created document version ({change_type}) for {filename}[/dim]"
                        )
                        content_has_changed = True
                    else:
                        console.print(
                            f"[dim]  Skipped version creation for {filename} (content unchanged)[/dim]"
                        )
                        content_has_changed = False
            except Exception as e:
                console.print(
                    f"[yellow]Warning: Failed to create document version: {e}[/yellow]"
                )
                # On error, default to treating as changed to ensure data isn't lost
                content_has_changed = True

            total_documents += 1

            # Update chunk JSON with file_id and source_id metadata
            # This makes future indexing operations independent of database
            chunks_updated = False
            for chunk in data:
                if isinstance(chunk, dict):
                    if "metadata" not in chunk:
                        chunk["metadata"] = {}
                    # Add file_id and source_id if not already present
                    if "file_id" not in chunk["metadata"]:
                        chunk["metadata"]["file_id"] = doc_file.id
                        chunks_updated = True
                    if "source_id" not in chunk["metadata"]:
                        chunk["metadata"]["source_id"] = source.id
                        chunks_updated = True
                    if "source_pdf_url" not in chunk["metadata"] and source_pdf_url:
                        chunk["metadata"]["source_pdf_url"] = source_pdf_url
                        chunks_updated = True

            # Write back updated chunks to JSON file
            if chunks_updated:
                try:
                    with open(chunk_file, "w") as f:
                        json.dump(data, f, indent=2)
                    console.print(
                        f"[dim]  Updated {chunk_file.name} with file_id metadata[/dim]"
                    )
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Failed to update chunk file: {e}[/yellow]"
                    )

            # Track changed file IDs for delta indexing
            if content_has_changed:
                changed_file_ids.append(doc_file.id)

            # Only insert chunks into database if content is new or has changed
            chunk_count_for_doc = 0
            if content_has_changed:
                # Save chunks in batches
                for i in range(0, len(data), batch_size):
                    batch = data[i : i + batch_size]

                    for chunk in batch:
                        chunk_metadata = chunk.get("metadata", {})

                        # Use chunk_index from metadata (set during chunking)
                        # Try chunk_id first (new format), fallback to chunk_index (legacy)
                        chunk_idx = chunk_metadata.get(
                            "chunk_id"
                        ) or chunk_metadata.get("chunk_index", 0)

                        # Build citation string if not already present
                        citation = chunk_metadata.get("citation")
                        if not citation:
                            citation = _build_citation(title, chunk_metadata)

                        # Build deep link to PDF page if page number is available
                        deep_link = chunk_metadata.get("deep_link")
                        if not deep_link and chunk_metadata.get("page_number"):
                            page_num = chunk_metadata.get("page_number")

                            # Try to build deep link from available metadata
                            # Priority: 1) Direct PDF URL, 2) Source URL + filename, 3) Filename only
                            source_url = chunk_metadata.get("source_url", "")
                            filename = chunk_metadata.get("filename", "")

                            if source_url and source_url.lower().endswith(".pdf"):
                                # Direct PDF URL (external)
                                deep_link = f"{source_url}#page={page_num}"
                            elif filename and filename.lower().endswith(".pdf"):
                                # Use API endpoint to serve PDF with page anchor
                                # Format: /api/documents/files/{filename}#page={page_num}
                                deep_link = (
                                    f"/api/documents/files/{filename}#page={page_num}"
                                )

                        save_chunk(
                            source_id=source.id,
                            file_id=doc_file.id,
                            chunk_index=chunk_idx,
                            text=chunk.get("content", ""),
                            page_number=chunk_metadata.get("page_number"),
                            page_range=chunk_metadata.get("page_range"),
                            section_title=chunk_metadata.get("section_title"),
                            section_hierarchy=chunk_metadata.get("section_hierarchy"),
                            clause_reference=chunk_metadata.get("clause_reference"),
                            source_pdf_url=source_pdf_url,
                            deep_link=deep_link,
                            citation=citation,
                            metadata=chunk_metadata,
                        )

                    total_chunks += len(batch)
                    chunk_count_for_doc += len(batch)
                    console.print(
                        f"[dim]  Loaded batch {i//batch_size + 1}: "
                        f"{len(batch)} chunks from {chunk_file.name}[/dim]"
                    )

                # Update document source and file with chunk count
                update_document_source_status(
                    source_id=source.id,
                    status="completed",
                    chunk_count=chunk_count_for_doc,
                )

                update_document_file_status(
                    file_id=doc_file.id,
                    status="completed",
                    chunk_count=chunk_count_for_doc,
                )
            else:
                # Content unchanged - skip database insertion
                console.print(
                    f"[dim]  Skipped chunk insertion for {filename} (content unchanged)[/dim]"
                )

        except Exception as e:
            console.print(f"[red]Error loading {chunk_file.name}: {e}[/red]")
            continue

    console.print(
        f"\n[bold green]✓ Loaded {total_chunks} chunks from "
        f"{total_documents} documents[/bold green]"
    )

    # Write changed document IDs to JSON file for delta indexing
    if changed_file_ids:
        changed_docs_file = chunks_dir / "changed_docs.json"
        try:
            with open(changed_docs_file, "w") as f:
                json.dump(
                    {
                        "changed_document_ids": changed_file_ids,
                        "total_changed": len(changed_file_ids),
                    },
                    f,
                    indent=2,
                )
            console.print(
                f"[dim]✓ Wrote {len(changed_file_ids)} changed document IDs to {changed_docs_file}[/dim]"
            )
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to write changed_docs.json: {e}[/yellow]"
            )
    else:
        console.print("[dim]No document changes detected[/dim]")


# ============================================================================
# General Commands
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
    console.print("  • [cyan]rag[/cyan]  - RAG query and search operations")
    console.print("  • [cyan]db[/cyan]   - Database load and management\n")

    console.print("[bold]Quick start:[/bold]")
    console.print("  1. greengovrag-cli etl ingest")
    console.print("  2. greengovrag-cli etl parse")
    console.print("  3. greengovrag-cli etl chunk")
    console.print("  4. greengovrag-cli db load-chunks")
    console.print("  5. greengovrag-cli rag index")
    console.print("  6. greengovrag-cli rag query 'your question here'\n")

    console.print("Use --help with any command for more details")


if __name__ == "__main__":
    app()

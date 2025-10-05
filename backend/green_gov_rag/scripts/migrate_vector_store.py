"""Migrate data between vector stores (FAISS → Qdrant, etc.)."""

from __future__ import annotations

import logging
import time
from typing import Optional

import typer
from langchain.docstore.document import Document

from green_gov_rag.config import settings
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

app = typer.Typer(help="Migrate data between vector stores")
logger = logging.getLogger(__name__)


@app.command()
def migrate(
    source_type: str = typer.Option(
        "faiss",
        "--source",
        "-s",
        help="Source vector store type (faiss, qdrant, chromadb)",
    ),
    target_type: str = typer.Option(
        "qdrant",
        "--target",
        "-t",
        help="Target vector store type (faiss, qdrant, chromadb)",
    ),
    source_path: Optional[str] = typer.Option(
        None,
        "--source-path",
        help="Source store path/URL (uses config if not specified)",
    ),
    target_path: Optional[str] = typer.Option(
        None,
        "--target-path",
        help="Target store path/URL (uses config if not specified)",
    ),
    batch_size: int = typer.Option(
        1000,
        "--batch-size",
        "-b",
        help="Number of documents to migrate per batch",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Simulate migration without writing to target",
    ),
):
    """Migrate vector store data from one backend to another.

    Examples:
        # Migrate from FAISS to Qdrant
        python -m green_gov_rag.scripts.migrate_vector_store \\
            --source faiss --target qdrant

        # Dry run to check what would be migrated
        python -m green_gov_rag.scripts.migrate_vector_store \\
            --source faiss --target qdrant --dry-run
    """
    typer.echo("\n🔄 Vector Store Migration Tool\n")
    typer.echo(f"Source: {source_type}")
    typer.echo(f"Target: {target_type}")
    typer.echo(f"Batch size: {batch_size}")
    typer.echo(f"Dry run: {dry_run}\n")

    if source_type == target_type:
        typer.echo("❌ Source and target stores are the same. Nothing to do.")
        raise typer.Exit(1)

    # Validate configurations
    typer.echo("📋 Validating configurations...")
    source_validation = VectorStoreFactory.validate_config(source_type)
    target_validation = VectorStoreFactory.validate_config(target_type)

    if not source_validation["valid"]:
        typer.echo("❌ Source configuration invalid:")
        for issue in source_validation["issues"]:
            typer.echo(f"  - {issue}")
        raise typer.Exit(1)

    if not target_validation["valid"]:
        typer.echo("❌ Target configuration invalid:")
        for issue in target_validation["issues"]:
            typer.echo(f"  - {issue}")
        raise typer.Exit(1)

    typer.echo("✅ Configurations valid\n")

    # Initialize embeddings
    typer.echo("🔧 Initializing embeddings...")
    embeddings = ChunkEmbedder().embedder

    # Create source store
    typer.echo(f"📂 Loading source store ({source_type})...")
    source_kwargs = {}
    if source_path:
        if source_type == "faiss":
            source_kwargs["index_path"] = source_path
        elif source_type == "qdrant":
            source_kwargs["url"] = source_path

    try:
        source_store = VectorStoreFactory.create_vector_store(
            embeddings,
            store_type=source_type,
            **source_kwargs,
        )

        # Load source data
        if source_type == "faiss" and source_path:
            source_store.load(source_path)
        elif source_type == "qdrant":
            qdrant_path = source_path or settings.qdrant_url or "http://localhost:6333"
            source_store.load(qdrant_path)

        source_info = source_store.get_store_info()
        typer.echo("✅ Source store loaded:")
        typer.echo(f"   Status: {source_info.get('status')}")
        typer.echo(f"   Documents: {source_info.get('document_count', 'unknown')}\n")

    except Exception as e:
        typer.echo(f"❌ Failed to load source store: {e}")
        raise typer.Exit(1)

    # Extract documents from source
    typer.echo("📥 Extracting documents from source...")
    start_time = time.time()

    try:
        # Different extraction methods for different stores
        if source_type == "faiss":
            # FAISS limitation: need to perform broad search to get documents
            # This is a workaround - not ideal for large datasets
            typer.echo("   ⚠️  Note: FAISS doesn't support listing all documents.")
            typer.echo("   Using broad similarity search to extract documents...")
            documents = _extract_faiss_documents(source_store, batch_size)

        elif source_type == "qdrant":
            # Qdrant supports direct metadata listing
            metadata_list = source_store.list_metadata()
            documents = [
                Document(
                    page_content=meta.get("page_content", ""),
                    metadata={k: v for k, v in meta.items() if k != "page_content"},
                )
                for meta in metadata_list
            ]

        else:
            typer.echo(f"❌ Extraction not implemented for {source_type}")
            raise typer.Exit(1)

        extract_time = time.time() - start_time
        typer.echo(f"✅ Extracted {len(documents)} documents in {extract_time:.2f}s\n")

    except Exception as e:
        typer.echo(f"❌ Failed to extract documents: {e}")
        raise typer.Exit(1)

    if len(documents) == 0:
        typer.echo("❌ No documents found in source store. Nothing to migrate.")
        raise typer.Exit(1)

    # Show sample document
    typer.echo("📄 Sample document:")
    sample = documents[0]
    typer.echo(f"   Content: {sample.page_content[:100]}...")
    typer.echo(f"   Metadata: {sample.metadata}\n")

    if dry_run:
        typer.echo("🏁 Dry run complete. No data was written to target store.")
        typer.echo(f"   Would have migrated {len(documents)} documents")
        raise typer.Exit(0)

    # Confirm migration
    confirm = typer.confirm(
        f"Migrate {len(documents)} documents from {source_type} to {target_type}?"
    )
    if not confirm:
        typer.echo("❌ Migration cancelled")
        raise typer.Exit(0)

    # Create target store
    typer.echo(f"\n📂 Creating target store ({target_type})...")
    target_kwargs = {}
    if target_path:
        if target_type == "faiss":
            target_kwargs["index_path"] = target_path
        elif target_type == "qdrant":
            target_kwargs["url"] = target_path

    try:
        target_store = VectorStoreFactory.create_vector_store(
            embeddings,
            store_type=target_type,
            **target_kwargs,
        )
        typer.echo("✅ Target store created\n")
    except Exception as e:
        typer.echo(f"❌ Failed to create target store: {e}")
        raise typer.Exit(1)

    # Migrate in batches
    typer.echo(f"📤 Migrating documents in batches of {batch_size}...")
    total_batches = (len(documents) + batch_size - 1) // batch_size

    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        batch_num = i // batch_size + 1

        try:
            if i == 0:
                # First batch: build store
                chunks = [
                    {"content": doc.page_content, "metadata": doc.metadata}
                    for doc in batch
                ]
                target_store.build_store(chunks)
            else:
                # Subsequent batches: add documents
                target_store.add_documents(batch)

            typer.echo(
                f"   ✅ Batch {batch_num}/{total_batches}: "
                f"{len(batch)} documents migrated"
            )

        except Exception as e:
            typer.echo(f"   ❌ Batch {batch_num} failed: {e}")
            raise typer.Exit(1)

    # Persist target store
    if target_type == "faiss":
        target_store.persist(target_path)

    # Summary
    total_time = time.time() - start_time
    typer.echo("\n✅ Migration complete!")
    typer.echo(f"   Total documents: {len(documents)}")
    typer.echo(f"   Total time: {total_time:.2f}s")
    typer.echo(f"   Average speed: {len(documents) / total_time:.1f} docs/sec")

    # Verify target
    target_info = target_store.get_store_info()
    typer.echo("\n📊 Target store info:")
    for key, value in target_info.items():
        typer.echo(f"   {key}: {value}")


def _extract_faiss_documents(faiss_store, max_docs: int = 10000) -> list[Document]:
    """Extract documents from FAISS using similarity search workaround.

    FAISS doesn't support listing all documents, so we use a broad
    similarity search with generic queries to retrieve as many as possible.
    """
    all_docs = []
    seen_content = set()

    # Use multiple generic queries to maximize coverage
    generic_queries = [
        "",  # Empty query
        "regulations",
        "environmental",
        "compliance",
        "requirements",
        "guidelines",
        "NSW VIC QLD",
    ]

    for query in generic_queries:
        try:
            results = faiss_store.similarity_search(query, k=max_docs)
            for doc in results:
                content_hash = hash(doc.page_content)
                if content_hash not in seen_content:
                    all_docs.append(doc)
                    seen_content.add(content_hash)

            if len(all_docs) >= max_docs:
                break
        except Exception:
            continue

    return all_docs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app()

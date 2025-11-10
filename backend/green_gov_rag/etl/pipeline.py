"""Enhanced ETL Pipeline with Automated Metadata Tagging.

This module provides an end-to-end ETL pipeline that:
1. Loads documents from config or cloud storage
2. Downloads and parses PDFs
3. Auto-tags with ESG/NGER metadata
4. Chunks with preserved metadata
5. Saves chunks to cloud or local storage
6. Builds embeddings and vector store

Supports both local filesystem and cloud storage (AWS S3, Azure Blob)
via the ETL storage adapter.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain.docstore.document import Document
from langchain_community.document_loaders import PyPDFLoader

from green_gov_rag.config import settings
from green_gov_rag.etl.chunker import TextChunker
from green_gov_rag.etl.loader import load_documents_config
from green_gov_rag.etl.metadata_tagger import ESGOpenAITagger
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

logger = logging.getLogger(__name__)


class EnhancedETLPipeline:
    """ETL pipeline with automated metadata extraction and cloud storage support."""

    def __init__(
        self,
        enable_auto_tagging: bool = True,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        use_cloud: bool | None = None,
        storage_adapter: ETLStorageAdapter | None = None,
    ):
        """Initialize ETL pipeline.

        Args:
        ----
            enable_auto_tagging: Whether to auto-tag documents with ESG metadata
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
            use_cloud: Whether to use cloud storage. If None, uses settings.
            storage_adapter: Optional custom storage adapter instance

        """
        self.enable_auto_tagging = enable_auto_tagging
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        # Initialize metadata tagger if enabled
        self.tagger = ESGOpenAITagger() if enable_auto_tagging else None

        # Determine storage mode
        if use_cloud is None:
            use_cloud = settings.cloud_provider != "local"

        self.use_cloud = use_cloud
        self.storage_adapter = storage_adapter or (
            ETLStorageAdapter() if use_cloud else None
        )

        logger.info(
            f"Initialized ETL pipeline: use_cloud={use_cloud}, "
            f"auto_tagging={enable_auto_tagging}"
        )

    def load_and_parse_documents(
        self,
        config_path: str = "configs/documents_config.yml",
    ) -> list[Document]:
        """Load documents from config and parse them.

        Args:
        ----
            config_path: Path to documents config YAML

        Returns:
        -------
            List of parsed Document objects with metadata

        """
        # Load document configs
        doc_configs = load_documents_config(config_path)

        documents = []

        # Import DocumentSourceFactory to generate file_ids
        from green_gov_rag.etl.sources.factory import DocumentSourceFactory

        factory = DocumentSourceFactory()

        for doc_config in doc_configs:
            # Create source plugin to generate file_id
            source = factory.create_source(doc_config)

            # Get document metadata from config
            base_metadata = {
                "title": doc_config.get("title", "Untitled"),
                "source_url": doc_config.get("source_url", ""),
                "jurisdiction": doc_config.get("jurisdiction", ""),
                "category": doc_config.get("category", ""),
                "topic": doc_config.get("topic", ""),
                "region": doc_config.get("region", ""),
            }

            # Add ESG metadata if present in config
            if "esg_metadata" in doc_config:
                base_metadata["esg_metadata"] = doc_config["esg_metadata"]

            # Add spatial metadata if present in config
            if "spatial_metadata" in doc_config:
                base_metadata["spatial_metadata"] = doc_config["spatial_metadata"]

            # Download URLs
            urls = doc_config.get("download_urls", [])

            for url in urls:
                # Generate file_id for this URL (consistent with ingest.py)
                file_id = source.get_document_id(url)

                # Add file_id to metadata for citation verification
                metadata_with_file_id = base_metadata.copy()
                metadata_with_file_id["file_id"] = file_id
                metadata_with_file_id[
                    "document_id"
                ] = file_id  # Alias for backward compatibility

                # For now, assume PDFs are already downloaded
                # In production, integrate with download_documents()
                # Create document with config metadata
                doc = Document(
                    page_content="",  # Will be populated by PDF loader
                    metadata=metadata_with_file_id,
                )
                documents.append(doc)

        return documents

    def auto_tag_documents(self, documents: list[Document]) -> list[Document]:
        """Auto-tag documents with ESG/NGER metadata using LLM.

        Args:
        ----
            documents: List of Document objects

        Returns:
        -------
            Documents with enriched metadata

        """
        if not self.tagger:
            return documents

        print("Auto-tagging documents with ESG metadata...")
        tagged_docs = self.tagger.tag_all(documents)
        print(f"Tagged {len(tagged_docs)} documents")

        return tagged_docs

    def chunk_documents(self, documents: list[Document]) -> list[dict[str, Any]]:
        """Chunk documents while preserving metadata.

        Args:
        ----
            documents: List of Document objects

        Returns:
        -------
            List of chunked documents with metadata

        """
        chunked_docs = []

        for doc in documents:
            # Convert to dict format expected by chunker
            doc_dict = {"content": doc.page_content, "metadata": doc.metadata}

            # Chunk with metadata preservation
            chunks = self.chunker.chunk_docs([doc_dict])

            chunked_docs.extend(chunks)

        print(f"Created {len(chunked_docs)} chunks from {len(documents)} documents")
        return chunked_docs

    def run(
        self,
        config_path: str = "configs/documents_config.yml",
        output_path: str | None = None,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run the complete ETL pipeline.

        Args:
        ----
            config_path: Path to documents config
            output_path: Optional path to save processed chunks (local mode)
            document_ids: Optional list of document IDs to process (cloud mode)

        Returns:
        -------
            List of processed and chunked documents

        """
        print("=" * 60)
        print("Enhanced ETL Pipeline - With Auto-Tagging")
        print(f"Storage mode: {'cloud' if self.use_cloud else 'local'}")
        print("=" * 60)

        # Step 1: Load and parse documents
        print("\n1. Loading documents from config...")
        documents = self.load_and_parse_documents(config_path)
        print(f"Loaded {len(documents)} documents")

        # Step 2: Auto-tag with ESG metadata (if enabled)
        if self.enable_auto_tagging:
            print("\n2. Auto-tagging with ESG metadata...")
            documents = self.auto_tag_documents(documents)

        # Step 3: Chunk documents
        print("\n3. Chunking documents...")
        chunks = self.chunk_documents(documents)

        # Step 4: Save chunks
        if self.use_cloud and self.storage_adapter and document_ids:
            print(f"\n4. Saving {len(chunks)} chunks to cloud storage...")
            for doc_id in document_ids:
                # Filter chunks for this document
                doc_chunks = [
                    c
                    for c in chunks
                    if c.get("metadata", {}).get("document_id") == doc_id
                ]
                if doc_chunks:
                    self.storage_adapter.save_chunks(doc_chunks, doc_id)
                    print(f"Saved {len(doc_chunks)} chunks for document {doc_id}")
        elif output_path:
            print(f"\n4. Saving chunks to {output_path}...")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)
            print(f"Saved {len(chunks)} chunks")

        print("\n" + "=" * 60)
        print("Pipeline Complete!")
        print("=" * 60)

        return chunks


def process_pdf_with_tagging(
    pdf_path: str,
    base_metadata: dict[str, Any] | None = None,
    auto_tag: bool = True,
) -> list[dict[str, Any]]:
    """Process a single PDF with optional auto-tagging.

    Args:
    ----
        pdf_path: Path to PDF file
        base_metadata: Base metadata from config
        auto_tag: Whether to auto-tag with ESG metadata

    Returns:
    -------
        List of chunked documents with metadata

    """
    # Load PDF
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    # Add base metadata to all pages
    if base_metadata:
        for page in pages:
            page.metadata.update(base_metadata)

    # Auto-tag if enabled
    if auto_tag:
        tagger = ESGOpenAITagger()
        pages = tagger.tag_all(pages)

    # Chunk documents
    chunker = TextChunker(chunk_size=1000, chunk_overlap=100)

    chunks = []
    for page in pages:
        doc_dict = {"content": page.page_content, "metadata": page.metadata}
        page_chunks = chunker.chunk_docs([doc_dict])
        chunks.extend(page_chunks)

    return chunks


# Example usage
if __name__ == "__main__":
    # Example 1: Run full pipeline
    pipeline = EnhancedETLPipeline(enable_auto_tagging=True)
    chunks = pipeline.run(output_path="data/processed/chunks_with_metadata.json")

    # Example 2: Process single PDF with auto-tagging
    base_metadata = {
        "title": "NGER Coal Mining Guideline",
        "jurisdiction": "federal",
        "category": "environment",
        "topic": "emissions_reporting",
    }

    pdf_chunks = process_pdf_with_tagging(
        pdf_path="data/raw/nger_guideline.pdf",
        base_metadata=base_metadata,
        auto_tag=True,
    )

    print(f"\nProcessed PDF into {len(pdf_chunks)} chunks")
    print(f"Sample chunk metadata: {pdf_chunks[0]['metadata']}")

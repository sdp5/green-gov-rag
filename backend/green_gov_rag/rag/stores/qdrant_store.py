"""Qdrant vector store implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from langchain.docstore.document import Document
from langchain_core.embeddings import Embeddings

from green_gov_rag.rag.vector_store_interface import VectorStoreInterface

if TYPE_CHECKING:
    from langchain_qdrant import QdrantVectorStore as LangChainQdrantVectorStore
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStoreInterface):
    """Qdrant-based vector store implementation.

    Production-grade vector database with advanced features.
    Best for: Production, large datasets, distributed deployments
    """

    def __init__(
        self,
        embeddings: Embeddings,
        url: str = "http://localhost:6333",
        api_key: str | None = None,
        collection_name: str = "greengovrag",
        **kwargs: Any,
    ):
        """Initialize Qdrant vector store.

        Args:
            embeddings: Embeddings model
            url: Qdrant server URL
            api_key: Optional API key for Qdrant Cloud
            collection_name: Name of the collection
            **kwargs: Additional arguments
        """
        super().__init__(embeddings)
        self.url = url
        self.api_key = api_key
        self.collection_name = collection_name
        self.store: Optional[LangChainQdrantVectorStore] = None
        self.client: Optional[QdrantClient] = None

        # Lazy import - only when Qdrant is actually used
        try:
            from langchain_qdrant import QdrantVectorStore as LangChainQdrantVectorStore
            from qdrant_client import QdrantClient

            self.LangChainQdrantVectorStore = LangChainQdrantVectorStore
            self.QdrantClient = QdrantClient
            self._initialize_client()
        except ImportError as e:
            logger.error(
                "Qdrant dependencies not installed. "
                "Install with: pip install qdrant-client langchain-qdrant"
            )
            raise ImportError(
                "Qdrant dependencies missing. Install: pip install qdrant-client langchain-qdrant"
            ) from e

    def _initialize_client(self) -> None:
        """Initialize Qdrant client and check connection with retry logic."""
        import time

        if not hasattr(self, "QdrantClient") or self.QdrantClient is None:
            raise ImportError("QdrantClient not available")

        self.client = self.QdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=10,
        )

        assert self.client is not None  # Help MyPy

        # Test connection with exponential backoff retry
        # This handles the case where EC2 instance needs time to boot and start Qdrant
        max_retries = 20  # 20 attempts over ~5 minutes with exponential backoff
        retry_delay = 3.0  # Start with 3 seconds
        max_delay = 30.0  # Cap at 30 seconds

        for attempt in range(1, max_retries + 1):
            try:
                collections = self.client.get_collections()
                logger.info(
                    f"Connected to Qdrant at {self.url} (attempt {attempt}/{max_retries}). "
                    f"Found {len(collections.collections)} collections."
                )
                return  # Success!
            except Exception as e:
                if attempt == max_retries:
                    logger.error(
                        f"Failed to connect to Qdrant after {max_retries} attempts: {e}"
                    )
                    raise

                logger.warning(
                    f"Qdrant connection attempt {attempt}/{max_retries} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)

                # Exponential backoff, capped at max_delay
                retry_delay = min(retry_delay * 1.5, max_delay)

    def add_documents(self, docs: list[Document]) -> None:
        """Add documents to Qdrant."""
        if self.store is None:
            raise ValueError("Vector store not initialized. Call build_store first.")

        # Qdrant handles persistence automatically
        self.store.add_documents(docs)
        logger.info(f"Added {len(docs)} documents to Qdrant")

    def build_store(self, chunks: list[dict], batch_size: int = 100) -> None:
        """Build Qdrant collection from chunks using batched processing.

        Args:
            chunks: List of chunk dictionaries
            batch_size: Number of documents to process per batch (default: 100)
        """
        if (
            not hasattr(self, "LangChainQdrantVectorStore")
            or self.LangChainQdrantVectorStore is None
        ):
            raise ImportError("Qdrant not available")

        assert self.LangChainQdrantVectorStore is not None  # Help MyPy

        if not chunks:
            logger.warning("No chunks provided for indexing")
            return

        total_batches = (len(chunks) + batch_size - 1) // batch_size
        logger.info(
            f"Building Qdrant collection '{self.collection_name}' "
            f"with {len(chunks)} chunks in {total_batches} batches"
        )

        # Process first batch to create collection
        first_batch_size = min(batch_size, len(chunks))
        first_batch = chunks[:first_batch_size]
        documents = [
            Document(
                page_content=chunk["content"],
                metadata=chunk.get("metadata", {}),
            )
            for chunk in first_batch
        ]

        self.store = self.LangChainQdrantVectorStore.from_documents(
            documents,
            self.embeddings,
            url=self.url,
            api_key=self.api_key,
            collection_name=self.collection_name,
            prefer_grpc=False,  # Use HTTP for compatibility
        )
        logger.info(f"Created collection with first batch of {len(first_batch)} chunks")

        # Process remaining batches if any
        if len(chunks) > first_batch_size:
            for i in range(first_batch_size, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_num = (i // batch_size) + 1

                documents = [
                    Document(
                        page_content=chunk["content"],
                        metadata=chunk.get("metadata", {}),
                    )
                    for chunk in batch
                ]

                self.add_documents(documents)
                logger.info(
                    f"Added batch {batch_num}/{total_batches}: {len(documents)} chunks"
                )

        logger.info(
            f"Completed building Qdrant collection '{self.collection_name}' "
            f"with {len(chunks)} total chunks"
        )

    def add_chunks(self, chunks: list[dict]) -> None:
        """Add chunks to existing Qdrant collection."""
        if self.store is None:
            self.build_store(chunks)
        else:
            documents = [
                Document(
                    page_content=chunk["content"],
                    metadata=chunk.get("metadata", {}),
                )
                for chunk in chunks
            ]
            self.add_documents(documents)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        metadata_filters: dict | None = None,
    ) -> list[Document]:
        """Perform similarity search with native metadata filtering."""
        if self.store is None:
            raise ValueError("Vector store not initialized.")

        # Qdrant supports native metadata filtering
        filter_dict: Any = None
        if metadata_filters:
            # Convert to Qdrant filter format
            filter_dict = self._build_qdrant_filter(metadata_filters)

        results = self.store.similarity_search(
            query,
            k=k,
            filter=filter_dict,
        )

        return results

    def _build_qdrant_filter(self, metadata_filters: dict) -> Any:
        """Build Qdrant filter from metadata dictionary.

        Qdrant uses a specific filter format with nested metadata:
        {
            "must": [
                {"key": "metadata.region", "match": {"value": "NSW"}},
                {"key": "metadata.topic", "match": {"value": "emissions"}}
            ]
        }

        Note: LangChain's QdrantVectorStore stores metadata in a nested structure
        under the 'metadata' key, so filters must use 'metadata.' prefix.

        IMPORTANT: Qdrant performs exact string matching (case-sensitive).
        Values are passed as-is from the query service, which should handle
        normalization (e.g., "SA" -> "South Australia", "State" -> "state").

        Special handling for LGA filtering:
        - lga_names: Filters by metadata.spatial_metadata.lga_names array
        """
        must_conditions = []

        for key, value in metadata_filters.items():
            # Special handling for LGA names (nested in spatial_metadata)
            if key == "lga_names":
                filter_key = "metadata.spatial_metadata.lga_names"
            # Skip region_specified (used only for filters_applied transparency)
            elif key == "region_specified":
                continue
            else:
                # Add 'metadata.' prefix for nested structure
                filter_key = f"metadata.{key}"

            if isinstance(value, list):
                # OR condition for lists
                must_conditions.append({"key": filter_key, "match": {"any": value}})
            else:
                # Exact match
                must_conditions.append({"key": filter_key, "match": {"value": value}})

        return {"must": must_conditions} if must_conditions else None

    def persist(self, path: str | None = None) -> None:
        """Persist is automatic with Qdrant.

        Qdrant persists data automatically to disk/cloud.
        This method exists for interface compatibility.
        """
        logger.info("Qdrant persists automatically. No action needed.")

    def load(self, path: str) -> None:
        """Load Qdrant collection.

        Qdrant loads collections automatically on connection.
        This creates a reference to an existing collection, or will create it on first add.
        """
        if not self.client:
            self._initialize_client()
        if (
            not hasattr(self, "LangChainQdrantVectorStore")
            or self.LangChainQdrantVectorStore is None
        ):
            raise ImportError("Qdrant not available")

        assert self.LangChainQdrantVectorStore is not None  # Help MyPy
        assert self.client is not None

        # Check if collection exists
        try:
            self.client.get_collection(collection_name=self.collection_name)
            logger.info(
                f"Connected to existing Qdrant collection '{self.collection_name}'"
            )
        except Exception:
            logger.info(
                f"Collection '{self.collection_name}' doesn't exist yet. "
                "Run 'rag index' or ETL pipeline to create and populate it."
            )

        # Create store reference (will create collection on first add if needed)
        self.store = self.LangChainQdrantVectorStore(
            client=self.client,
            collection_name=self.collection_name,
            embedding=self.embeddings,
        )
        logger.info(
            f"Qdrant vector store ready for collection '{self.collection_name}'"
        )

    def delete_by_id(self, ids: list[str]) -> None:
        """Delete documents by ID from Qdrant."""
        if not self.client:
            raise ValueError("Qdrant client not initialized.")
        if not hasattr(self, "QdrantClient") or self.QdrantClient is None:
            raise ImportError("QdrantClient not available")

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=ids,
        )
        logger.info(f"Deleted {len(ids)} documents from Qdrant")

    def delete_by_metadata(self, metadata_filters: dict) -> int:
        """Delete documents matching metadata filters (optimized for Qdrant).

        Args:
            metadata_filters: Metadata filters (e.g., {"document_id": "doc_123"})

        Returns:
            Number of documents deleted
        """
        if not self.client:
            raise ValueError("Qdrant client not initialized.")
        if not hasattr(self, "QdrantClient") or self.QdrantClient is None:
            raise ImportError("QdrantClient not available")

        # Use Qdrant's native filtering for efficient deletion
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        # Build filter conditions
        conditions = [
            FieldCondition(
                key=f"metadata.{key}",
                match=MatchValue(value=value),
            )
            for key, value in metadata_filters.items()
        ]

        # Type ignore for Qdrant's complex union type - runtime works correctly
        filter_obj: Filter | None = Filter(must=conditions) if conditions else None  # type: ignore[arg-type]

        # Delete using filter
        result = self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_obj,
        )

        deleted_count = getattr(result, "deleted", 0) if result else 0
        logger.info(
            f"Deleted {deleted_count} documents from Qdrant matching filters: {metadata_filters}"
        )
        return deleted_count

    def list_metadata(self) -> list[dict]:
        """List all metadata in Qdrant collection."""
        if not self.client:
            raise ValueError("Qdrant client not initialized.")
        if not hasattr(self, "QdrantClient") or self.QdrantClient is None:
            raise ImportError("QdrantClient not available")

        # Scroll through all points and extract metadata
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            limit=1000,  # Adjust based on collection size
            with_payload=True,
            with_vectors=False,
        )

        return [point.payload for point in points if point.payload is not None]

    def get_store_info(self) -> dict:
        """Get information about Qdrant collection."""
        if not self.client:
            return {
                "backend": "qdrant",
                "status": "not_initialized",
                "document_count": 0,
            }
        if not hasattr(self, "QdrantClient") or self.QdrantClient is None:
            return {
                "backend": "qdrant",
                "status": "error",
                "error": "QdrantClient not available",
            }

        try:
            collection_info = self.client.get_collection(self.collection_name)

            # Handle vector size - can be VectorParams or dict[str, VectorParams]
            vector_size = None
            vectors_config = collection_info.config.params.vectors
            if vectors_config:
                if hasattr(vectors_config, "size"):
                    vector_size = vectors_config.size
                elif isinstance(vectors_config, dict):
                    # If it's a dict, get the first vector config
                    first_vector = next(iter(vectors_config.values()), None)
                    if first_vector and hasattr(first_vector, "size"):
                        vector_size = first_vector.size

            return {
                "backend": "qdrant",
                "status": "active",
                "url": self.url,
                "collection_name": self.collection_name,
                "document_count": collection_info.points_count,
                "vector_size": vector_size,
                "supports_metadata_listing": True,
                "supports_deletion": True,
                "supports_updates": True,
                "indexed_fields": list(collection_info.payload_schema.keys())
                if collection_info.payload_schema
                else [],
            }
        except Exception as e:
            logger.error(f"Failed to get Qdrant collection info: {e}")
            return {
                "backend": "qdrant",
                "status": "error",
                "error": str(e),
            }

# rag/agent_tools.py

"""Agent Tools for GreenGovRAG.

Provides wrapper functions to call the RAG chain from LangChain Agents,
supporting optional metadata filters and structured responses.
"""

from __future__ import annotations

from .rag_chain import RAGChain


class RAGAgentTools:
    def __init__(self, rag_chain: RAGChain):
        """Initialize the Agent tools with a RAG chain.
        :param rag_chain: RAGChain instance.
        """
        self.rag_chain = rag_chain

    def answer_question(
        self,
        question: str,
        metadata_filters: dict | None = None,
        top_k: int = 4,
    ):
        """Query the RAG chain with optional metadata filtering.
        :param question: User query string
        :param metadata_filters: Optional dictionary of metadata filters (e.g., region, topic)
        :param top_k: Number of top documents to retrieve
        :return: dict containing 'answer' and 'sources'.
        """
        response = self.rag_chain.query(
            question=question,
            metadata_filters=metadata_filters,
            k=top_k,
        )

        # Format sources nicely
        sources = []
        for doc in response.get("source_documents", []):
            sources.append(
                {
                    "title": doc.metadata.get("title", "Unknown"),
                    "url": doc.metadata.get("source_url", ""),
                    "topic": doc.metadata.get("topic", ""),
                    "region": doc.metadata.get("region", ""),
                },
            )

        return {"answer": response.get("result", ""), "sources": sources}

    def agent_tool_wrapper(self, question: str, context: dict | None = None):
        """Optional wrapper to integrate with LangChain Agents.
        Allows passing context as metadata filters.
        :param question: User query string
        :param context: Optional context dict to apply as metadata filters
        :return: dict with answer and sources.
        """
        metadata_filters = context or None
        return self.answer_question(question, metadata_filters=metadata_filters)


class RAGAgent:
    """RAG Agent with separated retrieval and generation phases for caching."""

    def __init__(self, vector_store=None, embedder=None):
        from green_gov_rag.config import settings
        from green_gov_rag.rag.embeddings import ChunkEmbedder
        from green_gov_rag.rag.rag_chain import RAGChain
        from green_gov_rag.rag.vector_store_factory import create_vector_store

        # Initialize embedder if not provided
        if embedder is None:
            embedder = ChunkEmbedder(provider="huggingface")

        self.embedder = embedder

        # Initialize vector store if not provided
        if vector_store is None:
            # Use factory to create vector store based on configuration
            store_type = settings.vector_store_type.lower()

            store_kwargs = {}
            if store_type == "qdrant":
                store_kwargs["url"] = settings.qdrant_url
                store_kwargs["collection_name"] = "greengovrag"
            elif store_type == "faiss":
                store_kwargs["index_path"] = settings.vector_store_path + "/faiss.index"

            vector_store = create_vector_store(
                embeddings=self.embedder.embedder, store_type=store_type, **store_kwargs
            )

            # Load existing collection if Qdrant or FAISS
            if hasattr(vector_store, "load"):
                try:
                    if store_type == "qdrant":
                        # For Qdrant, load() connects to existing collection
                        vector_store.load(path="")  # Path not used for Qdrant
                    elif store_type == "faiss":
                        # For FAISS, load from index file
                        index_path = store_kwargs.get("index_path")
                        if index_path:
                            vector_store.load(path=index_path)
                except Exception as e:
                    import logging

                    logging.warning(f"Could not load existing vector store: {e}")
                    raise  # Re-raise so we know what went wrong

        self.vector_store = vector_store

        # Validate vector store has documents
        self._validate_vector_store()

        self.chain = RAGChain(self.vector_store, self.embedder)

    def _validate_vector_store(self) -> None:
        """Validate that vector store exists and has documents.

        Raises:
            RuntimeError: If vector store is empty or invalid
        """
        try:
            # Try to get vector store count
            doc_count = self._get_vector_store_count()

            if doc_count == 0:
                raise RuntimeError(
                    "Vector store is empty. No documents found.\n\n"
                    "To fix this, run the document ingestion pipeline:\n"
                    "  python -m green_gov_rag.etl.ingest_documents\n\n"
                    "Or if using Docker:\n"
                    "  docker-compose run --rm backend python -m green_gov_rag.etl.ingest_documents"
                )

        except Exception as e:
            if "Vector store is empty" in str(e):
                raise
            # If we can't validate, log warning but don't fail
            # (allows for non-standard vector store implementations)
            import logging

            logging.warning(f"Could not validate vector store: {e}")

    def _get_vector_store_count(self) -> int:
        """Get count of documents in vector store.

        Returns:
            Number of documents in vector store
        """
        import logging

        logger = logging.getLogger(__name__)

        # Get the underlying LangChain vector store
        # Factory pattern stores use .store attribute
        vs = getattr(self.vector_store, "store", self.vector_store)

        logger.debug(f"Vector store type: {type(vs)}")
        logger.debug(f"Vector store has client: {hasattr(vs, 'client')}")
        logger.debug(
            f"Vector store has collection_name: {hasattr(vs, 'collection_name')}"
        )

        # FAISS
        if hasattr(vs, "index") and hasattr(vs.index, "ntotal"):
            count = vs.index.ntotal
            logger.debug(f"FAISS index count: {count}")
            return count

        # Qdrant - check the wrapper object first
        if hasattr(self.vector_store, "client") and hasattr(
            self.vector_store, "collection_name"
        ):
            try:
                collection_name = self.vector_store.collection_name
                info = self.vector_store.client.get_collection(collection_name)
                count = info.points_count or 0
                logger.debug(f"Qdrant collection '{collection_name}' count: {count}")
                return count
            except Exception as e:
                logger.debug(f"Failed to get Qdrant count from wrapper: {e}")

        # Qdrant - check the underlying store
        if hasattr(vs, "client") and hasattr(vs, "collection_name"):
            try:
                collection_name = vs.collection_name
                info = vs.client.get_collection(collection_name)
                count = info.points_count or 0
                logger.debug(f"Qdrant collection '{collection_name}' count: {count}")
                return count
            except Exception as e:
                logger.debug(f"Failed to get Qdrant count: {e}")

        # Chroma
        if hasattr(vs, "_collection"):
            count = vs._collection.count()
            logger.debug(f"Chroma collection count: {count}")
            return count

        # Generic fallback - try a test search
        try:
            results = vs.similarity_search("test", k=1)
            count = 1 if results else 0
            logger.debug(f"Fallback search count: {count}")
            return count
        except Exception as e:
            logger.debug(f"Fallback search failed: {e}")
            return 0

    def retrieve(
        self, query: str, metadata_filters: dict | None = None, k: int = 5
    ) -> tuple[str, list]:
        """Retrieve relevant documents without LLM generation.

        This is Phase 1 of the RAG pipeline - allows caching layer to check
        for cached answers before expensive LLM generation.

        Args:
            query: User query string
            metadata_filters: Optional metadata filters (region, jurisdiction, etc.)
            k: Number of documents to retrieve

        Returns:
            Tuple of (context_string, source_documents)
        """
        # Retrieve documents from vector store
        documents = self.chain.retrieve_documents(
            query=query, metadata_filters=metadata_filters, k=k
        )

        # Build formatted context for LLM
        context = self.chain.build_context_from_documents(documents)

        return context, documents

    def generate(self, query: str, context: str) -> str:
        """Generate answer using LLM given pre-retrieved context.

        This is Phase 2 of the RAG pipeline - called only on cache miss.

        Args:
            query: User query string
            context: Pre-formatted context from retrieved documents

        Returns:
            Generated answer string
        """
        return self.chain.generate_answer(query=query, context=context)

    def list_documents(self):
        """Return all document metadata stored in the vector store."""
        return self.vector_store.list_metadata()


# ------------------------------
# Example usage
# ------------------------------
if __name__ == "__main__":
    from rag.embeddings import ChunkEmbedder
    from rag.rag_chain import RAGChain as RAGChainClass
    from rag.vector_store import VectorStore

    # Initialize the vector store (load prebuilt FAISS or Qdrant store)
    vector_store = VectorStore(
        index_path="faiss_index",
        embeddings=ChunkEmbedder(
            provider="huggingface",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        ).embedder,
    )
    # Load existing vector store from
    vector_store = vector_store.load(path="data/processed/faiss_index")

    # Initialize RAG Chain
    rag_chain = RAGChainClass(vector_store)

    # Initialize Agent Tools
    agent_tools = RAGAgentTools(rag_chain)

    # Example 1: Simple query without filters
    response = agent_tools.answer_question(
        "What are native vegetation clearance rules in SA?",
    )
    print("Answer:\n", response["answer"])
    print("Sources:\n", response["sources"])

    # Example 2: Query with metadata filters
    filters = {"region": "South Australia", "topic": "vegetation_clearance"}
    response_filtered = agent_tools.answer_question(
        "What approvals are required for land clearing?",
        metadata_filters=filters,
    )
    print("\nFiltered Answer:\n", response_filtered["answer"])
    print("Filtered Sources:\n", response_filtered["sources"])

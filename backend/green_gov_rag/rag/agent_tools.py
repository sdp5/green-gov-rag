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
    def __init__(self, vector_store=None, embedder=None):
        from green_gov_rag.rag.embeddings import ChunkEmbedder
        from green_gov_rag.rag.rag_chain import RAGChain
        from green_gov_rag.rag.vector_store import VectorStore

        # Initialize embedder if not provided
        if embedder is None:
            embedder = ChunkEmbedder(provider="huggingface")

        self.embedder = embedder

        # Initialize vector store if not provided
        if vector_store is None:
            # VectorStore requires embeddings, so we create one with the embedder
            vector_store = VectorStore(embeddings=self.embedder.embedder)

        self.vector_store = vector_store
        self.chain = RAGChain(self.vector_store, self.embedder)

    def query(self, text: str, metadata_filters: dict | None = None):
        """:param text: User query
        :param metadata_filters: dict of metadata to filter retrieved documents (e.g., region, topic)
        :return: (answer_text, list_of_source_metadata)
        """
        # Call the RAGChain query method
        result = self.chain.query(question=text, metadata_filters=metadata_filters)
        # Extract answer and sources from result
        answer = result.get("result", "")
        sources = result.get("source_documents", [])
        return answer, sources

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

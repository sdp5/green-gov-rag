# rag/rag_chain.py

"""RAG Chain for GreenGovRAG.

Retrieval-Augmented Generation pipeline supporting multiple LLM providers:
- OpenAI
- Azure OpenAI
- AWS Bedrock
- Anthropic

Supports optional metadata filtering during retrieval.

1. Retrieve: Fetch top-K relevant document chunks using vector search.
2. Embed: Convert query into vector using HuggingFace/OpenAI embeddings.
3. Generate: Pass context + query to LLM for answer generation.
4. Query with sources: Returns answer + metadata for transparency.

Now uses centralized settings from green_gov_rag.config and LLMFactory for multi-provider support.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from green_gov_rag.config import settings
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.enhanced_response import EnhancedResponse, ResponseFormatter
from green_gov_rag.rag.llm_factory import get_llm
from green_gov_rag.rag.vector_store import VectorStore

if TYPE_CHECKING:
    from langchain.schema.language_model import BaseLanguageModel


class RAGChain:
    def __init__(
        self,
        vector_store: VectorStore,
        embedder: ChunkEmbedder | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        top_k: int = 5,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ):
        """Initialize RAG Chain.

        :param vector_store: VectorStore instance
        :param embedder: ChunkEmbedder instance
        :param llm_provider: LLM provider (openai, azure, bedrock, anthropic).
                            Defaults to settings.llm_provider
        :param llm_model: Model name. Defaults to settings.llm_model
        :param top_k: Number of retrieved chunks to pass to LLM
        :param temperature: Sampling temperature for LLM
        :param max_tokens: Maximum tokens in LLM response
        """
        self.vector_store = vector_store
        self.embedder = embedder or ChunkEmbedder()
        self.llm_provider = llm_provider or settings.llm_provider
        self.llm_model = llm_model or settings.llm_model
        self.top_k = top_k
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize LLM using factory
        self.llm: BaseLanguageModel = get_llm(
            provider=self.llm_provider,
            model=self.llm_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def retrieve(self, query: str) -> list[dict]:
        """Retrieve top_k relevant chunks for the query."""
        query_embedding = self.embedder.embed_query(query)  # type: ignore[attr-defined]
        return self.vector_store.store.search(query_embedding, top_k=self.top_k)  # type: ignore[union-attr,call-arg,return-value]

    def generate_answer(self, query: str) -> str:
        """Generate answer using retrieved context and LLM."""
        from langchain.schema import HumanMessage

        retrieved = self.retrieve(query)
        context = "\n".join(
            [
                r["metadata"].get("source", "")
                + ": "
                + r["metadata"].get("content", "")
                for r in retrieved
            ],
        )

        prompt = f"Answer the query based on the following context:\n{context}\n\nQuery: {query}\nAnswer:"

        # Use LangChain's invoke method for all providers
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content if hasattr(response, "content") else str(response)

    def query_with_sources(self, query: str) -> dict:
        """Return both the answer and the retrieved sources for transparency."""
        retrieved = self.retrieve(query)
        answer = self.generate_answer(query)
        return {"query": query, "answer": answer, "sources": retrieved}

    def query_with_enhanced_citations(self, query: str, k: int = 5) -> EnhancedResponse:
        """Query with enhanced citations and deep links.

        Args:
        ----
            query: User question
            k: Number of sources to retrieve

        Returns:
        -------
            EnhancedResponse with inline citations and hierarchical metadata

        """
        from langchain.docstore.document import Document

        # Retrieve documents
        results = self.vector_store.similarity_search(query, k=k)

        # Convert to Document objects if needed
        documents: list[Document] = []
        if results:
            # Type narrowing - assume results is list of Documents
            documents = results

        # Generate answer
        answer = self.generate_answer(query)

        # Create enhanced response
        return ResponseFormatter.create_enhanced_response(
            query=query,
            answer=answer,
            sources=documents,
        )

    def query(self, question: str, metadata_filters: dict | None = None, k: int = 4):
        """Query the RAG chain with optional metadata filtering.
        :param question: User query string
        :param metadata_filters: Optional dictionary of metadata filters
        :param k: Number of top documents to retrieve
        :return: dict with 'result' and 'source_documents'.
        """
        # Retrieve documents with optional metadata filtering
        if metadata_filters:
            source_docs = self.vector_store.similarity_search(
                question,
                k=k,
                metadata_filters=metadata_filters,
            )
        else:
            # Use existing retrieve method
            retrieved = self.retrieve(question)
            # Convert to Document objects for compatibility
            from langchain.docstore.document import Document

            source_docs = [
                Document(
                    page_content=r.get("metadata", {}).get("content", ""),
                    metadata=r.get("metadata", {}),
                )
                for r in retrieved
            ]

        # Generate answer using the LLM
        answer = self.generate_answer(question)

        return {
            "result": answer,
            "source_documents": source_docs,
        }


if __name__ == "__main__":
    from green_gov_rag.rag.embeddings import ChunkEmbedder as ChunkEmbedderClass
    from green_gov_rag.rag.vector_store import VectorStore as VectorStoreClass

    # Quick demo
    store = VectorStoreClass(
        index_path="faiss_index",
        embeddings=ChunkEmbedderClass(
            provider="huggingface",
            model_name="sentence-transformers/all-MiniLM-L6-v2",
        ).embedder,
    )
    embedder = ChunkEmbedderClass()
    rag_chain = RAGChain(vector_store=store, embedder=embedder)

    query = "What are the native vegetation clearance rules in South Australia?"
    result = rag_chain.query_with_sources(query)
    print(result)

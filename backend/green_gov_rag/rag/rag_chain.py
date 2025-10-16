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

from typing import TYPE_CHECKING, Union

from green_gov_rag.config import settings
from green_gov_rag.rag.embeddings import ChunkEmbedder
from green_gov_rag.rag.enhanced_response import EnhancedResponse, ResponseFormatter
from green_gov_rag.rag.llm_factory import get_llm
from green_gov_rag.rag.vector_store import VectorStore

if TYPE_CHECKING:
    from langchain.schema.language_model import BaseLanguageModel

    from green_gov_rag.rag.vector_store_interface import VectorStoreInterface


class RAGChain:
    def __init__(
        self,
        vector_store: Union[VectorStore, "VectorStoreInterface"],
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

    def retrieve_documents(
        self, query: str, metadata_filters: dict | None = None, k: int | None = None
    ) -> list:
        """Retrieve relevant documents using vector similarity search.

        Args:
            query: User query string
            metadata_filters: Optional metadata filters (region, jurisdiction, etc.)
            k: Number of documents to retrieve (defaults to self.top_k)

        Returns:
            List of Document objects with page_content and metadata
        """
        k = k or self.top_k

        # Use vector store's similarity_search with optional filters
        if metadata_filters:
            documents = self.vector_store.similarity_search(
                query,
                k=k,
                metadata_filters=metadata_filters,
            )
        else:
            documents = self.vector_store.similarity_search(query, k=k)

        return documents

    def generate_answer(self, query: str, context: str) -> str:
        """Generate answer using LLM given pre-built context.

        Args:
            query: User query string
            context: Pre-formatted context from retrieved documents

        Returns:
            Generated answer string
        """
        from langchain.schema import HumanMessage

        prompt = (
            f"Answer the query based on the following context:\n\n"
            f"{context}\n\n"
            f"Query: {query}\n\n"
            f"Answer:"
        )

        # Use LangChain's invoke method for all providers
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content if hasattr(response, "content") else str(response)

    def build_context_from_documents(self, documents: list) -> str:
        """Build formatted context string from documents.

        Args:
            documents: List of Document objects

        Returns:
            Formatted context string for LLM
        """
        context_parts = []
        for i, doc in enumerate(documents, 1):
            # Extract content and metadata
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            metadata = doc.metadata if hasattr(doc, "metadata") else {}

            # Format with source info
            source = metadata.get("title", metadata.get("source", f"Document {i}"))
            context_parts.append(f"[Source: {source}]\n{content}\n")

        return "\n".join(context_parts)

    def query_with_sources(self, query: str) -> dict:
        """Return both the answer and the retrieved sources for transparency."""
        # Phase 1: Retrieve documents
        documents = self.retrieve_documents(query)

        # Phase 2: Build context and generate
        context = self.build_context_from_documents(documents)
        answer = self.generate_answer(query, context)

        return {"query": query, "answer": answer, "sources": documents}

    def query_with_enhanced_citations(self, query: str, k: int = 5) -> EnhancedResponse:
        """Query with enhanced citations and deep links.

        Args:
            query: User question
            k: Number of sources to retrieve

        Returns:
            EnhancedResponse with inline citations and hierarchical metadata
        """
        # Phase 1: Retrieve documents
        documents = self.retrieve_documents(query, k=k)

        # Phase 2: Build context and generate
        context = self.build_context_from_documents(documents)
        answer = self.generate_answer(query, context)

        # Create enhanced response
        return ResponseFormatter.create_enhanced_response(
            query=query,
            answer=answer,
            sources=documents,
        )

    def query(self, question: str, metadata_filters: dict | None = None, k: int = 4):
        """Query the RAG chain with optional metadata filtering.

        Args:
            question: User query string
            metadata_filters: Optional dictionary of metadata filters
            k: Number of top documents to retrieve

        Returns:
            dict with 'result' and 'source_documents'
        """
        # Phase 1: Retrieve documents with optional metadata filtering
        source_docs = self.retrieve_documents(
            query=question, metadata_filters=metadata_filters, k=k
        )

        # Phase 2: Build context and generate answer
        context = self.build_context_from_documents(source_docs)
        answer = self.generate_answer(question, context)

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

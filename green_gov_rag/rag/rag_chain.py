# rag/rag_chain.py

"""
RAG Chain for GreenGovRAG
-------------------------
Retrieval-Augmented Generation pipeline using FAISS + LLM (OpenAI / Bedrock)
Supports optional metadata filtering during retrieval.

1. Retrieve: Fetch top-K relevant document chunks using FAISS vector search.
2. Embed: Convert query into vector using HuggingFace/OpenAI embeddings.
3. Generate: Pass context + query to LLM (OpenAI/Bedrock) for answer generation.
4. Query with sources: Returns answer + metadata for transparency.
5. Extensible: Can add Bedrock or other LLMs later.
"""

from typing import List, Dict, Optional
from rag.vector_store import VectorStore
import numpy as np

# Optional: HuggingFace / OpenAI embeddings
from rag.embeddings import ChunkEmbedder

# Optional: LLM client wrappers
import os
import openai

class RAGChain:
    def __init__(self,
                 vector_store: VectorStore,
                 embedder: Optional[ChunkEmbedder] = None,
                 llm_provider: str = "openai",
                 llm_model: str = "gpt-4",
                 top_k: int = 5):
        """
        Initialize RAG Chain.

        :param vector_store: VectorStore instance
        :param embedder: ChunkEmbedder instance
        :param llm_provider: 'openai' or 'bedrock' (future)
        :param llm_model: model name
        :param top_k: number of retrieved chunks to pass to LLM
        """
        self.vector_store = vector_store
        self.embedder = embedder or ChunkEmbedder()
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.top_k = top_k

        if llm_provider == "openai":
            openai.api_key = os.environ.get("OPENAI_API_KEY")

    def retrieve(self, query: str) -> List[Dict]:
        """
        Retrieve top_k relevant chunks for the query.
        """
        query_embedding = self.embedder.embed_query(query)
        results = self.vector_store.store.search(query_embedding, top_k=self.top_k)
        return results

    def generate_answer(self, query: str) -> str:
        """
        Generate answer using retrieved context and LLM.
        """
        retrieved = self.retrieve(query)
        context = "\n".join([r["metadata"].get("source", "") + ": " + r["metadata"].get("content", "")
                             for r in retrieved])

        prompt = f"Answer the query based on the following context:\n{context}\n\nQuery: {query}\nAnswer:"

        if self.llm_provider == "openai":
            response = openai.ChatCompletion.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )
            answer = response.choices[0].message["content"]
            return answer
        else:
            # Placeholder for Bedrock or other LLMs
            return "LLM provider not implemented."

    def query_with_sources(self, query: str) -> Dict:
        """
        Return both the answer and the retrieved sources for transparency.
        """
        retrieved = self.retrieve(query)
        answer = self.generate_answer(query)
        return {
            "query": query,
            "answer": answer,
            "sources": retrieved
        }

    def query(self, question: str, metadata_filters: Optional[Dict] = None, k: int = 4):
        """
        Query the RAG chain with optional metadata filtering.
        :param question: User query string
        :param metadata_filters: Optional dictionary of metadata filters
        :param k: Number of top documents to retrieve
        :return: dict with 'result' and 'source_documents'
        """
        # If filters are provided, create a filtered retriever
        if metadata_filters:
            retriever = lambda q: self.vector_store.similarity_search(
                q, k=k, metadata_filters=metadata_filters
            )
        else:
            retriever = self.vector_store.store.as_retriever(search_kwargs={"k": k})

        # Execute the chain
        result = self.chain.run(
            question,
            callbacks=None,
            return_only_outputs=True
        )

        # Attach filtered documents if applicable
        source_docs = retriever(question) if metadata_filters else result.get("source_documents", [])

        return {
            "result": result.get("result") if isinstance(result, dict) else result,
            "source_documents": source_docs
        }


if __name__ == "__main__":
    from rag.vector_store import VectorStore
    from rag.embeddings import ChunkEmbedder

    # Quick demo
    store = VectorStore(
        index_path="faiss_index",
        embeddings=ChunkEmbedder(
            provider="huggingface", model_name="sentence-transformers/all-MiniLM-L6-v2"
        ).embedder
    )
    embedder = ChunkEmbedder()
    rag_chain = RAGChain(vector_store=store, embedder=embedder)

    query = "What are the native vegetation clearance rules in South Australia?"
    result = rag_chain.query_with_sources(query)
    print(result)

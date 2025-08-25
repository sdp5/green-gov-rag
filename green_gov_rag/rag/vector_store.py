# rag/vector_store.py

"""
Vector Store for GreenGovRAG
-----------------------------
Handles storing, retrieving, and filtering document embeddings for RAG.

1. FAISS backend for fast similarity search.
2. Metadata filtering support: Use metadata_filters in similarity_search.
3. Stores metadata alongside embeddings.
4. Persistent storage: index + metadata saved to disk.
5. Supports additions and searches.
6. Easy to integrate into your RAG chain.
"""

# rag/vector_store.py

"""
Vector Store Wrapper for GreenGovRAG
------------------------------------

"""

from typing import Dict, List, Optional

from langchain.docstore.document import Document
from langchain.embeddings.base import Embeddings
from langchain.vectorstores import FAISS

from .filters import filter_by_metadata


class VectorStore:
    def __init__(self, embeddings: Embeddings, index_path: Optional[str] = None):
        """
        Initialize the vector store. If index_path exists, load the FAISS index.
        :param embeddings: LangChain Embeddings instance (OpenAI/HuggingFace/Bedrock)
        :param index_path: Optional path to persisted FAISS index
        """
        self.embeddings = embeddings
        if index_path:
            self.store = FAISS.load_local(index_path, embeddings)
        else:
            self.store = FAISS(embedding_function=embeddings)
        self.index_path = index_path

    def add_documents(self, docs: List[Document]):
        """
        Add documents to the vector store.
        :param docs: List of LangChain Document objects
        """
        self.store.add_documents(docs)
        if self.index_path:
            self.store.save_local(self.index_path)

    def build_store(self, chunks: List[Dict]):
        """
        Build vector store from list of chunks.
        Each chunk should be:
        {"content": str, "metadata": dict}
        """
        documents = [
            Document(page_content=chunk["content"], metadata=chunk.get("metadata", {}))
            for chunk in chunks
        ]
        self.store = FAISS.from_documents(documents, self.embeddings)

    def add_chunks(self, chunks: List[Dict]):
        """
        Add more chunks to existing store.
        """
        if self.store is None:
            self.build_store(chunks)
            return

        documents = [
            Document(page_content=chunk["content"], metadata=chunk.get("metadata", {}))
            for chunk in chunks
        ]
        self.store.add_documents(documents)

    def list_metadata(self):
        """
        Return a list of metadata dictionaries for all stored embeddings.
        """
        return [
            doc["metadata"] for doc in self.store
        ]  # assuming `self.store` holds {'embedding': ..., 'metadata': ...}

    def similarity_search(
        self, query: str, k: int = 4, metadata_filters: Optional[Dict] = None
    ) -> List[Document]:
        """
        Perform similarity search with optional metadata filtering.
        :param query: Query string
        :param k: Number of top documents to return
        :param metadata_filters: Dictionary of metadata to filter on
        :return: List of LangChain Document objects
        """
        if self.store is None:
            raise ValueError("Vector store not initialized.")

        # Perform initial similarity search
        results = self.store.similarity_search(query, k=k, filters=metadata_filters)

        # If filters provided, apply them
        if metadata_filters:
            # Convert Document objects to dicts for filtering
            docs_with_meta = [
                {"content": doc.page_content, "metadata": doc.metadata} for doc in results
            ]
            filtered_docs_dict = filter_by_metadata(docs_with_meta, metadata_filters)

            # Convert back to Document objects
            results = [
                Document(page_content=d["content"], metadata=d["metadata"])
                for d in filtered_docs_dict
            ]

        return results

    def persist(self, path: Optional[str] = None):
        """
        Persist FAISS index locally
        """
        save_path = path or self.index_path
        if save_path:
            self.store.save_local(save_path)

    def load(self, path: str):
        self.store = FAISS.load_local(path, self.embeddings)


if __name__ == "__main__":
    # Quick demo
    # from rag.embeddings import ChunkEmbedder
    # from etl.chunker import TextChunker
    #
    # sample_texts = ["LangChain simplifies building AI applications."]
    # text_chunker = TextChunker(chunk_size=512, chunk_overlap=50)
    # chunks = []
    # for text in sample_texts:
    #     chunks.extend([{"content": c, "metadata": {"source": "demo"}} for c in text_chunker.chunk_text(text)])
    #
    # embedder = ChunkEmbedder(provider="huggingface")
    # embedded = embedder.embed_chunks(chunks)
    #
    # store = FAISS.from_documents(
    #     [doc["content"] for doc in embedded],
    #     embedder.embedder,  # your HuggingFace or Bedrock embedding function
    #     metadatas=[doc["metadata"] for doc in embedded]
    # )
    # store.add_documents(embedded)
    #
    # # Search with the first embedding
    # results = store.search(embedded[0]["embedding"], top_k=3)
    # print("Search results:", results)

    from rag.embeddings import ChunkEmbedder  # your embeddings wrapper

    # sample chunks
    chunks = [
        {
            "content": "This is a test document about SA native vegetation.",
            "metadata": {"region": "SA", "topic": "vegetation"},
        },
        {
            "content": "NSW requires biodiversity offsets for land clearing.",
            "metadata": {"region": "NSW", "topic": "biodiversity"},
        },
    ]

    embeddings = (
        ChunkEmbedder().embedder
    )  # Initialize your embeddings provider (HuggingFace, Bedrock, etc.)
    store = VectorStore(embeddings=embeddings)
    store.build_store(chunks)

    # Retrieve chunks with optional metadata filtering
    results = store.similarity_search(
        query="What are vegetation clearance rules in SA?", k=3, metadata_filters={"region": "SA"}
    )

    for r in results:
        print(r.page_content, r.metadata)

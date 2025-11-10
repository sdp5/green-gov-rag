# rag/embeddings.py

"""Embeddings module.

Generate vector embeddings for document chunks using either
AWS Bedrock LLM or HuggingFace embedding models.

1. Supports dual embedding providers:
    - HuggingFace (sentence-transformers)
    - AWS Bedrock (via OpenAI-compatible API)
2. Takes chunk dicts with content + metadata.
3. Returns dicts with embedding included.
4. Easily integrated into your ETL pipeline after chunker.py.

Now uses centralized settings from green_gov_rag.config
"""

from __future__ import annotations

# Optional: OpenAI-style API (for Bedrock, OpenAI API compatible)
from langchain_community.embeddings import OpenAIEmbeddings

# Optional: Hugging Face
from langchain_huggingface import HuggingFaceEmbeddings

from green_gov_rag.config import settings


class ChunkEmbedder:
    def __init__(self, provider: str = "bedrock", model_name: str | None = None):
        """Initialize embedding generator.

        :param provider: "bedrock" or "huggingface"
        :param model_name: Name of the model to use.
        """
        self.provider = provider.lower()
        if self.provider == "huggingface":
            self.model_name = model_name or settings.embedding_model
            self.embedder: HuggingFaceEmbeddings | OpenAIEmbeddings = (
                HuggingFaceEmbeddings(model_name=self.model_name)
            )
        elif self.provider == "bedrock":
            bedrock_model = model_name or settings.bedrock_model_id
            self.model_name = bedrock_model if bedrock_model else "anthropic.claude-v2"
            self.embedder = OpenAIEmbeddings(model=self.model_name)
        else:
            msg = "provider must be 'bedrock' or 'huggingface'"
            raise ValueError(msg)

    def embed_chunks(
        self, chunks: list[dict], batch_size: int = 100, show_progress: bool = True
    ) -> list[dict]:
        """Generate embeddings for a list of chunk dictionaries using batching.

        :param chunks: List of dicts with at least {"content": str, "metadata": dict}
        :param batch_size: Number of chunks to embed per batch (default: 100)
        :param show_progress: Show progress information (default: True)
        :return: List of dicts with {"content", "metadata", "embedding"}
        """
        embedded_chunks = []

        # Filter out empty chunks
        valid_chunks = [
            chunk
            for chunk in chunks
            if chunk.get("content") and str(chunk.get("content")).strip()
        ]

        if not valid_chunks:
            return []

        total_batches = (len(valid_chunks) + batch_size - 1) // batch_size

        for i in range(0, len(valid_chunks), batch_size):
            batch = valid_chunks[i : i + batch_size]
            batch_num = i // batch_size + 1

            # Extract texts and metadata
            texts = [chunk["content"] for chunk in batch]
            metadatas = [chunk.get("metadata", {}) for chunk in batch]

            # Generate embeddings for entire batch at once
            vectors = self.embedder.embed_documents(texts)

            # Combine results
            for text, metadata, vector in zip(texts, metadatas, vectors):
                embedded_chunks.append(
                    {"content": text, "metadata": metadata, "embedding": vector}
                )

            if show_progress and batch_num % 10 == 0:
                print(
                    f"   Processed batch {batch_num}/{total_batches} ({len(embedded_chunks)} chunks)"
                )

        if show_progress:
            print(
                f"   Completed: {len(embedded_chunks)} chunks embedded in {total_batches} batches"
            )

        return embedded_chunks


if __name__ == "__main__":
    from etl.chunker import TextChunker

    # Demo
    sample_texts = [
        "LangChain simplifies building AI applications with LLMs. "
        "You can chain prompts, models, and outputs easily.",
    ]
    text_chunker = TextChunker()
    chunks = []
    for text in sample_texts:
        chunks.extend(
            [
                {"content": c, "metadata": {"source": "demo"}}
                for c in text_chunker.chunk_text(text)
            ],
        )

    embedder = ChunkEmbedder(provider="huggingface")
    embedded = embedder.embed_chunks(chunks)

    for i, e in enumerate(embedded, 1):
        print(f"Chunk {i} embedding length: {len(e['embedding'])}")

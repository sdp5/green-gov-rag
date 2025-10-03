# rag/embeddings.py

"""Embeddings module
-----------------
Generate vector embeddings for document chunks using either
AWS Bedrock LLM or HuggingFace embedding models.

1. Supports dual embedding providers:
    - HuggingFace (sentence-transformers)
    - AWS Bedrock (via OpenAI-compatible API)
2. Takes chunk dicts with content + metadata.
3. Returns dicts with embedding included.
4. Easily integrated into your ETL pipeline after chunker.py.
"""

import os

# Optional: Hugging Face
# Optional: OpenAI-style API (for Bedrock, OpenAI API compatible)
from langchain.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings


class ChunkEmbedder:
    def __init__(self, provider: str = "bedrock", model_name: str = None):
        """Initialize embedding generator.

        :param provider: "bedrock" or "huggingface"
        :param model_name: Name of the model to use.
        """
        self.provider = provider.lower()
        if self.provider == "huggingface":
            self.model_name = model_name or "sentence-transformers/all-MiniLM-L6-v2"
            self.embedder = HuggingFaceEmbeddings(model_name=self.model_name)
        elif self.provider == "bedrock":
            bedrock_model = model_name or os.getenv("BEDROCK_MODEL_ID")
            self.model_name = bedrock_model if bedrock_model else "anthropic.claude-v2"
            self.embedder = OpenAIEmbeddings(model=self.model_name)
        else:
            raise ValueError("provider must be 'bedrock' or 'huggingface'")

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """Generate embeddings for a list of chunk dictionaries.

        :param chunks: List of dicts with at least {"content": str, "metadata": dict}
        :return: List of dicts with {"content", "metadata", "embedding"}
        """
        embedded_chunks = []
        for chunk in chunks:
            text = chunk.get("content")
            metadata = chunk.get("metadata", {})

            if not text or not text.strip():
                continue

            vector = self.embedder.embed_query(text)
            embedded_chunks.append({"content": text, "metadata": metadata, "embedding": vector})
        return embedded_chunks


if __name__ == "__main__":
    from etl.chunker import TextChunker

    # Demo
    sample_texts = [
        "LangChain simplifies building AI applications with LLMs. "
        "You can chain prompts, models, and outputs easily."
    ]
    text_chunker = TextChunker()
    chunks = []
    for text in sample_texts:
        chunks.extend(
            [{"content": c, "metadata": {"source": "demo"}} for c in text_chunker.chunk_text(text)]
        )

    embedder = ChunkEmbedder(provider="huggingface")
    embedded = embedder.embed_chunks(chunks)

    for i, e in enumerate(embedded, 1):
        print(f"Chunk {i} embedding length: {len(e['embedding'])}")

# rag/embeddings.py

"""Embeddings module.

Generate vector embeddings for document chunks using one of:
    - HuggingFace (sentence-transformers, local)
    - Azure OpenAI (text-embedding-3-large, cloud)
    - OpenAI (text-embedding-3-large, cloud)
    - AWS Bedrock (via OpenAI-compatible API)

Takes chunk dicts with content + metadata.
Returns dicts with embedding included.

Uses centralized settings from green_gov_rag.config
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from green_gov_rag.config import settings


def create_embeddings(
    provider: str | None = None,
    model_name: str | None = None,
) -> Embeddings:
    """Create a LangChain Embeddings instance for the given provider.

    This is the single source of truth for constructing embeddings objects.
    All code paths (CLI, vector store factory, embedding service) should
    use this function so the provider/model configuration is consistent.

    Args:
        provider: Embedding provider string. Defaults to settings.embedding_provider.
        model_name: Model name / deployment name. Defaults to settings.embedding_model.

    Returns:
        A LangChain Embeddings instance.
    """
    provider = (provider or settings.embedding_provider).lower()
    model_name = model_name or settings.embedding_model

    if provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name)

    if provider == "azure_openai":
        from langchain_openai import AzureOpenAIEmbeddings

        deployment = settings.azure_openai_embedding_deployment or model_name
        return AzureOpenAIEmbeddings(
            model=model_name,
            azure_deployment=deployment,
            azure_endpoint=settings.azure_openai_endpoint or "",
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=model_name,
            openai_api_key=settings.openai_api_key,
        )

    if provider == "bedrock":
        from langchain_community.embeddings import OpenAIEmbeddings as BedrockEmbeddings

        bedrock_model = model_name or settings.bedrock_model_id or "anthropic.claude-v2"
        return BedrockEmbeddings(model=bedrock_model)

    msg = f"Unsupported embedding provider: {provider}. Use: huggingface, azure_openai, openai, bedrock"
    raise ValueError(msg)


class ChunkEmbedder:
    def __init__(self, provider: str | None = None, model_name: str | None = None):
        """Initialize embedding generator.

        :param provider: Embedding provider. Defaults to settings.embedding_provider.
        :param model_name: Name of the model to use. Defaults to settings.embedding_model.
        """
        self.provider = (provider or settings.embedding_provider).lower()
        self.model_name = model_name or settings.embedding_model
        self.embedder: Embeddings = create_embeddings(self.provider, self.model_name)

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

    # Demo — uses whatever provider/model is configured in settings / .env
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

    embedder = ChunkEmbedder()
    embedded = embedder.embed_chunks(chunks)

    for i, e in enumerate(embedded, 1):
        print(f"Chunk {i} embedding length: {len(e['embedding'])}")

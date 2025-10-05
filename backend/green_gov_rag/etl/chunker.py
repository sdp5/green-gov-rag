# etl/chunker.py

"""Chunker module for splitting documents into smaller text chunks using LangChain text splitters.

1. Uses RecursiveCharacterTextSplitter (handles paragraphs → sentences → words).
2. Configurable chunk_size, chunk_overlap, and separators.
3. Skips empty/whitespace-only texts.
4. Returns flat list of chunks for indexing or embeddings.
"""

from __future__ import annotations

from typing import Any

from langchain.text_splitter import RecursiveCharacterTextSplitter, TokenTextSplitter

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 100


class TextChunker:
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        splitter_type: str = "recursive",
    ):
        """Initialize text chunker.
        :param chunk_size: Max characters or tokens per chunk
        :param chunk_overlap: Overlap between chunks
        :param splitter_type: "recursive" or "token".
        """
        self.splitter_type = splitter_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        if splitter_type == "recursive":
            self.splitter: RecursiveCharacterTextSplitter | TokenTextSplitter = (
                RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", " ", ""],
                )
            )
        elif splitter_type == "token":
            self.splitter = TokenTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        else:
            msg = f"Unsupported splitter_type: {splitter_type}"
            raise ValueError(msg)

    def chunk_text(self, text: str) -> list[str]:
        """Split raw text into chunks."""
        return self.splitter.split_text(text)

    def chunk_docs(self, docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split list of documents into smaller chunks.
        Each doc should have: {"content": str, "metadata": dict}.
        """
        chunked_docs = []
        for doc in docs:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})

            chunks = self.chunk_text(content)
            for i, chunk in enumerate(chunks):
                chunked_docs.append(
                    {"content": chunk, "metadata": {**metadata, "chunk_id": i}},
                )
        return chunked_docs

    def chunk_with_hierarchy(
        self,
        hierarchical_chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Chunk hierarchical documents while preserving section metadata.

        For documents parsed with HierarchicalPDFParser, this preserves
        section hierarchy, page numbers, and structural context.

        Args:
        ----
            hierarchical_chunks: Chunks from HierarchicalPDFParser with metadata

        Returns:
        -------
            List of smaller chunks with preserved hierarchical metadata

        """
        chunked_docs = []

        for doc_chunk in hierarchical_chunks:
            content = doc_chunk.get("content", "")
            metadata = doc_chunk.get("metadata", {})

            # Split content into smaller chunks
            text_chunks = self.chunk_text(content)

            # Preserve hierarchical metadata for each sub-chunk
            for i, text_chunk in enumerate(text_chunks):
                chunked_docs.append(
                    {
                        "content": text_chunk,
                        "metadata": {
                            **metadata,  # Preserve all hierarchical metadata
                            "sub_chunk_id": i,  # Track sub-chunks within section
                            # Update chunk_id to be unique across all chunks
                            "chunk_id": f"{metadata.get('chunk_id', 0)}_{i}",
                        },
                    },
                )

        return chunked_docs


# Module-level convenience functions for backward compatibility
def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    splitter_type: str = "recursive",
) -> list[str]:
    """Convenience function to chunk text without creating a TextChunker instance."""
    # Ensure chunk_overlap is not larger than chunk_size
    actual_overlap = min(chunk_overlap, chunk_size - 1) if chunk_size > 1 else 0
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=actual_overlap,
        splitter_type=splitter_type,
    )
    return chunker.chunk_text(text)

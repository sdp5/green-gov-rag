"""CLI commands for GreenGovRAG."""

# cli.py
from pathlib import Path

import typer

from green_gov_rag.etl import chunker, ingest, loader
from green_gov_rag.rag import embeddings, rag_chain, vector_store

app = typer.Typer(help="GreenGovRAG CLI: ETL + RAG pipeline management")


@app.command()
def ingest_docs(config_path: str = "configs/documents_config.yml", output_dir: str = "data/raw"):
    """Download all documents listed in documents_config.yml
    """
    typer.echo(f"Loading config from {config_path}...")
    docs = loader.load_documents_config(config_path)
    ingest.download_documents(docs, output_dir)  # type: ignore[attr-defined]
    typer.echo(f"Downloaded documents to {output_dir}")


@app.command()
def parse_docs(input_dir: str = "data/raw", parsed_dir: str = "data/processed"):
    """Parse PDFs and HTML files into plain text
    """
    typer.echo(f"Parsing documents from {input_dir}...")
    for doc_file in Path(input_dir).glob("*"):
        text = ingest.dispatch_parser(str(doc_file))  # type: ignore[attr-defined]
        out_file = Path(parsed_dir) / (doc_file.stem + ".txt")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(text)
    typer.echo(f"Parsed text saved to {parsed_dir}")


@app.command()
def chunk_docs(input_dir: str = "data/processed", chunked_dir: str = "data/processed/chunks"):
    """Chunk parsed text using LangChain TextSplitters
    """
    typer.echo(f"Chunking documents from {input_dir}...")
    for txt_file in Path(input_dir).glob("*.txt"):
        text = txt_file.read_text()
        chunks = chunker.chunk_text(text)  # type: ignore[attr-defined]
        out_file = Path(chunked_dir) / (txt_file.stem + "_chunks.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        import json

        with open(out_file, "w") as f:
            json.dump(chunks, f)
    typer.echo(f"Chunked documents saved to {chunked_dir}")


@app.command()
def embed_docs(
    chunked_dir: str = "data/processed/chunks",
    embedding_cache_dir: str = "data/processed/embeddings",
    model_name: str = "amazon/bedrock",
):
    """Embed text chunks using RAG embeddings (Bedrock / HuggingFace)
    """
    typer.echo(f"Embedding chunks from {chunked_dir} using {model_name}...")
    for chunk_file in Path(chunked_dir).glob("*_chunks.json"):
        import json

        with open(chunk_file) as f:
            chunks = json.load(f)
        embedded = embeddings.embed_chunks(chunks, model_name=model_name)  # type: ignore[attr-defined]
        out_file = Path(embedding_cache_dir) / (chunk_file.stem + "_embeddings.json")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w") as f:
            json.dump(embedded, f)
    typer.echo(f"Embeddings saved to {embedding_cache_dir}")


@app.command()
def build_vector_store(
    embedding_dir: str = "data/processed/embeddings",
    store_path: str = "data/vector_store/faiss.index",
):
    """Build vector store (FAISS / Qdrant) from embeddings
    """
    typer.echo(f"Building vector store from {embedding_dir}...")
    store = vector_store.build_vector_store(embedding_dir)  # type: ignore[attr-defined]
    vector_store.save_vector_store(store, store_path)  # type: ignore[attr-defined]
    typer.echo(f"Vector store saved to {store_path}")


@app.command()
def evaluate_query(
    query: str, store_path: str = "data/vector_store/faiss.index", metadata_filters: str | None = None
):
    """Query RAG chain against the vector store
    """
    store = vector_store.load_vector_store(store_path)  # type: ignore[attr-defined]
    rag = rag_chain.RAGChain(store)

    filters = None
    if metadata_filters:
        import json

        filters = json.loads(metadata_filters)

    answer, sources = rag.query(query, metadata_filters=filters)
    typer.echo("\nAnswer:\n" + answer)
    typer.echo("\nSources:")
    for src in sources:
        typer.echo(f"- {src}")


if __name__ == "__main__":
    app()

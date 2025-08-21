import yaml
from pathlib import Path

def load_documents_config(config_path: str = "configs/documents_config.yml"):
    """
    Load document metadata from YAML config.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_path} not found.")

    with open(config_file, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("documents", [])

def get_document_sources():
    """
    Returns a list of all source URLs for ingestion.
    """
    documents = load_documents_config()
    sources = []
    for doc in documents:
        urls = doc.get("download_urls", [])
        sources.extend(urls)
    return sources

if __name__ == "__main__":
    docs = load_documents_config()
    print(f"Found {len(docs)} documents in config.")

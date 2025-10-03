from pathlib import Path

import yaml


def load_documents_config(config_path: str = "configs/documents_config.yml"):
    """Load document metadata from YAML config.
    """
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file {config_path} not found.")

    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("documents", [])


def get_document_sources():
    """Returns a list of all source URLs for ingestion.
    """
    documents = load_documents_config()
    sources = []
    for doc in documents:
        urls = doc.get("download_urls", [])
        sources.extend(urls)
    return sources


def load_yaml(file_path: str) -> dict:
    """Load YAML file and return as dictionary.

    :param file_path: Path to YAML file
    :return: Parsed YAML content as dictionary
    """
    yaml_file = Path(file_path)
    if not yaml_file.exists():
        raise FileNotFoundError(f"YAML file {file_path} not found.")

    with open(yaml_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    docs = load_documents_config()
    print(f"Found {len(docs)} documents in config.")

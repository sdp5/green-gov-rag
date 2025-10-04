from __future__ import annotations

from pathlib import Path

import yaml

from green_gov_rag.etl.sources.base import DocumentSource
from green_gov_rag.etl.sources.factory import DocumentSourceFactory


def load_documents_config(config_path: str = "configs/documents_config.yml"):
    """Load document metadata from YAML config.

    This function maintains backward compatibility with the original API
    while supporting the new plugin-based architecture.

    Args:
        config_path: Path to documents configuration file

    Returns:
        List of document configuration dictionaries
    """
    config_file = Path(config_path)
    if not config_file.exists():
        msg = f"Config file {config_path} not found."
        raise FileNotFoundError(msg)

    with open(config_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("documents", [])


def load_document_sources(
    config_path: str = "configs/documents_config.yml",
) -> list[DocumentSource]:
    """Load document sources using the plugin-based architecture.

    This is the new API that returns DocumentSource objects instead of
    raw configuration dictionaries.

    Args:
        config_path: Path to documents configuration file

    Returns:
        List of DocumentSource plugin instances

    Example:
        >>> sources = load_document_sources()
        >>> for source in sources:
        ...     metadata = source.get_metadata()
        ...     urls = source.get_download_urls()
        ...     validation = source.validate()
    """
    configs = load_documents_config(config_path)
    factory = DocumentSourceFactory()
    return factory.create_sources_from_list(configs)


def get_document_sources():
    """Returns a list of all source URLs for ingestion.

    This function maintains backward compatibility with the original API.

    Returns:
        List of download URLs
    """
    documents = load_documents_config()
    sources = []
    for doc in documents:
        urls = doc.get("download_urls", [])
        sources.extend(urls)
    return sources


def get_document_sources_by_type(source_type: str) -> list[DocumentSource]:
    """Get document sources filtered by type.

    Args:
        source_type: Source type identifier (e.g., 'federal_legislation')

    Returns:
        List of DocumentSource instances matching the type

    Example:
        >>> federal_sources = get_document_sources_by_type('federal_legislation')
        >>> emissions_sources = get_document_sources_by_type('emissions_reporting')
    """
    sources = load_document_sources()
    return [s for s in sources if s.get_source_type() == source_type]


def get_document_sources_by_jurisdiction(jurisdiction: str) -> list[DocumentSource]:
    """Get document sources filtered by jurisdiction.

    Args:
        jurisdiction: Jurisdiction filter ('federal', 'state', 'local')

    Returns:
        List of DocumentSource instances matching the jurisdiction

    Example:
        >>> federal_sources = get_document_sources_by_jurisdiction('federal')
        >>> local_sources = get_document_sources_by_jurisdiction('local')
    """
    sources = load_document_sources()
    return [s for s in sources if s.get_metadata().get("jurisdiction") == jurisdiction]


def load_yaml(file_path: str) -> dict:
    """Load YAML file and return as dictionary.

    :param file_path: Path to YAML file
    :return: Parsed YAML content as dictionary
    """
    yaml_file = Path(file_path)
    if not yaml_file.exists():
        msg = f"YAML file {file_path} not found."
        raise FileNotFoundError(msg)

    with open(yaml_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    docs = load_documents_config()
    print(f"Found {len(docs)} documents in config.")

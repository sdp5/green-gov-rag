# rag/filters.py

"""Metadata Filters for RAG.

Provides helper functions to filter documents/chunks in a vector store
based on metadata such as jurisdiction, region, category, or topic.

1. Flexible filtering:
    - Can filter by single value ("jurisdiction": "state") or multiple options ("region": ["SA", "NSW"]).
2. Works with vector stores:
    - You can wrap this around VectorStore’s .docs list before performing RAG retrieval.
3. Plug-and-play:
    - Can be imported in rag/agent_tools.py or directly in your RAG chain for pre-filtering.
"""

from __future__ import annotations


def filter_by_metadata(documents: list[dict], filters: dict) -> list[dict]:
    """Filters a list of document chunks based on metadata criteria.

    Performs case-insensitive string matching for all filter values.
    Special handling for LGA filtering via spatial_metadata.lga_names array.

    :param documents: List of document chunks, each chunk is a dict with 'metadata' key
    :param filters: Dictionary with metadata keys and expected values
                    Example: {"jurisdiction": "state", "region": "South Australia"}
                    Special key "lga_names" filters by spatial_metadata.lga_names array
    :return: Filtered list of document chunks
    """
    filtered_docs = []

    for doc in documents:
        metadata = doc.get("metadata", {})
        match = True
        for key, value in filters.items():
            # Special handling for LGA names (nested in spatial_metadata)
            if key == "lga_names":
                spatial_metadata = metadata.get("spatial_metadata", {})
                lga_names = spatial_metadata.get("lga_names", [])
                # Check if any of the requested LGAs match any in the document
                if isinstance(value, list):
                    # Normalize for comparison
                    normalized_filters = [
                        v.lower() if isinstance(v, str) else v for v in value
                    ]
                    normalized_lgas = [
                        lga.lower() if isinstance(lga, str) else lga
                        for lga in lga_names
                    ]
                    # Check if any filter LGA matches any document LGA
                    if not any(lga in normalized_lgas for lga in normalized_filters):
                        match = False
                        break
                else:
                    # Single LGA
                    normalized_value = (
                        value.lower() if isinstance(value, str) else value
                    )
                    normalized_lgas = [
                        lga.lower() if isinstance(lga, str) else lga
                        for lga in lga_names
                    ]
                    if normalized_value not in normalized_lgas:
                        match = False
                        break
            # Skip region_specified (used only for filters_applied transparency)
            elif key == "region_specified":
                continue
            else:
                # Standard metadata filtering
                metadata_value = metadata.get(key)

                # Support list of values for a key (OR condition)
                if isinstance(value, list):
                    # Normalize both filter values and metadata value for comparison
                    normalized_filters = [
                        v.lower() if isinstance(v, str) else v for v in value
                    ]
                    normalized_meta = (
                        metadata_value.lower()
                        if isinstance(metadata_value, str)
                        else metadata_value
                    )
                    if normalized_meta not in normalized_filters:
                        match = False
                        break
                else:
                    # Single value - case-insensitive comparison for strings
                    if isinstance(value, str) and isinstance(metadata_value, str):
                        if value.lower() != metadata_value.lower():
                            match = False
                            break
                    elif metadata_value != value:
                        match = False
                        break
        if match:
            filtered_docs.append(doc)

    return filtered_docs


# Example usage
if __name__ == "__main__":
    documents = [
        {
            "content": "Doc1 text",
            "metadata": {
                "jurisdiction": "state",
                "region": "SA",
                "topic": "biodiversity",
            },
        },
        {
            "content": "Doc2 text",
            "metadata": {
                "jurisdiction": "federal",
                "region": "Australia",
                "topic": "emissions",
            },
        },
        {
            "content": "Doc3 text",
            "metadata": {"jurisdiction": "state", "region": "NSW", "topic": "planning"},
        },
    ]

    filters = {"jurisdiction": "state"}
    filtered = filter_by_metadata(documents, filters)
    print("Filtered Docs:")
    for doc in filtered:
        print(doc["metadata"])

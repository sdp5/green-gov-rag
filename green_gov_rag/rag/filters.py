# rag/filters.py

"""Metadata Filters for RAG
------------------------
Provides helper functions to filter documents/chunks in a vector store
based on metadata such as jurisdiction, region, category, or topic.

1. Flexible filtering:
    - Can filter by single value ("jurisdiction": "state") or multiple options ("region": ["SA", "NSW"]).
2. Works with vector stores:
    - You can wrap this around VectorStore’s .docs list before performing RAG retrieval.
3. Plug-and-play:
    - Can be imported in rag/agent_tools.py or directly in your RAG chain for pre-filtering.
"""



def filter_by_metadata(documents: list[dict], filters: dict) -> list[dict]:
    """Filters a list of document chunks based on metadata criteria.

    :param documents: List of document chunks, each chunk is a dict with 'metadata' key
    :param filters: Dictionary with metadata keys and expected values
                    Example: {"jurisdiction": "state", "region": "South Australia"}
    :return: Filtered list of document chunks
    """
    filtered_docs = []

    for doc in documents:
        metadata = doc.get("metadata", {})
        match = True
        for key, value in filters.items():
            # Support list of values for a key
            if isinstance(value, list):
                if metadata.get(key) not in value:
                    match = False
                    break
            elif metadata.get(key) != value:
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
            "metadata": {"jurisdiction": "state", "region": "SA", "topic": "biodiversity"},
        },
        {
            "content": "Doc2 text",
            "metadata": {"jurisdiction": "federal", "region": "Australia", "topic": "emissions"},
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

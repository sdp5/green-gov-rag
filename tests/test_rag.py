import pytest
from rag import embeddings, vector_store, rag_chain

SAMPLE_CHUNKS = [
    {"content": "Carbon emissions report for NSW", "metadata": {"region": "NSW"}},
    {"content": "Biodiversity conservation guidelines", "metadata": {"region": "SA"}},
]

@pytest.fixture
def embedded_chunks():
    # Embed with dummy embeddings (mocked)
    return embeddings.embed_chunks(SAMPLE_CHUNKS, model_name="mock")


def test_vector_store_build(embedded_chunks):
    store = vector_store.build_vector_store(embedded_chunks)
    assert store is not None
    assert hasattr(store, "similarity_search")
    results = store.similarity_search("Carbon report", k=1)
    assert len(results) <= 1


def test_rag_chain_basic(embedded_chunks):
    store = vector_store.build_vector_store(embedded_chunks)
    rag = rag_chain.RAGChain(store, model_name="mock")
    result = rag.run("Carbon report")
    assert isinstance(result, str)


def test_rag_chain_with_filters(embedded_chunks):
    store = vector_store.build_vector_store(embedded_chunks)
    rag = rag_chain.RAGChain(store, model_name="mock")
    # Filter by region
    result = rag.run("Biodiversity", metadata_filters={"region": "SA"})
    assert isinstance(result, str)
    # Should ignore irrelevant regions
    result2 = rag.run("Biodiversity", metadata_filters={"region": "NSW"})
    assert isinstance(result2, str)


def test_embeddings_output_shape():
    embedded = embeddings.embed_chunks(SAMPLE_CHUNKS, model_name="mock")
    for e in embedded:
        assert "embedding" in e
        assert isinstance(e["embedding"], list)

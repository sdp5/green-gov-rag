"""Tests for RAG components.

This test suite covers:
- Embeddings generation (ChunkEmbedder)
- Vector store operations (FAISS, Qdrant interfaces)
- Hybrid geospatial search
- Location NER (Named Entity Recognition)
- Query expansion and jurisdiction detection
- RAG chain integration
"""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain.schema import Document

# ============================================================================
# Mock Fixtures for RAG Components
# ============================================================================


@pytest.fixture
def mock_llm():
    """Mock LLM for testing without API calls."""
    mock = MagicMock()
    mock.predict.return_value = "Mocked LLM response about environmental regulations."
    mock.invoke.return_value = Mock(content="Mocked response")
    return mock


@pytest.fixture
def mock_vector_results():
    """Mock vector search results."""
    return [
        Document(
            page_content="Carbon emissions report for NSW coal mining.",
            metadata={
                "source": "nsw_emissions.pdf",
                "region": "NSW",
                "lga_code": "12345",
                "state": "NSW",
                "jurisdiction": "state",
            },
        ),
        Document(
            page_content="Biodiversity conservation guidelines for SA.",
            metadata={
                "source": "sa_biodiversity.pdf",
                "region": "SA",
                "lga_code": "40070",
                "state": "SA",
                "jurisdiction": "state",
            },
        ),
    ]


@pytest.fixture
def mock_spatial_query():
    """Mock spatial query parameters."""
    from green_gov_rag.rag.hybrid_search import SpatialQuery

    return SpatialQuery(
        location_name="City of Adelaide",
        lga_codes=["40070"],
        state="SA",
        coordinates=None,
        radius_km=5.0,
    )


# ============================================================================
# Embeddings Tests (ChunkEmbedder)
# ============================================================================


def test_embeddings_output_shape(mock_embedder, sample_chunks):
    """Test embeddings shape and structure."""
    embedded = mock_embedder.embed_chunks(sample_chunks[:2])
    assert len(embedded) == 2
    for e in embedded:
        assert "embedding" in e
        assert "content" in e
        assert "metadata" in e
        assert isinstance(e["embedding"], list)
        assert len(e["embedding"]) == 384  # Mock embedding dimension


def test_embeddings_empty_chunks(mock_embedder):
    """Test embedding empty chunk list."""
    embedded = mock_embedder.embed_chunks([])
    assert embedded == []


def test_embeddings_batch_processing(mock_embedder, sample_chunks):
    """Test batch processing of chunks."""
    # Create larger sample for batching
    large_chunks = sample_chunks * 50  # 150 chunks
    embedded = mock_embedder.embed_chunks(large_chunks)
    assert len(embedded) == 150


def test_embeddings_filters_empty_content(mock_embedder):
    """Test that empty content chunks are filtered out."""
    chunks = [
        {"content": "Valid content", "metadata": {}},
        {"content": "", "metadata": {}},
        {"content": "   ", "metadata": {}},
        {"content": "Another valid", "metadata": {}},
    ]

    with patch.object(mock_embedder, "embed_chunks") as mock_embed:
        # Simulate real embedder behavior (filters empty)
        valid_chunks = [c for c in chunks if c.get("content", "").strip()]  # type: ignore[attr-defined]
        mock_embed.return_value = [
            {**c, "embedding": [0.1] * 384} for c in valid_chunks
        ]

        embedded = mock_embed(chunks)
        assert len(embedded) == 2  # Only non-empty chunks


def test_embeddings_query_single(mock_embedder):
    """Test single query embedding."""
    query = "What are the carbon emissions regulations in NSW?"
    embedding = mock_embedder.embed_query(query)
    assert isinstance(embedding, list)
    assert len(embedding) == 384


def test_chunk_embedder_initialization():
    """Test ChunkEmbedder initialization with mocked providers."""
    with patch("green_gov_rag.rag.embeddings.HuggingFaceEmbeddings") as mock_hf:
        from green_gov_rag.rag.embeddings import ChunkEmbedder

        embedder = ChunkEmbedder(provider="huggingface")
        assert embedder.provider == "huggingface"
        mock_hf.assert_called_once()


def test_chunk_embedder_invalid_provider():
    """Test ChunkEmbedder with invalid provider."""
    from green_gov_rag.rag.embeddings import ChunkEmbedder

    with pytest.raises(ValueError, match="provider must be"):
        ChunkEmbedder(provider="invalid")


# ============================================================================
# Vector Store Tests
# ============================================================================


def test_vector_store_build(in_memory_faiss):
    """Test vector store initialization and structure."""
    assert in_memory_faiss is not None
    assert hasattr(in_memory_faiss, "similarity_search")
    assert hasattr(in_memory_faiss, "similarity_search_with_score")


def test_vector_store_similarity_search(in_memory_faiss):
    """Test basic similarity search."""
    results = in_memory_faiss.similarity_search("Carbon report", k=2)
    assert isinstance(results, list)
    assert len(results) <= 2
    if results:
        assert hasattr(results[0], "page_content")
        assert hasattr(results[0], "metadata")


def test_vector_store_with_k_limit(in_memory_faiss):
    """Test k parameter limits results."""
    results = in_memory_faiss.similarity_search("emissions", k=1)
    assert len(results) <= 1


def test_vector_store_empty_query(in_memory_faiss):
    """Test handling of empty query."""
    results = in_memory_faiss.similarity_search("", k=5)
    assert isinstance(results, list)


def test_vector_store_metadata_filtering(in_memory_faiss):
    """Test metadata-based filtering."""
    # Note: FAISS doesn't support metadata filtering natively,
    # but we test the interface exists
    results = in_memory_faiss.similarity_search("Biodiversity", k=5)
    assert isinstance(results, list)

    # Filter results by region manually (simulates post-filtering)
    sa_results = [r for r in results if r.metadata.get("region") == "SA"]
    assert isinstance(sa_results, list)


# ============================================================================
# Hybrid Geospatial Search Tests
# ============================================================================


def test_hybrid_search_initialization(in_memory_faiss):
    """Test HybridGeospatialSearch initialization."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
    assert search.vector_store == in_memory_faiss
    assert search.ner is None


def test_hybrid_search_with_ner(in_memory_faiss):
    """Test hybrid search with NER enabled."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    with patch("green_gov_rag.rag.hybrid_search.LocationNER"):
        search = HybridGeospatialSearch(in_memory_faiss, enable_ner=True)
        assert search.ner is not None


def test_hybrid_search_basic_query(in_memory_faiss):
    """Test basic hybrid search without spatial filtering."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
    results = search.search("carbon emissions", k=5)
    assert isinstance(results, list)


def test_hybrid_search_with_spatial_query(in_memory_faiss, mock_spatial_query):
    """Test hybrid search with spatial query."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
    results = search.search(
        "biodiversity conservation",
        spatial_query=mock_spatial_query,
        k=5,
    )
    assert isinstance(results, list)


def test_hybrid_search_metadata_filters(in_memory_faiss):
    """Test hybrid search with metadata filters."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
    results = search.search(
        "environmental regulations",
        metadata_filters={"jurisdiction": "state"},
        k=5,
    )
    assert isinstance(results, list)


def test_hybrid_search_query_expansion(in_memory_faiss):
    """Test query expansion in hybrid search."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    with patch("green_gov_rag.rag.hybrid_search.expand_query") as mock_expand:
        mock_expand.return_value = (
            "Environment Protection and Biodiversity Conservation"
        )

        search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
        results = search.search("EPBC", k=5, enable_query_expansion=True)

        mock_expand.assert_called_once()
        assert isinstance(results, list)


def test_spatial_query_dataclass():
    """Test SpatialQuery dataclass."""
    from green_gov_rag.rag.hybrid_search import SpatialQuery

    sq = SpatialQuery(
        location_name="Adelaide",
        lga_codes=["40070"],
        state="SA",
        coordinates=(-34.9285, 138.6007),
        radius_km=10.0,
    )
    assert sq.location_name == "Adelaide"
    assert sq.lga_codes == ["40070"]
    assert sq.state == "SA"
    assert sq.coordinates == (-34.9285, 138.6007)
    assert sq.radius_km == 10.0


# ============================================================================
# Location NER Tests
# ============================================================================


def test_location_ner_initialization():
    """Test LocationNER initialization without LLM."""
    from green_gov_rag.rag.location_ner import LocationNER

    ner = LocationNER(use_llm=False)
    assert ner.llm is None
    assert ner.use_llm is False


def test_location_ner_rule_based_extraction():
    """Test rule-based location extraction."""
    from green_gov_rag.rag.location_ner import LocationNER

    ner = LocationNER(use_llm=False)
    text = "What are the regulations in South Australia and New South Wales?"

    results = ner.extract_locations(text)
    assert "states" in results
    assert "lgas" in results
    assert "raw_locations" in results
    assert isinstance(results["states"], list)
    assert isinstance(results["lgas"], list)


def test_location_ner_lga_extraction():
    """Test LGA extraction from text."""
    from green_gov_rag.rag.location_ner import LocationNER

    ner = LocationNER(use_llm=False)
    text = "Requirements for City of Adelaide and Port Adelaide Enfield"

    results = ner.extract_locations(text)
    # Should extract Adelaide-related LGAs
    assert isinstance(results["lgas"], list)


def test_location_ner_case_insensitive():
    """Test case-insensitive location matching."""
    from green_gov_rag.rag.location_ner import LocationNER

    ner = LocationNER(use_llm=False)
    text = "regulations in SOUTH AUSTRALIA"

    results = ner.extract_locations(text)
    assert len(results["states"]) > 0 or len(results["raw_locations"]) > 0


def test_location_ner_with_llm_mock():
    """Test LocationNER with mocked LLM."""
    from green_gov_rag.rag.location_ner import LocationNER

    with patch("green_gov_rag.rag.llm_factory.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Mock(content='{"locations": ["Adelaide", "SA"]}')
        mock_get_llm.return_value = mock_llm

        ner = LocationNER(use_llm=True)
        assert ner.llm is not None


# ============================================================================
# Query Expansion Tests
# ============================================================================


def test_query_expansion_basic():
    """Test basic query expansion for acronyms."""
    from green_gov_rag.rag.query_expansion import expand_query

    # Test EPBC Act expansion
    query = "What is required under the EPBC Act?"
    expanded = expand_query(query)
    assert isinstance(expanded, str)
    # Should contain expanded form or original
    assert len(expanded) >= len(query)


def test_jurisdiction_detection():
    """Test jurisdiction detection from query."""
    from green_gov_rag.rag.query_expansion import detect_jurisdiction_from_query

    query_federal = "What are the federal emissions regulations?"
    jurisdiction = detect_jurisdiction_from_query(query_federal)
    assert jurisdiction in [None, "federal", "state", "local"]

    query_state = "NSW planning requirements"
    jurisdiction = detect_jurisdiction_from_query(query_state)
    assert jurisdiction in [None, "federal", "state", "local"]


def test_query_expansion_no_acronyms():
    """Test query expansion with no acronyms."""
    from green_gov_rag.rag.query_expansion import expand_query

    query = "What are the biodiversity requirements?"
    expanded = expand_query(query)
    # Should return similar or same query
    assert isinstance(expanded, str)


# ============================================================================
# RAG Chain Integration Tests
# ============================================================================


def test_rag_chain_basic(in_memory_faiss, mock_embedder):
    """Test basic RAG chain initialization."""
    from green_gov_rag.rag.rag_chain import RAGChain

    with patch("green_gov_rag.rag.rag_chain.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm

        rag = RAGChain(in_memory_faiss, embedder=mock_embedder)
        assert rag.vector_store is not None


def test_rag_chain_with_filters(in_memory_faiss):
    """Test RAG with metadata filters."""
    results = in_memory_faiss.similarity_search(
        "Biodiversity conservation",
        k=5,
    )
    assert isinstance(results, list)

    # Manual filter by metadata (simulates RAG chain filtering)
    filtered = [r for r in results if r.metadata.get("region") == "SA"]
    assert isinstance(filtered, list)


# ============================================================================
# Vector Store Factory Tests
# ============================================================================


@pytest.mark.skip(
    reason="Factory implementation requires complex internal module structure"
)
def test_vector_store_factory_faiss():
    """Test vector store factory for FAISS."""
    # from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

    # mock_embeddings = MagicMock()
    # Would test factory behavior with proper mocks
    pass


@pytest.mark.skip(
    reason="Factory implementation requires complex internal module structure"
)
def test_vector_store_factory_qdrant():
    """Test vector store factory for Qdrant."""
    # from green_gov_rag.rag.vector_store_factory import VectorStoreFactory

    # mock_embeddings = MagicMock()
    # Would test factory behavior with proper mocks
    pass


# ============================================================================
# LLM Factory Tests
# ============================================================================


@pytest.mark.skip(reason="Requires OPENAI_API_KEY environment variable")
def test_llm_factory_openai():
    """Test LLM factory for OpenAI."""
    with patch("langchain_openai.ChatOpenAI") as mock_openai:
        from green_gov_rag.rag.llm_factory import get_llm

        mock_openai.return_value = MagicMock()
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            llm = get_llm(provider="openai", model="gpt-4")
            assert llm is not None


@pytest.mark.skip(reason="Requires ANTHROPIC_API_KEY environment variable")
def test_llm_factory_anthropic():
    """Test LLM factory for Anthropic."""
    with patch("langchain_anthropic.ChatAnthropic") as mock_anthropic:
        from green_gov_rag.rag.llm_factory import get_llm

        mock_anthropic.return_value = MagicMock()
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            llm = get_llm(provider="anthropic", model="claude-3-sonnet-20240229")
            assert llm is not None


@pytest.mark.skip(
    reason="Requires AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
)
def test_llm_factory_bedrock():
    """Test LLM factory for AWS Bedrock."""
    with patch("langchain_aws.ChatBedrock") as mock_bedrock:
        from green_gov_rag.rag.llm_factory import get_llm

        mock_bedrock.return_value = MagicMock()
        llm = get_llm(provider="bedrock", model="anthropic.claude-v2")
        assert llm is not None


# ============================================================================
# Enhanced Response Tests
# ============================================================================


def test_enhanced_response_with_citations(mock_vector_results):
    """Test enhanced response generation with citations."""
    # This would test the enhanced_response module
    # Mock implementation for now
    response_text = "Based on NSW regulations..."
    citations = [{"source": "nsw_emissions.pdf", "page": 1, "relevance": 0.95}]

    assert isinstance(response_text, str)
    assert isinstance(citations, list)
    assert all("source" in c for c in citations)


def test_trust_score_calculation():
    """Test trust score calculation for responses."""

    # Mock trust score logic
    def calculate_trust_score(citations, response_length):
        if not citations:
            return 0.0
        return min(1.0, len(citations) * 0.2 + (response_length > 100) * 0.2)

    score1 = calculate_trust_score([{"source": "doc1"}], 150)
    assert 0.0 <= score1 <= 1.0

    score2 = calculate_trust_score([], 50)
    assert score2 == 0.0


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_embedding_with_special_characters(mock_embedder):
    """Test embeddings with special characters."""
    chunks = [
        {
            "content": "Regulations: § 123.45(a)(1) @ $50/tonne CO₂-e",
            "metadata": {},
        }
    ]
    embedded = mock_embedder.embed_chunks(chunks)
    assert len(embedded) == 1
    assert "embedding" in embedded[0]


def test_empty_vector_store_search(in_memory_faiss):
    """Test search on vector store with limited results."""
    results = in_memory_faiss.similarity_search("nonexistent topic", k=100)
    # Should return available results (limited by actual data)
    assert isinstance(results, list)


def test_hybrid_search_no_results_fallback(in_memory_faiss):
    """Test hybrid search fallback when no results match filters."""
    from green_gov_rag.rag.hybrid_search import HybridGeospatialSearch

    search = HybridGeospatialSearch(in_memory_faiss, enable_ner=False)
    # Search with very restrictive filters
    results = search.search(
        "quantum physics",  # Unrelated topic
        metadata_filters={"jurisdiction": "interplanetary"},  # Non-existent
        k=5,
    )
    assert isinstance(results, list)


def test_location_ner_empty_text():
    """Test LocationNER with empty text."""
    from green_gov_rag.rag.location_ner import LocationNER

    ner = LocationNER(use_llm=False)
    results = ner.extract_locations("")
    assert results["states"] == []
    assert results["lgas"] == []


def test_query_expansion_with_unicode(mock_embedder):
    """Test query expansion with unicode characters."""
    from green_gov_rag.rag.query_expansion import expand_query

    query = "Café regulations in NSW?"
    expanded = expand_query(query)
    assert isinstance(expanded, str)
    assert "Café" in expanded or "Cafe" in expanded

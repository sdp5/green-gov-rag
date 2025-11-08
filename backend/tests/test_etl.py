"""Tests for ETL pipeline.

This test suite includes comprehensive mocking for all external dependencies:
- Network calls (tiktoken downloads, HTTP requests)
- File system operations (where appropriate)
- External services (LLM APIs, cloud storage)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from green_gov_rag.etl import chunker, ingest, loader, utils, validators

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


# ============================================================================
# Mock Fixtures for External Dependencies
# ============================================================================


@pytest.fixture
def mock_tiktoken_encoding():
    """Mock tiktoken encoding to avoid network downloads."""
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3, 4, 5]  # Mock token IDs

    with patch("tiktoken.get_encoding", return_value=mock_encoding):
        yield mock_encoding


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for HTTP downloads."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"mock file content"
    mock_response.text = "mock text content"
    mock_response.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_response):
        yield mock_response


@pytest.fixture
def mock_file_download():
    """Mock file downloads in ingest module."""

    def fake_download(url, dest_path):
        # Create a fake file
        Path(dest_path).write_text("mock downloaded content")
        return dest_path

    return fake_download


# ============================================================================
# Utils Tests (text cleaning, preprocessing)
# ============================================================================


def test_text_cleaning_basic():
    """Test basic text cleaning removes extra whitespace and newlines."""
    sample_text = "This  is  a   TEST.\nWith multiple  spaces."
    cleaned = utils.clean_text(sample_text)
    assert "\n" not in cleaned
    assert "  " not in cleaned
    assert cleaned == "This is a TEST. With multiple spaces."


def test_text_cleaning_empty():
    """Test cleaning empty string."""
    assert utils.clean_text("") == ""


def test_text_cleaning_unicode():
    """Test unicode normalization."""
    text_with_unicode = "Café résumé naïve"
    normalized = utils.normalize_unicode(text_with_unicode)
    assert isinstance(normalized, str)
    # NFKC normalization should preserve accented characters
    assert "Café" in normalized


def test_remove_urls():
    """Test URL removal from text."""
    text_with_urls = "Check https://example.com and www.test.com for info."
    cleaned = utils.remove_urls(text_with_urls)
    assert "https://example.com" not in cleaned
    assert "www.test.com" not in cleaned
    assert "Check" in cleaned
    assert "for info" in cleaned


def test_remove_non_alphanumeric():
    """Test removal of special characters."""
    text = "Hello @world! #test $price €100 ™brand"
    cleaned = utils.remove_non_alphanumeric(text)
    assert "@" not in cleaned
    assert "#" not in cleaned
    assert "$" not in cleaned
    assert "€" not in cleaned
    assert "™" not in cleaned
    assert "Hello" in cleaned
    assert "world" in cleaned


def test_collapse_whitespace():
    """Test collapsing multiple spaces and newlines."""
    text = "Line 1\n\n\nLine 2    with    spaces"
    collapsed = utils.collapse_whitespace(text)
    assert "\n\n" not in collapsed
    assert "   " not in collapsed
    assert collapsed == "Line 1 Line 2 with spaces"


def test_batch_clean():
    """Test batch cleaning of multiple texts."""
    texts = [
        "Text  with   spaces",
        "URL: http://example.com here",
        "Symbols: @#$% removed",
    ]
    cleaned = utils.batch_clean(texts)
    assert len(cleaned) == 3
    assert all(isinstance(t, str) for t in cleaned)
    assert "http://example.com" not in cleaned[1]
    assert "@#$%" not in cleaned[2]


# ============================================================================
# Chunker Tests (text splitting, hierarchical chunking)
# ============================================================================


def test_chunking_normal():
    """Test normal text chunking."""
    text = " ".join([f"Sentence {i}." for i in range(50)])
    chunks = chunker.chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert all(len(c) > 0 for c in chunks)


def test_chunking_edge_cases():
    """Test chunking with text shorter than chunk size."""
    text = "Short text"
    chunks = chunker.chunk_text(text, chunk_size=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunking_empty_text():
    """Test chunking empty string."""
    chunks = chunker.chunk_text("", chunk_size=100)
    # LangChain text splitters return empty list for empty text
    assert len(chunks) == 0 or (len(chunks) == 1 and chunks[0] == "")


def test_chunking_with_overlap():
    """Test chunking with overlap preserves context."""
    text = "A B C D E F G H I J K L M N O P"
    chunks = chunker.chunk_text(text, chunk_size=10, chunk_overlap=5)
    assert len(chunks) > 1
    # Check that consecutive chunks have overlap
    if len(chunks) > 1:
        # Some content should appear in multiple chunks
        assert any(
            any(word in chunks[i + 1] for word in chunks[i].split())
            for i in range(len(chunks) - 1)
        )


def test_text_chunker_class():
    """Test TextChunker class initialization and usage."""
    text_chunker = chunker.TextChunker(chunk_size=50, chunk_overlap=10)
    text = "This is a test document with multiple sentences to chunk."
    chunks = text_chunker.chunk_text(text)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1


def test_text_chunker_recursive():
    """Test recursive character text splitter."""
    text_chunker = chunker.TextChunker(
        chunk_size=50,
        chunk_overlap=10,
        splitter_type="recursive",
    )
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    chunks = text_chunker.chunk_text(text)
    assert len(chunks) >= 1


def test_text_chunker_token(mock_tiktoken_encoding):
    """Test token-based text splitter with mocked tiktoken.

    This test mocks the tiktoken encoding to avoid network downloads.
    """
    # Mock the split_text method to return predictable chunks
    with patch(
        "langchain_text_splitters.base.TokenTextSplitter.split_text"
    ) as mock_split:
        mock_split.return_value = ["This is a", "test document."]

        text_chunker = chunker.TextChunker(
            chunk_size=10,
            chunk_overlap=2,
            splitter_type="token",
        )
        text = "This is a test document."
        chunks = text_chunker.chunk_text(text)

        assert isinstance(chunks, list)
        assert len(chunks) == 2
        assert chunks[0] == "This is a"
        assert chunks[1] == "test document."


def test_text_chunker_invalid_type():
    """Test that invalid splitter type raises error."""
    with pytest.raises(ValueError, match="Unsupported splitter_type"):
        chunker.TextChunker(splitter_type="invalid")


def test_chunk_docs():
    """Test chunking documents with metadata."""
    text_chunker = chunker.TextChunker(chunk_size=20, chunk_overlap=5)
    docs = [
        {"content": "Document 1 content here.", "metadata": {"title": "Doc 1"}},
        {"content": "Document 2 content here.", "metadata": {"title": "Doc 2"}},
    ]
    chunked = text_chunker.chunk_docs(docs)
    assert len(chunked) >= 2
    assert all("chunk_id" in doc["metadata"] for doc in chunked)
    assert all("title" in doc["metadata"] for doc in chunked)


def test_chunk_with_hierarchy():
    """Test hierarchical chunking preserves section metadata."""
    text_chunker = chunker.TextChunker(chunk_size=30, chunk_overlap=5)
    hierarchical_chunks = [
        {
            "content": "Section 1 content with multiple sentences that need chunking.",
            "metadata": {
                "section": "1.0",
                "section_title": "Introduction",
                "page": 1,
                "chunk_id": 0,
            },
        },
    ]
    chunked = text_chunker.chunk_with_hierarchy(hierarchical_chunks)
    assert len(chunked) >= 1
    # Check metadata preservation
    assert all("section" in doc["metadata"] for doc in chunked)
    assert all("page" in doc["metadata"] for doc in chunked)
    assert all("chunk_id" in doc["metadata"] for doc in chunked)
    assert all("original_chunk_id" in doc["metadata"] for doc in chunked)
    assert all("sub_chunk_id" in doc["metadata"] for doc in chunked)


def test_chunk_overlap_validation():
    """Test that chunk overlap is adjusted if too large."""
    # Overlap should be capped at chunk_size - 1
    chunks = chunker.chunk_text("Test text", chunk_size=5, chunk_overlap=10)
    # Should not raise error, overlap should be adjusted
    assert isinstance(chunks, list)


# ============================================================================
# Validator Tests (document validation, file checks)
# ============================================================================


def test_validator_checks():
    """Test basic document validation."""
    valid_doc = {"title": "Doc", "download_urls": ["url"], "sovereign": True}
    invalid_doc = {"title": "Doc", "sovereign": True}
    assert validators.validate_document(valid_doc) is True
    assert validators.validate_document(invalid_doc) is False


def test_validate_document_missing_title():
    """Test validation fails without title."""
    doc = {"download_urls": ["url"], "sovereign": True}
    assert validators.validate_document(doc) is False


def test_validate_document_empty_urls():
    """Test validation fails with empty URL list."""
    doc = {"title": "Doc", "download_urls": [], "sovereign": True}
    assert validators.validate_document(doc) is False


def test_validate_document_urls_not_list():
    """Test validation fails when urls is not a list."""
    doc = {"title": "Doc", "download_urls": "not-a-list", "sovereign": True}
    assert validators.validate_document(doc) is False


def test_validate_file_exists(tmp_path):
    """Test file existence validation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert validators.validate_file_exists(str(test_file)) is True
    assert validators.validate_file_exists(str(tmp_path / "nonexistent.txt")) is False


def test_validate_pdf(tmp_path):
    """Test PDF file validation."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_text("fake pdf content")
    assert validators.validate_pdf(str(pdf_file)) is True

    txt_file = tmp_path / "test.txt"
    txt_file.write_text("text content")
    assert validators.validate_pdf(str(txt_file)) is False

    # Non-existent file
    assert validators.validate_pdf(str(tmp_path / "missing.pdf")) is False


def test_validate_html(tmp_path):
    """Test HTML file validation."""
    html_file = tmp_path / "test.html"
    html_file.write_text("<html></html>")
    assert validators.validate_html(str(html_file)) is True

    htm_file = tmp_path / "test.htm"
    htm_file.write_text("<html></html>")
    assert validators.validate_html(str(htm_file)) is True

    txt_file = tmp_path / "test.txt"
    txt_file.write_text("text")
    assert validators.validate_html(str(txt_file)) is False


def test_validate_metadata_complete():
    """Test metadata validation with all required fields."""
    doc = {
        "title": "Test",
        "jurisdiction": "federal",
        "category": "legislation",
        "topic": "biodiversity",
        "region": "Australia",
        "sovereign": True,
    }
    assert validators.validate_metadata(doc) is True


def test_validate_metadata_incomplete():
    """Test metadata validation with missing fields."""
    doc = {
        "title": "Test",
        "jurisdiction": "federal",
        # Missing other required fields
    }
    assert validators.validate_metadata(doc) is False


# ============================================================================
# Loader Tests (YAML parsing, config loading)
# ============================================================================


def test_loader_yaml_parsing(tmp_path):
    """Test basic YAML loading."""
    yaml_file = tmp_path / "docs.yml"
    yaml_file.write_text(
        """
    documents:
      - title: Sample
        download_urls: [http://example.com/doc.pdf]
    """,
    )
    loaded = loader.load_yaml(str(yaml_file))
    assert "documents" in loaded
    assert len(loaded["documents"]) == 1


def test_loader_yaml_with_metadata(tmp_path):
    """Test YAML loading with rich metadata."""
    yaml_file = tmp_path / "docs.yml"
    yaml_file.write_text(
        """
    documents:
      - title: EPBC Act
        download_urls:
          - http://example.com/epbc.pdf
        jurisdiction: federal
        category: legislation
        topic: biodiversity
        region: Australia
        sovereign: true
        spatial_metadata:
          spatial_scope: federal
          applies_to_all_lgas: true
    """,
    )
    loaded = loader.load_yaml(str(yaml_file))
    assert loaded["documents"][0]["jurisdiction"] == "federal"
    assert loaded["documents"][0]["spatial_metadata"]["spatial_scope"] == "federal"


def test_loader_empty_yaml(tmp_path):
    """Test loading empty YAML file."""
    yaml_file = tmp_path / "empty.yml"
    yaml_file.write_text("")
    loaded = loader.load_yaml(str(yaml_file))
    assert loaded is None or loaded == {}


def test_loader_invalid_yaml(tmp_path):
    """Test loading malformed YAML."""
    yaml_file = tmp_path / "invalid.yml"
    yaml_file.write_text("invalid: yaml: content: here")
    with pytest.raises(Exception):  # YAML parse error
        loader.load_yaml(str(yaml_file))


# ============================================================================
# Ingest Tests (document downloading, processing)
# ============================================================================


def test_ingest_download(monkeypatch):
    """Test document download mocking."""
    called = {}

    def fake_download(docs, out_dir):
        called["yes"] = True
        return ["dummy.txt"]

    monkeypatch.setattr(ingest, "download_documents", fake_download)
    docs = [{"title": "Test Doc", "download_urls": ["http://example.com"]}]
    result = ingest.download_documents(docs, str(RAW_DIR))
    assert called.get("yes") is True
    assert isinstance(result, list)


def test_ingest_download_multiple_docs(monkeypatch):
    """Test downloading multiple documents."""

    def fake_download(docs, out_dir):
        return [f"doc_{i}.pdf" for i in range(len(docs))]

    monkeypatch.setattr(ingest, "download_documents", fake_download)
    docs = [
        {"title": "Doc 1", "download_urls": ["http://example.com/1.pdf"]},
        {"title": "Doc 2", "download_urls": ["http://example.com/2.pdf"]},
    ]
    result = ingest.download_documents(docs, str(RAW_DIR))
    assert len(result) == 2


# ============================================================================
# Integration Tests (combining multiple modules)
# ============================================================================


def test_full_text_pipeline():
    """Test complete text processing pipeline."""
    # 1. Raw text
    raw_text = (
        "This  is  a   TEST.\nWith URLs: http://example.com and special chars @#$"
    )

    # 2. Clean text
    cleaned = utils.clean_text(raw_text)
    assert "http://example.com" not in cleaned
    assert "@#$" not in cleaned

    # 3. Chunk text
    chunks = chunker.chunk_text(cleaned, chunk_size=20, chunk_overlap=5)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_document_validation_pipeline(tmp_path):
    """Test document validation pipeline."""
    # 1. Create YAML config
    yaml_file = tmp_path / "config.yml"
    yaml_file.write_text(
        """
    documents:
      - title: Valid Doc
        download_urls: [http://example.com/doc.pdf]
        sovereign: true
      - title: Invalid Doc
        sovereign: true
    """,
    )

    # 2. Load config
    config = loader.load_yaml(str(yaml_file))
    docs = config["documents"]

    # 3. Validate documents
    validation_results = [validators.validate_document(doc) for doc in docs]
    assert validation_results[0] is True  # Valid
    assert validation_results[1] is False  # Invalid (missing URLs)


def test_chunk_then_clean():
    """Test that cleaning before chunking works correctly."""
    dirty_text = "Paragraph 1 with http://example.com.\n\nParagraph 2 with @symbols."

    # Clean first
    cleaned = utils.clean_text(dirty_text)

    # Then chunk
    chunks = chunker.chunk_text(cleaned, chunk_size=30)

    # Verify no URLs or symbols in chunks
    for chunk in chunks:
        assert "http://" not in chunk
        assert "@" not in chunk


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


def test_chunking_very_long_text():
    """Test chunking very long text doesn't cause issues."""
    long_text = " ".join([f"Word{i}" for i in range(10000)])
    chunks = chunker.chunk_text(long_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 10
    assert all(len(c) <= 120 for c in chunks)  # Allow some buffer


def test_cleaning_special_unicode():
    """Test cleaning text with various unicode characters."""
    text = "Hello 世界 مرحبا мир 🌍"
    cleaned = utils.clean_text(text)
    # Should handle unicode gracefully
    assert isinstance(cleaned, str)


def test_empty_document_list():
    """Test processing empty document list."""
    text_chunker = chunker.TextChunker()
    result = text_chunker.chunk_docs([])
    assert result == []


def test_document_with_no_content():
    """Test handling documents with empty content."""
    text_chunker = chunker.TextChunker()
    docs = [{"content": "", "metadata": {"title": "Empty"}}]
    chunked = text_chunker.chunk_docs(docs)
    # LangChain splitters return empty list for empty content
    assert isinstance(chunked, list)

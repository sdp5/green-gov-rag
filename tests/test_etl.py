import pytest
from pathlib import Path
from etl import utils, chunker, ingest, loader, validators

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def test_text_cleaning_basic():
    sample_text = "This  is  a   TEST.\nWith multiple  spaces."
    cleaned = utils.clean_text(sample_text)
    assert "\n" not in cleaned
    assert "  " not in cleaned
    assert cleaned == "This is a TEST. With multiple spaces."


def test_text_cleaning_empty():
    assert utils.clean_text("") == ""


def test_chunking_normal():
    text = " ".join([f"Sentence {i}." for i in range(50)])
    chunks = chunker.chunk_text(text, chunk_size=10, chunk_overlap=2)
    assert isinstance(chunks, list)
    assert all(isinstance(c, str) for c in chunks)
    assert all(len(c) > 0 for c in chunks)


def test_chunking_edge_cases():
    text = "Short text"
    chunks = chunker.chunk_text(text, chunk_size=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_ingest_download(monkeypatch):
    called = {}

    def fake_download(docs, out_dir):
        called["yes"] = True
        return ["dummy.txt"]

    monkeypatch.setattr(ingest, "download_documents", fake_download)
    docs = [{"title": "Test Doc", "download_urls": ["http://example.com"]}]
    result = ingest.download_documents(docs, RAW_DIR)
    assert called.get("yes") is True
    assert isinstance(result, list)


def test_loader_yaml_parsing(tmp_path):
    yaml_file = tmp_path / "docs.yml"
    yaml_file.write_text("""
    documents:
      - title: Sample
        download_urls: [http://example.com/doc.pdf]
    """)
    loaded = loader.load_yaml(str(yaml_file))
    assert "documents" in loaded
    assert len(loaded["documents"]) == 1


def test_validator_checks():
    valid_doc = {"title": "Doc", "download_urls": ["url"], "sovereign": True}
    invalid_doc = {"title": "Doc", "sovereign": True}
    assert validators.validate_document(valid_doc) is True
    assert validators.validate_document(invalid_doc) is False

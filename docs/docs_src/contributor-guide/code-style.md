# Code Style Guide

> Standards and conventions for writing clean, maintainable code in GreenGovRAG

## Table of Contents

- [Overview](#overview)
- [Python Code Style](#python-code-style)
- [Ruff Configuration](#ruff-configuration)
- [MyPy Type Checking](#mypy-type-checking)
- [Docstring Standards](#docstring-standards)
- [Import Ordering](#import-ordering)
- [Naming Conventions](#naming-conventions)
- [File Organization](#file-organization)
- [Code Formatting](#code-formatting)
- [Running Tools](#running-tools)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Common Patterns](#common-patterns)
- [Anti-patterns to Avoid](#anti-patterns-to-avoid)

## Overview

GreenGovRAG follows strict code quality standards to ensure maintainability, readability, and consistency across the codebase. We use automated tools to enforce these standards.

**Core Principles:**

- Code should be self-documenting
- Type hints are required for all functions
- Documentation should explain "why", not "what"
- Complexity should be minimized (max McCabe complexity: 10)
- Security considerations should be addressed
- Performance implications should be understood

**Tools We Use:**

- **Ruff**: Fast Python linter and formatter (replaces Black, isort, flake8, pylint)
- **MyPy**: Static type checker
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks for automated checks

## Python Code Style

### PEP 8 Compliance

We follow [PEP 8](https://pep8.org/) with specific customizations defined in `pyproject.toml`.

**Key Rules:**

- Line length: 100 characters (not 79)
- Indentation: 4 spaces (never tabs)
- Encoding: UTF-8
- Quotes: Double quotes for strings (configurable)
- Line endings: Unix-style (LF)

### Line Length

```python
# Good: Within 100 characters
def process_document(doc_path: str, metadata: dict[str, Any]) -> ProcessedDocument:
    """Process a document with the given metadata."""
    return processor.process(doc_path, metadata)

# Bad: Exceeds 100 characters
def process_document(doc_path: str, metadata: dict[str, Any], chunk_size: int = 1000, chunk_overlap: int = 200, enable_ocr: bool = False) -> ProcessedDocument:
    return processor.process(doc_path, metadata, chunk_size, chunk_overlap, enable_ocr)

# Good: Split long function signature
def process_document(
    doc_path: str,
    metadata: dict[str, Any],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    enable_ocr: bool = False,
) -> ProcessedDocument:
    """Process a document with the given metadata."""
    return processor.process(doc_path, metadata, chunk_size, chunk_overlap, enable_ocr)
```

### Indentation

```python
# Good: Consistent 4-space indentation
def query_with_filters(
    query: str,
    lga_name: str | None = None,
    document_types: list[str] | None = None,
) -> QueryResult:
    """Execute query with optional filters."""
    if lga_name:
        filters = {"lga_name": lga_name}
    else:
        filters = {}

    return search_engine.query(query, filters)

# Bad: Inconsistent indentation
def query_with_filters(
  query: str,
    lga_name: str | None = None,
      document_types: list[str] | None = None,
) -> QueryResult:
  if lga_name:
      filters = {"lga_name": lga_name}
  return search_engine.query(query, filters)
```

## Ruff Configuration

Ruff is configured in `backend/pyproject.toml` with strict rules enabled.

### Enabled Rule Categories

The following rule categories are enabled (see `pyproject.toml` for complete list):

- **F** (Pyflakes): Basic Python errors
- **E/W** (pycodestyle): PEP 8 style violations
- **I** (isort): Import sorting
- **N** (pep8-naming): Naming conventions
- **D** (pydocstyle): Docstring conventions
- **UP** (pyupgrade): Modern Python syntax
- **ANN** (flake8-annotations): Type annotations
- **S** (flake8-bandit): Security issues
- **B** (flake8-bugbear): Common bugs
- **C4** (flake8-comprehensions): List/dict comprehensions
- **PT** (flake8-pytest-style): Pytest conventions
- **RUF** (Ruff-specific): Ruff's own rules

### Ignored Rules

Some rules are explicitly ignored:

```python
# See pyproject.toml [tool.ruff.lint.ignore] section

# ANN101, ANN102: Type hints for self/cls (MyPy handles this)
# S101: Assert usage (allowed in tests)
# TD002, TD003: TODO formatting (relaxed)
# COM812: Trailing commas (preference)
```

### Running Ruff

```bash
# Format code (modifies files)
ruff format .

# Check for issues (no modifications)
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Show explanation for a rule
ruff rule E501  # Line too long

# Check specific file
ruff check green_gov_rag/api/routes/query.py

# Check with specific rules
ruff check --select=D .  # Only docstring rules
```

## MyPy Type Checking

### Type Hints Requirements

**All functions must have type hints:**

```python
# Good: Complete type hints
def fetch_documents(
    source_url: str,
    max_pages: int = 10,
    timeout: int = 30,
) -> list[Document]:
    """Fetch documents from the given source."""
    documents: list[Document] = []
    for page in range(max_pages):
        doc = fetch_page(source_url, page, timeout)
        documents.append(doc)
    return documents

# Bad: Missing type hints
def fetch_documents(source_url, max_pages=10, timeout=30):
    documents = []
    for page in range(max_pages):
        doc = fetch_page(source_url, page, timeout)
        documents.append(doc)
    return documents
```

### Modern Type Syntax

Use Python 3.12+ type syntax:

```python
# Good: Modern type syntax (Python 3.12+)
def process_batch(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def get_optional_value(key: str) -> str | None:
    return cache.get(key)

# Bad: Old type syntax (pre-3.10)
from typing import List, Dict, Optional

def process_batch(items: List[str]) -> Dict[str, int]:
    return {item: len(item) for item in items}

def get_optional_value(key: str) -> Optional[str]:
    return cache.get(key)
```

### Complex Types

```python
from typing import Any, TypeVar, Generic, Protocol
from collections.abc import Callable, Iterable

# Good: Proper generic types
T = TypeVar("T")

def first_or_none(items: Iterable[T]) -> T | None:
    """Return first item or None if empty."""
    return next(iter(items), None)

# Good: Callable types
def retry_on_error(
    func: Callable[[str], bool],
    max_retries: int = 3,
) -> bool:
    """Retry function on error."""
    for _ in range(max_retries):
        try:
            return func("test")
        except Exception:
            continue
    return False

# Good: Protocol for structural typing
class Processor(Protocol):
    """Protocol for document processors."""

    def process(self, text: str) -> str:
        """Process text."""
        ...
```

### Type Checking Configuration

MyPy is configured in `backend/pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
warn_unused_ignores = true
ignore_missing_imports = true
warn_redundant_casts = true
strict_optional = true
check_untyped_defs = true
```

### Running MyPy

```bash
# Check entire codebase
mypy green_gov_rag tests

# Check specific file
mypy green_gov_rag/api/routes/query.py

# Show error codes
mypy --show-error-codes green_gov_rag

# Generate coverage report
mypy --html-report mypy-report green_gov_rag
```

## Docstring Standards

We use **Google-style docstrings** exclusively.

### Module Docstrings

```python
"""Document ingestion and processing module.

This module provides functionality for ingesting documents from various sources,
parsing them into structured format, and storing metadata in the database.

Example:
    >>> from green_gov_rag.etl import ingest
    >>> result = ingest.process_source("epbc_act")
    >>> print(f"Processed {result.count} documents")
"""
```

### Function Docstrings

```python
def query_with_location(
    query: str,
    lga_name: str,
    buffer_km: float = 0.0,
    top_k: int = 5,
) -> QueryResult:
    """Execute RAG query with geospatial filtering.

    Retrieves relevant regulatory documents based on the query text and filters
    by Local Government Area. Optionally expands the search to neighboring LGAs
    within the specified buffer distance.

    Args:
        query: The user's question or search query.
        lga_name: Name of the Local Government Area (e.g., "Adelaide City Council").
        buffer_km: Distance in kilometers to expand search radius. Defaults to 0.0.
        top_k: Number of top results to return. Defaults to 5.

    Returns:
        QueryResult containing the answer, source documents, and metadata.

    Raises:
        ValueError: If lga_name is empty or invalid.
        VectorStoreError: If vector store connection fails.
        LLMError: If LLM API call fails.

    Example:
        >>> result = query_with_location(
        ...     query="Can I clear native vegetation?",
        ...     lga_name="Adelaide Hills Council",
        ...     buffer_km=10.0,
        ... )
        >>> print(result.answer)
    """
    if not lga_name:
        raise ValueError("lga_name cannot be empty")

    # Implementation...
```

### Class Docstrings

```python
class DocumentProcessor:
    """Process regulatory documents for ingestion into the RAG system.

    This class handles document parsing, chunking, and metadata extraction
    for various document formats including PDF, HTML, and Word documents.

    Attributes:
        chunk_size: Maximum size of text chunks in tokens.
        chunk_overlap: Number of overlapping tokens between chunks.
        enable_ocr: Whether to use OCR for scanned documents.

    Example:
        >>> processor = DocumentProcessor(chunk_size=1000)
        >>> chunks = processor.process_file("path/to/document.pdf")
        >>> print(f"Created {len(chunks)} chunks")
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        enable_ocr: bool = False,
    ) -> None:
        """Initialize the document processor.

        Args:
            chunk_size: Maximum chunk size in tokens.
            chunk_overlap: Overlapping tokens between chunks.
            enable_ocr: Enable OCR for scanned PDFs.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.enable_ocr = enable_ocr
```

### Property Docstrings

```python
@property
def is_healthy(self) -> bool:
    """Check if the service is healthy.

    Returns:
        True if all dependencies are reachable, False otherwise.
    """
    return self._check_database() and self._check_vector_store()
```

## Import Ordering

Imports are automatically sorted by Ruff (isort integration).

### Import Order

1. Standard library imports
2. Third-party imports
3. Local application imports

```python
# Good: Proper import ordering
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from langchain_community.vectorstores import FAISS
from sqlmodel import Session, select

from green_gov_rag.api.schemas import QueryRequest, QueryResponse
from green_gov_rag.config import settings
from green_gov_rag.models.database import get_session
from green_gov_rag.rag.enhanced_response import EnhancedRAGPipeline

# Bad: Random import order
from green_gov_rag.config import settings
import os
from fastapi import APIRouter
from green_gov_rag.models.database import get_session
import numpy as np
from datetime import datetime
```

### Import Style

```python
# Good: Explicit imports
from green_gov_rag.rag.vector_store import VectorStoreFactory
from green_gov_rag.models.document import Document, DocumentMetadata

# Acceptable: Module import for many items
from green_gov_rag import models

# Bad: Star imports (never use)
from green_gov_rag.rag.vector_store import *
```

### Conditional Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import only for type checking, not runtime
    from green_gov_rag.rag.llm_factory import LLMProvider
```

## Naming Conventions

### Variables and Functions

```python
# Good: snake_case for variables and functions
document_count = 0
max_retry_attempts = 3

def fetch_documents() -> list[Document]:
    """Fetch documents from database."""
    pass

def calculate_trust_score(sources: list[Source]) -> float:
    """Calculate trust score from sources."""
    pass

# Bad: camelCase or PascalCase for variables/functions
documentCount = 0
maxRetryAttempts = 3

def FetchDocuments():
    pass
```

### Classes

```python
# Good: PascalCase for classes
class DocumentProcessor:
    """Process documents."""
    pass

class EnhancedRAGPipeline:
    """Enhanced RAG pipeline."""
    pass

# Bad: snake_case or other styles
class document_processor:
    pass

class enhanced_rag_pipeline:
    pass
```

### Constants

```python
# Good: UPPER_CASE for constants
MAX_CHUNK_SIZE = 1000
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
API_VERSION = "v1"

# Bad: Other cases for constants
max_chunk_size = 1000
defaultEmbeddingModel = "..."
```

### Private Members

```python
class DocumentCache:
    """Cache for documents."""

    def __init__(self) -> None:
        # Good: Leading underscore for private
        self._cache: dict[str, Document] = {}
        self._hit_count = 0

    def _update_stats(self) -> None:
        """Private method for internal use."""
        self._hit_count += 1

    # Good: Public API
    def get(self, key: str) -> Document | None:
        """Get document from cache."""
        doc = self._cache.get(key)
        if doc:
            self._update_stats()
        return doc
```

### Type Variables

```python
# Good: PascalCase for type variables
T = TypeVar("T")
DocumentT = TypeVar("DocumentT", bound=Document)

# Bad: Other cases
t = TypeVar("t")
DOCUMENT_T = TypeVar("DOCUMENT_T")
```

## File Organization

### Module Structure

```python
"""Module docstring here."""

# Standard library imports
import os
from datetime import datetime
from pathlib import Path

# Third-party imports
from fastapi import APIRouter
from langchain_community.vectorstores import FAISS

# Local imports
from green_gov_rag.config import settings
from green_gov_rag.models import Document

# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Type definitions
DocumentList = list[Document]

# Classes
class DocumentProcessor:
    """Process documents."""
    pass

# Functions
def process_document(doc: Document) -> ProcessedDocument:
    """Process a document."""
    pass

# Main execution
if __name__ == "__main__":
    main()
```

### File Naming

```python
# Good: snake_case for modules
enhanced_response.py
vector_store.py
metadata_tagger.py

# Bad: Other cases
enhancedResponse.py
VectorStore.py
MetadataTagger.py
```

## Code Formatting

### Blank Lines

```python
# Good: Proper spacing
class DocumentProcessor:
    """Process documents."""

    def __init__(self) -> None:
        """Initialize processor."""
        self.cache = {}

    def process(self, doc: Document) -> ProcessedDocument:
        """Process document."""
        # Function implementation
        pass


class VectorStore:
    """Vector store implementation."""
    pass


def standalone_function() -> None:
    """Standalone function."""
    pass

# Bad: Inconsistent spacing
class DocumentProcessor:
    def __init__(self) -> None:
        self.cache = {}
    def process(self, doc: Document) -> ProcessedDocument:
        pass
class VectorStore:
    pass
```

### Line Breaks

```python
# Good: Logical line breaks
def query_documents(
    query: str,
    filters: dict[str, Any] | None = None,
    top_k: int = 5,
) -> list[Document]:
    """Query documents with filters."""
    if filters is None:
        filters = {}

    results = vector_store.similarity_search(
        query,
        k=top_k,
        filter=filters,
    )

    return results

# Bad: No logical grouping
def query_documents(query: str, filters: dict[str, Any] | None = None, top_k: int = 5) -> list[Document]:
    if filters is None:
        filters = {}
    results = vector_store.similarity_search(query, k=top_k, filter=filters)
    return results
```

### String Quotes

```python
# Good: Double quotes (default)
message = "Processing document"
query = "SELECT * FROM documents WHERE type = 'regulation'"

# Acceptable: Single quotes for strings containing double quotes
html = '<div class="container">Content</div>'

# Good: Triple double quotes for docstrings
def func() -> None:
    """This is a docstring."""
    pass
```

## Running Tools

### Format and Lint Workflow

```bash
# 1. Format code with Ruff
cd backend
ruff format .

# 2. Fix auto-fixable lint issues
ruff check --fix .

# 3. Check remaining issues
ruff check .

# 4. Run type checking
mypy green_gov_rag tests

# 5. Run tests
pytest
```

### CI/CD Checks

All of these checks run in CI/CD:

```bash
# Format check (fails if not formatted)
ruff format --check .

# Lint check (fails if issues found)
ruff check .

# Type check
mypy green_gov_rag tests

# Test with coverage
pytest --cov=green_gov_rag --cov-report=xml
```

### Using Make Commands

If `Makefile` is available:

```bash
make format    # Format code
make lint      # Check linting
make mypy      # Type check
make test      # Run tests
make check-all # Run all checks
```

## Pre-commit Hooks

Pre-commit hooks automatically run checks before commits.

### Install Hooks

```bash
pip install pre-commit
pre-commit install
```

### Manual Run

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

### Skip Hooks (Use Sparingly)

```bash
# Skip all hooks for a commit
git commit --no-verify -m "message"

# Better: Fix the issues instead of skipping
```

## Common Patterns

### Error Handling

```python
# Good: Specific exceptions with context
def fetch_document(doc_id: str) -> Document:
    """Fetch document by ID."""
    try:
        doc = database.get(doc_id)
    except DatabaseError as e:
        logger.error(f"Failed to fetch document {doc_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e}",
        ) from e

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found",
        )

    return doc

# Bad: Bare except, no context
def fetch_document(doc_id: str):
    try:
        doc = database.get(doc_id)
        return doc
    except:
        return None
```

### Context Managers

```python
# Good: Use context managers for resources
def process_file(file_path: Path) -> str:
    """Process file contents."""
    with file_path.open("r", encoding="utf-8") as f:
        content = f.read()
    return content.strip()

# Bad: Manual resource management
def process_file(file_path: Path) -> str:
    f = file_path.open("r")
    content = f.read()
    f.close()
    return content.strip()
```

### Comprehensions

```python
# Good: Clear comprehensions
doc_ids = [doc.id for doc in documents if doc.is_active]
metadata = {doc.id: doc.title for doc in documents}

# Bad: Complex nested comprehensions
result = {
    doc.id: [
        chunk.text for chunk in doc.chunks
        if chunk.length > 100 and chunk.has_metadata
    ]
    for doc in documents
    if doc.is_active and doc.type in ["regulation", "policy"]
}

# Better: Break down complex logic
active_docs = [doc for doc in documents if doc.is_active]
result = {}
for doc in active_docs:
    if doc.type in ["regulation", "policy"]:
        large_chunks = [
            chunk.text for chunk in doc.chunks
            if chunk.length > 100 and chunk.has_metadata
        ]
        result[doc.id] = large_chunks
```

## Anti-patterns to Avoid

### Magic Numbers

```python
# Bad: Magic numbers
def chunk_text(text: str) -> list[str]:
    chunks = []
    for i in range(0, len(text), 1000):
        chunks.append(text[i:i + 1000])
    return chunks

# Good: Named constants
DEFAULT_CHUNK_SIZE = 1000

def chunk_text(text: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    """Split text into chunks."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks
```

### Mutable Default Arguments

```python
# Bad: Mutable default argument
def add_document(doc: Document, tags: list[str] = []) -> None:
    tags.append("default")
    doc.tags = tags

# Good: None default with initialization
def add_document(doc: Document, tags: list[str] | None = None) -> None:
    """Add document with tags."""
    if tags is None:
        tags = []
    tags.append("default")
    doc.tags = tags
```

### Overly Complex Functions

```python
# Bad: High complexity (McCabe complexity > 10)
def process_document(doc: Document) -> ProcessedDocument:
    if doc.type == "pdf":
        if doc.is_scanned:
            if doc.language == "en":
                # ... many nested conditions
                pass

# Good: Break down into smaller functions
def process_document(doc: Document) -> ProcessedDocument:
    """Process document based on type."""
    if doc.type == "pdf":
        return process_pdf(doc)
    elif doc.type == "html":
        return process_html(doc)
    else:
        return process_generic(doc)

def process_pdf(doc: Document) -> ProcessedDocument:
    """Process PDF document."""
    if doc.is_scanned:
        return process_scanned_pdf(doc)
    return process_text_pdf(doc)
```

---

**Ready to write tests?** Continue to the [Testing Guide](testing.md) to learn about our testing practices!

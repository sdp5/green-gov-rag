# Contributing to GreenGovRAG

Thank you for your interest in contributing to GreenGovRAG! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Development Setup](#development-setup)
- [Project Architecture](#project-architecture)
- [Areas for Contribution](#areas-for-contribution)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of experience level, background, or identity.

### Expected Behavior

- Be respectful and considerate in communication
- Provide constructive feedback
- Focus on what's best for the project and community
- Show empathy towards other contributors
- Accept constructive criticism gracefully

### Unacceptable Behavior

- Harassment, discrimination, or offensive comments
- Personal attacks or trolling
- Publishing private information without consent
- Any conduct that would be inappropriate in a professional setting

### Enforcement

Instances of unacceptable behavior may be reported to contact@sundeep.id.au. All complaints will be reviewed and investigated promptly and fairly.

---

## Getting Started

### Prerequisites

- **Python**: 3.12 or higher
- **Node.js**: 18+ (for frontend development)
- **Docker**: 20.10+ and Docker Compose
- **Git**: 2.30+
- **PostgreSQL**: 15+ (or use Docker)

### First-Time Setup

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/green-gov-rag.git
   cd green-gov-rag
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/sdp5/green-gov-rag.git
   ```

4. **Install backend dependencies**:
   ```bash
   cd backend
   pip install -e .[dev]
   ```

5. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Initialize database**:
   ```bash
   alembic upgrade head
   ```

7. **Run tests to verify setup**:
   ```bash
   pytest tests/
   ```

---

## Development Workflow

### Branch Strategy

We use a **Git Flow** inspired workflow:

- **`main`**: Production-ready code, deployed to live environment
- **`dev`**: Integration branch for features, the default branch for PRs
- **`feature/*`**: Feature branches (e.g., `feature/add-vic-planning-schemes`)
- **`bugfix/*`**: Bug fix branches (e.g., `bugfix/fix-qdrant-timeout`)
- **`hotfix/*`**: Urgent production fixes (merge to `main` and `dev`)

### Creating a Feature Branch

1. **Ensure you're on the latest dev**:
   ```bash
   git checkout dev
   git pull upstream dev
   ```

2. **Create your feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes** and commit regularly

4. **Keep your branch updated**:
   ```bash
   git fetch upstream
   git rebase upstream/dev
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Syncing with Upstream

```bash
# Fetch latest changes
git fetch upstream

# Update your dev branch
git checkout dev
git merge upstream/dev

# Rebase your feature branch
git checkout feature/your-feature-name
git rebase dev
```

---

## Coding Standards

### Python (Backend)

We use **Ruff** for linting and formatting with strict settings:

#### Code Style
- **Line length**: 100 characters maximum
- **Docstrings**: Google-style for all public functions/classes
- **Type hints**: Required for all function signatures
- **Imports**: Sorted with `isort` (integrated in Ruff)

#### Running Code Quality Tools

```bash
cd backend

# Format code (automatically fixes issues)
ruff format .

# Lint code
ruff check .

# Fix auto-fixable lint issues
ruff check --fix .

# Type checking
mypy green_gov_rag tests
```

#### Example Code Style

```python
"""Module for processing environmental documents.

This module provides utilities for parsing and chunking
environmental regulation documents.
"""

from typing import List, Optional

import pandas as pd
from langchain.schema import Document


def process_document(
    document: Document,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    """Process a document into smaller chunks.

    Args:
        document: The input document to process.
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.

    Returns:
        A list of chunked documents with preserved metadata.

    Raises:
        ValueError: If chunk_size is less than chunk_overlap.
    """
    if chunk_size < chunk_overlap:
        raise ValueError("chunk_size must be >= chunk_overlap")
    
    # Implementation here
    chunks: List[Document] = []
    return chunks
```

### TypeScript/React (Frontend)

- **ESLint**: Airbnb style guide
- **Prettier**: 2 spaces, single quotes, trailing commas
- **Type Safety**: Strict TypeScript, no `any` types

```bash
cd frontend

# Format code
npm run format

# Lint
npm run lint
```

### SQL

- Use SQLModel for database models
- Follow Alembic migration conventions
- Add indexes for frequently queried fields

---

## Testing Guidelines

### Test Requirements

- **All new features** must include tests
- **Bug fixes** should include regression tests
- **Minimum coverage**: 70% overall, 90% for core RAG logic

### Test Categories

We use pytest markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_chunk_text():
    """Test text chunking logic."""
    pass

@pytest.mark.integration
def test_qdrant_connection():
    """Test Qdrant vector store integration."""
    pass

@pytest.mark.slow
def test_full_pipeline():
    """Test complete ETL pipeline (takes >30s)."""
    pass
```

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run with coverage
pytest --cov=green_gov_rag --cov-report=html

# Run specific test file
pytest tests/test_rag.py

# Skip slow tests
pytest -m "not slow"
```

### Writing Good Tests

```python
# Good: Descriptive name, clear assertions
def test_location_ner_extracts_sa_cities():
    """Test that NER correctly identifies South Australian cities."""
    text = "Solar farm proposed near Murray Bridge, SA"
    locations = extract_locations(text)
    
    assert len(locations) == 1
    assert locations[0].name == "Murray Bridge"
    assert locations[0].state == "SA"

# Bad: Vague name, unclear intent
def test_ner():
    result = do_stuff()
    assert result
```

### Mocking External Services

Always mock external APIs in tests:

```python
from unittest.mock import patch

@patch('green_gov_rag.rag.llm_factory.get_llm')
def test_rag_query_with_mock_llm(mock_get_llm):
    mock_llm = MockLLM(responses=["Test response"])
    mock_get_llm.return_value = mock_llm
    
    result = query_rag("test query")
    assert result.answer == "Test response"
```

---

## Commit Messages

We follow **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, build config)
- **perf**: Performance improvements

### Examples

```bash
# Good commits
feat(rag): add support for Victorian planning schemes
fix(vector-store): resolve Qdrant connection timeout on large queries
docs(readme): update deployment instructions for Azure
refactor(etl): simplify document source factory pattern
test(integration): add tests for hybrid search functionality

# Commit with body
feat(api): add geospatial filtering to query endpoint

Implements LGA-based filtering for environmental queries.
Users can now specify a Local Government Area to narrow
search results to region-specific regulations.

Closes #42
```

### Commit Message Rules

- Use imperative mood: "add feature" not "added feature"
- Capitalize subject line
- No period at end of subject
- Limit subject to 72 characters
- Wrap body at 100 characters
- Reference issues/PRs in footer

---

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines (Ruff passes)
- [ ] Type checking passes (MyPy)
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated (if needed)
- [ ] Commits follow conventional commits format
- [ ] Branch is rebased on latest `dev`

### Creating a Pull Request

1. **Push your branch** to your fork
2. **Open a PR** against `sdp5/green-gov-rag:dev` (not `main`!)
3. **Fill out the PR template** completely
4. **Link related issues** using "Closes #123"

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issues
Closes #123

## How Has This Been Tested?
Describe the tests you ran and how to reproduce them.

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added and passing
- [ ] Dependent changes merged
```

### Review Process

1. **Automated checks** must pass (GitHub Actions)
2. **At least one approval** required from maintainers
3. **All comments addressed** before merge
4. **Squash and merge** to keep history clean

### After Merge

- Delete your feature branch (both local and remote)
- Pull latest `dev` to start next feature

---

## Issue Reporting

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** for known solutions
3. **Try latest `dev` branch** (bug may be fixed)

### Issue Templates

#### Bug Report

```markdown
**Describe the bug**
A clear description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What you expected to happen.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.12.1]
- GreenGovRAG version: [e.g., 0.1.0]
- Docker version (if applicable): [e.g., 24.0.5]

**Logs**
```
Paste relevant logs here
```

**Additional context**
Any other information about the problem.
```

#### Feature Request

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or workarounds you've thought about.

**Additional context**
Mockups, examples, or references.
```

---

## Development Setup

### Docker-Based Development

```bash
# Start all services (recommended for full-stack development)
docker-compose --profile dev up

# Backend only
docker-compose up backend postgres qdrant

# Run tests in Docker
docker-compose run backend pytest
```

### Local Development (No Docker)

```bash
# Start PostgreSQL and Qdrant
docker-compose up postgres qdrant -d

# Run backend locally
cd backend
uvicorn green_gov_rag.api.main:app --reload --port 8000

# Run frontend locally
cd frontend
npm run dev
```

### Environment Variables

Key variables for development (see `.env.example`):

```bash
# LLM Configuration
LLM_PROVIDER=openai          # openai|azure|bedrock|anthropic
LLM_MODEL=gpt-4o-mini        # Use mini models for dev
OPENAI_API_KEY=sk-...

# Vector Store
VECTOR_STORE_TYPE=faiss      # Use FAISS for local dev
QDRANT_URL=http://localhost:6333

# Database
DATABASE_URL=postgresql://greengovrag:devpassword@localhost:5432/greengovrag

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG
ENABLE_CORS=true
```

### Database Migrations

```bash
cd backend

# Create a new migration
alembic revision --autogenerate -m "add user authentication"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Project Architecture

### Key Components

```
backend/green_gov_rag/
├── api/                    # FastAPI application
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   └── schemas/           # Request/response models
├── rag/                   # RAG implementation
│   ├── embeddings.py      # Embedding models
│   ├── llm_factory.py     # LLM provider abstraction
│   ├── vector_store.py    # Vector store interface
│   └── hybrid_search.py   # Search logic
├── etl/                   # ETL pipeline
│   ├── pipeline.py        # Orchestration
│   ├── sources/           # Document scrapers
│   └── parsers/           # Document parsers
├── models/                # Database models
└── config.py              # Configuration management
```

### Design Patterns Used

- **Factory Pattern**: `llm_factory.py`, `vector_store_factory.py`
- **Repository Pattern**: `db_writer.py`
- **Dependency Injection**: FastAPI dependencies
- **Plugin System**: Document sources in `etl/sources/`

### Adding a New Document Source

1. Create `backend/green_gov_rag/etl/sources/your_source.py`:

```python
from green_gov_rag.etl.sources.base import BaseDocumentSource
from langchain.schema import Document

class YourSourceScraper(BaseDocumentSource):
    """Scraper for Your Source documents."""
    
    def fetch_documents(self) -> list[Document]:
        """Fetch documents from the source."""
        # Implementation
        pass
    
    def validate_config(self) -> None:
        """Validate source configuration."""
        required = ["url", "selector"]
        for key in required:
            if key not in self.config:
                raise ValueError(f"Missing required config: {key}")
```

2. Register in `backend/configs/documents_config.yml`:

```yaml
sources:
  - type: your_source
    enabled: true
    config:
      url: https://example.gov.au
      selector: ".document-list"
```

3. Add tests in `tests/etl/sources/test_your_source.py`

---

## Areas for Contribution

### High Priority

#### 1. Scalable Document Source Management 🔥
**Problem**: Currently requires manual YAML editing (`documents_config.yml`) for each new document source - not scalable for growth.

**Current Limitations**:
- Manual YAML editing required for each new source
- No auto-discovery of new documents from monitored websites
- GitHub commit required to add documents
- No web UI for adding sources
- Difficult for non-technical contributors

**Proposed Solutions**:

**Option A: Database-backed Source Registry** (Quick Win)
- New table: `document_sources` (id, name, source_type, base_url, enabled, config JSONB)
- Admin API endpoints for CRUD operations: `POST /api/admin/sources`, `PUT /api/admin/sources/{id}`
- ETL reads from DB instead of YAML
- Web UI for adding/editing sources (admin dashboard)
- Migration script to import existing YAML sources

**Option B: Auto-Discovery with Scrapers**
```python
class EPAMonitor(MonitorableSource):
    """Automatically discover new EPA documents."""
    
    def discover_documents(self) -> List[DocumentMetadata]:
        # Scrape EPA website for new PDFs
        # Check if URL changed
        # Auto-detect new versions
        pass
```

**Option C: Hybrid Approach** (Recommended)
- **Tier 1**: Critical sources - Auto-monitored with scrapers (federal legislation, state EPA, NGER)
- **Tier 2**: Standard sources - Database-backed, manually added via admin UI (council schemes, industry guidelines)
- **Tier 3**: Contributed sources - GitHub issues → automated ingestion (community contributions)

**How to Contribute**:
1. Implement `document_sources` table schema in Alembic migration
2. Create admin API endpoints in `backend/green_gov_rag/api/admin/`
3. Build React admin UI component for source management
4. Write migration script: `scripts/migrate_yaml_to_db.py`

---

#### 2. Auto-Location Extraction for Queries
**Status**: Infrastructure implemented but **DISABLED** (needs better document coverage)

**Current Implementation**:
- `HybridGeospatialSearch.search_with_auto_location()` - uses NER to extract locations
- `RAGChain.retrieve_documents(use_auto_location=True)` - passes flag through
- `QueryService` - has integration point but disabled (line 173: `use_auto_location = False`)

**Why Disabled**:
Auto-location filtering can be too narrow when document coverage is limited, resulting in empty source lists. The LLM still generates reasonable answers but without citations (trust score drops to zero).

**Auto-Location Queries** (when enabled):
```python
# User query: "What are tree clearing rules in Adelaide?"
# System auto-extracts: "Adelaide" → City of Adelaide LGA
# Results: Only documents from Adelaide LGA

# User query: "Emission rules in Port Adelaide Enfield"
# System auto-extracts: "Port Adelaide Enfield" → Port Adelaide Enfield LGA

# User query: "Building rules in NSW"
# System auto-extracts: "NSW" → New South Wales state-wide documents
```

**To Enable Later**:
When document coverage improves (>500 documents, >20 LGAs), change line 173 in `backend/green_gov_rag/api/services/query_service.py`:

```python
# Current (disabled):
use_auto_location = False

# Future (enabled):
use_auto_location = not normalized_lgas and not normalized_region
```

**Better Approach - Make Configurable**:
Add to `backend/green_gov_rag/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    enable_auto_location: bool = Field(
        default=False,
        description="Enable automatic location extraction from queries"
    )
    
    auto_location_min_documents: int = Field(
        default=500,
        description="Minimum documents required before enabling auto-location"
    )
```

Then in `query_service.py`:
```python
use_auto_location = (
    settings.enable_auto_location 
    and not normalized_lgas 
    and not normalized_region
)
```

**How to Contribute**:
1. Add configuration fields to `config.py`
2. Implement document count check before enabling auto-location
3. Add admin UI toggle for enabling/disabling feature
4. Write tests for edge cases (ambiguous locations, multiple matches)
5. Add metrics tracking for auto-location accuracy

---

#### 3. Frontend Development
**Status**: React UI is in early stages, needs significant work

- [ ] Complete admin dashboard for document management
- [ ] User authentication UI (login, registration, profile)
- [ ] Interactive query interface with location selection
- [ ] Document browser with filtering and search
- [ ] Analytics dashboard with charts (Recharts integration)
- [ ] Mobile-responsive design improvements

---

#### 4. Authentication & Authorization
**Status**: No authentication currently implemented (open API)

- [ ] Implement OAuth2/JWT authentication
- [ ] User roles: Admin, Contributor, Viewer
- [ ] API key management for programmatic access
- [ ] Rate limiting per user/API key
- [ ] Admin-only endpoints protection
- [ ] Session management and token refresh

---

#### 5. Multi-LGA Query Support
**Status**: Currently single LGA per query

- [ ] Support queries spanning multiple LGAs: "Compare Adelaide and Brisbane tree clearing rules"
- [ ] Implement result aggregation across regions
- [ ] Add comparison view in UI
- [ ] Handle conflicting regulations across jurisdictions

---

### Medium Priority

#### 6. Real-time Document Updates
- [ ] Webhook-based document updates (instead of daily ETL)
- [ ] RSS feed monitoring for government websites
- [ ] Change detection for existing documents
- [ ] Incremental indexing (not full reindex)

#### 7. Parcel-level Geospatial Queries
**Status**: Currently LGA-level only

- [ ] Add support for specific address/parcel queries
- [ ] Integrate with Geocoder APIs (Google Maps, Mapbox)
- [ ] Buffer zone queries (e.g., "Within 500m of river")
- [ ] Property boundary overlays

#### 8. Export Features
- [ ] Export query responses to PDF reports
- [ ] Export to DOCX with proper formatting
- [ ] Bulk export capabilities for multiple queries
- [ ] Email delivery of reports
- [ ] Template customization for different report types

#### 9. Advanced Monitoring & Observability
- [ ] Prometheus + Grafana integration
- [ ] Enhanced alerting (Slack, email, PagerDuty)
- [ ] Performance dashboards (query latency, cache hit rates)
- [ ] Error tracking with Sentry
- [ ] Distributed tracing for RAG pipeline

#### 10. Test Coverage Improvements
**Current**: ~30% overall, needs improvement

- [ ] Increase overall coverage to 60%+
- [ ] Core RAG logic: 75%+
- [ ] E2E tests for frontend
- [ ] Performance benchmarks
- [ ] Load testing for API (Locust, k6)
- [ ] Integration tests for all LLM providers

---

### New Features & Enhancements

#### 11. Additional Document Sources
- [ ] Victoria planning scheme scraper
- [ ] Queensland environmental regulations
- [ ] Western Australia EPA guidelines
- [ ] ACT and NT legislation
- [ ] Industry standards (ISO, AS/NZS)

#### 12. Advanced RAG Features
- [ ] Multi-modal RAG (images, diagrams from PDFs)
- [ ] Conversational memory (follow-up questions)
- [ ] Query refinement suggestions
- [ ] Similar query recommendations
- [ ] Document version tracking and diff view

#### 13. Collaboration Features
- [ ] Shared query collections
- [ ] Comment threads on queries
- [ ] Team workspaces
- [ ] Document annotations

#### 14. Mobile Application
- [ ] React Native mobile app
- [ ] Offline mode with cached documents
- [ ] Push notifications for document updates
- [ ] Location-based suggestions

---

### Documentation Improvements

- [ ] Video tutorials for setup and usage
- [ ] Interactive API examples (Postman collection)
- [ ] Architecture diagrams (C4 model, sequence diagrams)
- [ ] Data source onboarding guide for contributors
- [ ] Deployment guides for additional cloud providers (GCP, DigitalOcean)
- [ ] RAG performance tuning guide
- [ ] Troubleshooting cookbook

---

### Bug Fixes & Optimizations

- [ ] Optimize Qdrant index performance (HNSW parameters)
- [ ] Improve LGA boundary matching accuracy
- [ ] Reduce ETL pipeline memory usage (streaming, batching)
- [ ] Add retry logic with exponential backoff for failed API calls
- [ ] Fix rate limiting edge cases
- [ ] Improve error messages and logging
- [ ] Database query optimization (add missing indexes)

---

## Getting Help

### Resources

- **Documentation**: `docs/` directory
- **GitHub Discussions**: For questions and ideas
- **GitHub Issues**: For bug reports and feature requests

### Common Questions

**Q: How do I add a new LLM provider?**  
A: Extend `llm_factory.py` and add configuration in `config.py`. See existing providers for examples.

**Q: How do I test changes without deploying?**  
A: Use Docker Compose locally or run backend + database individually. See [Development Setup](#development-setup).

**Q: Can I contribute without Python experience?**  
A: Yes! Documentation, frontend (React/TypeScript), testing, and issue triage are all valuable contributions.

**Q: How long do PR reviews take?**  
A: We aim to review within 4-5 business days. Complex PRs may take longer.

---

## Recognition

Contributors are recognized in:
- GitHub Contributors page
- Release notes for significant contributions

Thank you for contributing to GreenGovRAG! 🌱

---

**Last Updated**: 2025-11-21
**Maintainer**: Sundeep Anand (contact@sundeep.id.au)  
**License**: MIT (code), CC BY 3.0 AU (data)
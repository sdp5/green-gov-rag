<div align="center">

# GreenGovRAG

**AI-Powered Navigation for Australian Environmental & Planning Regulations**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue)](https://docs.greengovrag.sundeep.id.au)

[Documentation](https://docs.greengovrag.sundeep.id.au) • [Quick Start](#-quick-start) • [Contributing](#-contributing) • [Support](#-support)

</div>

---

## Overview

GreenGovRAG helps navigate Australia's complex environmental and planning regulations using **Retrieval-Augmented Generation (RAG)**. Ask questions in plain English and get accurate, cited answers from official government sources.

**Key Features:**
- **Geospatial Filtering** - Query by Local Government Area (LGA)
- **Multi-Source** - Federal, state, and local council regulations
- **Legal Citations** - Page numbers and section references
- **Multi-LLM** - OpenAI, Anthropic, AWS Bedrock, Azure support
- **Cloud Ready** - Deploy to AWS, Azure, or Docker

## Use Cases

- **Environmental Impact Assessments** - Determine EIA requirements for projects
- **Vegetation Clearing** - Understand native vegetation regulations by region
- **Planning & Zoning** - Check permitted uses and development controls
- **Emissions Compliance** - Navigate NGER reporting and carbon standards
- **Heritage & Conservation** - Query heritage overlay requirements

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React Web UI  │────▶│  FastAPI Backend │────▶│  Vector Store   │
│   (TypeScript)  │     │   (Python 3.12)  │     │ (FAISS/Qdrant)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐         ┌───────────────┐
                        │  PostgreSQL  │         │  Embeddings   │
                        │   Database   │         │ (HuggingFace) │
                        └──────────────┘         └───────────────┘
```

**Tech Stack:**
- **Backend:** FastAPI, LangChain, SQLModel, Alembic
- **RAG:** FAISS/Qdrant, OpenAI/Anthropic/Bedrock LLMs
- **ETL:** Airflow (local), GitHub Actions (prod)
- **Frontend:** React, TypeScript, Mapbox GL
- **Cloud:** AWS (ECS, S3, RDS) or Azure (Container Apps, Blob Storage)

## Repository Structure

```
green-gov-rag/
├── backend/          # Python backend (FastAPI + RAG + ETL)
├── frontend/         # React frontend (TypeScript)
├── deploy/           # Docker Compose & cloud configs
├── docs/             # MkDocs documentation
├── data/             # Document storage & vectors
└── .github/          # CI/CD workflows
```

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose (recommended)
- OpenAI API key (or other LLM provider)

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/sdp5/green-gov-rag
cd green-gov-rag

# Configure environment
cd deploy/docker
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up
```

**Access:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:3000

### Option 2: Local Development

```bash
# Backend
cd backend
pip install -e .[dev]
cp .env.example .env
# Edit .env with your configuration
alembic upgrade head
uvicorn green_gov_rag.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Try a Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Do I need an EIA for a solar farm in regional NSW?",
    "lga_name": "Dubbo Regional"
  }'
```

**Full Documentation:** https://docs.greengovrag.sundeep.id.au

## Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding document sources, or improving documentation, your help is appreciated.

### Ways to Contribute

- **Report bugs** via [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
- **Add document sources** - Contribute new regulations or planning schemes
- **Code contributions** - Fix bugs, add features, improve tests
- **Documentation** - Improve guides, add examples, fix typos
- **Discussions** - Share ideas and use cases

### Getting Started

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Read the [Contributor Guide](https://docs.greengovrag.sundeep.id.au/contributor-guide/overview/)**
4. **Make your changes** (follow our [Code Style](https://docs.greengovrag.sundeep.id.au/contributor-guide/code-style/))
5. **Run tests** (`pytest tests/`)
6. **Submit a Pull Request**

See our [Development Setup Guide](https://docs.greengovrag.sundeep.id.au/contributor-guide/dev-setup/) for detailed instructions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- All regulatory documents sourced from official Australian government websites
- Data sovereignty: Documents processed and stored in Australian data centers
- Built with [LangChain](https://www.langchain.com/), [FastAPI](https://fastapi.tiangolo.com/), and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)

## Support

- **Documentation:** https://docs.greengovrag.sundeep.id.au
- **Bug Reports:** [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
- **Questions:** [GitHub Discussions](https://github.com/sdp5/green-gov-rag/discussions)

---

<div align="center">

**Made with 🌿 for the Australian environmental compliance community**

[Star us on GitHub](https://github.com/sdp5/green-gov-rag) • [Read the Docs](https://docs.greengovrag.sundeep.id.au) • [Contribute](https://docs.greengovrag.sundeep.id.au/contributor-guide/overview/)

</div>

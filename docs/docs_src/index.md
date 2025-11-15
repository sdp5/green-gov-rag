# GreenGovRAG Documentation

Welcome to the GreenGovRAG documentation! GreenGovRAG is an AI assistant powered by Retrieval-Augmented Generation (RAG) that helps navigate Australian environmental and planning regulations.

## What is GreenGovRAG?

GreenGovRAG combines regulatory document retrieval with geospatial filtering to answer questions about:

- **Environmental Compliance** - EPBC Act, state environmental regulations
- **Land Use & Planning** - Local council planning schemes, zoning rules
- **Vegetation Clearing** - Native vegetation regulations by state and LGA
- **Emissions Standards** - NGER reporting, ESG frameworks, carbon accounting

**Key Features:**
- Multi-LLM support (OpenAI, Anthropic, AWS Bedrock, Azure)
- Geospatial filtering by Local Government Area (LGA)
- Legal-grade citations with page numbers and sections
- Hybrid search (BM25 + vector similarity)
- Cloud storage support (AWS S3, Azure Blob, Local)
- Production-ready deployment options

## Getting Started Paths

### I want to use GreenGovRAG

**Start here if you want to query Australian regulations:**

1. [Installation Guide](getting-started/installation.md) - Set up GreenGovRAG
2. [Quick Start](getting-started/quickstart.md) - Get running in 5 minutes
3. [Configuration Guide](getting-started/configuration.md) - Configure your setup
4. [First Query Tutorial](getting-started/first-query.md) - Submit your first query

**Then explore:**
- [User Guide](user-guide/) - Learn how to use the system effectively
- [Troubleshooting](user-guide/troubleshooting.md) - Common issues and solutions

### I want to contribute to GreenGovRAG

**Start here if you want to add document sources or fix bugs:**

1. [Contribution Overview](contributor-guide/overview.md) - How to contribute
2. [Development Setup](contributor-guide/dev-setup.md) - Set up your environment
3. [Adding Document Sources](contributor-guide/document-sources.md) - Add new regulations
4. [Code Style Guide](contributor-guide/code-style.md) - Follow our standards
5. [Testing Guide](contributor-guide/testing.md) - Write and run tests
6. [Pull Request Workflow](contributor-guide/pull-requests.md) - Submit your changes

### I want to customize or extend GreenGovRAG

**Start here if you want to customize the RAG pipeline or add features:**

1. [System Architecture](developer-guide/architecture/overview.md) - Understand the design
2. [RAG Pipeline Deep Dive](developer-guide/architecture/rag-pipeline.md) - How RAG works
3. [ETL Pipeline Guide](developer-guide/architecture/etl-pipeline.md) - Document processing
4. [Plugin System](developer-guide/architecture/plugin-system.md) - Extensibility
5. [Metadata Standards](developer-guide/metadata-standards.md) - ESG & geospatial tags
6. [Citation System](developer-guide/citations.md) - Legal-grade citations

### I want to deploy GreenGovRAG

**Start here if you want to deploy to production:**

1. [Deployment Overview](deployment/overview.md) - Choose your deployment
2. [Cloud Provider Comparison](.local/cloud-comparison.md) - AWS vs Azure vs Local
3. [Local Docker Setup](deployment/local-docker.md) - Development environment
4. [AWS Deployment](deployment/aws.md) - Deploy on AWS
5. [Azure Deployment](deployment/azure.md) - Deploy on Azure
6. [Production Checklist](deployment/production-checklist.md) - Go-live requirements

## Documentation Structure

### User Guide
Learn how to use GreenGovRAG effectively:

- [Querying the System](user-guide/querying.md) - API and CLI usage
- [Vector Stores](user-guide/vector-stores.md) - FAISS vs Qdrant
- [Caching](user-guide/caching.md) - LLM response caching for cost savings
- [Monitoring](user-guide/monitoring.md) - Health checks and metrics
- [Troubleshooting](user-guide/troubleshooting.md) - Common issues and solutions

### Contributor Guide
For open-source contributors:

- [Overview](contributor-guide/overview.md) - How to contribute
- [Development Setup](contributor-guide/dev-setup.md) - Local environment
- [Adding Document Sources](contributor-guide/document-sources.md) - New regulations
- [Code Style](contributor-guide/code-style.md) - Ruff, MyPy, standards
- [Testing](contributor-guide/testing.md) - Write and run tests
- [Pull Requests](contributor-guide/pull-requests.md) - PR workflow

### Developer Guide
For advanced customization:

- **Architecture**
  - [System Overview](developer-guide/architecture/overview.md) - High-level design
  - [RAG Pipeline](developer-guide/architecture/rag-pipeline.md) - RAG internals
  - [ETL Pipeline](developer-guide/architecture/etl-pipeline.md) - Document processing
  - [Plugin System](developer-guide/architecture/plugin-system.md) - Extensibility
- **Components**
  - [Metadata Standards](developer-guide/metadata-standards.md) - ESG & geospatial
  - [Citation System](developer-guide/citations.md) - Legal-grade citations
  - [Cloud Storage](developer-guide/cloud-storage.md) - Multi-cloud architecture
- **Customization**
  - [LLM Configuration](developer-guide/llm-config.md) - Switching LLM providers
  - [Custom Parsers](developer-guide/custom-parsers.md) - Build custom parsers
  - [Custom Embeddings](developer-guide/custom-embeddings.md) - Custom embedding models

### Deployment
Production deployment guides:

- [Overview](deployment/overview.md) - Deployment options
- [Local Docker](deployment/local-docker.md) - Docker Compose setup
- [AWS](deployment/aws.md) - AWS ECS, S3, RDS
- [Azure](deployment/azure.md) - Azure Container Apps, Blob Storage
- [Cloud Comparison](.local/cloud-comparison.md) - Cost and feature matrix
- [Production Checklist](deployment/production-checklist.md) - Security, scaling, backups
- [Monitoring](deployment/monitoring.md) - Logs, metrics, alerts

### API Reference
Comprehensive API documentation:

- [REST API](api-reference/rest-api.md) - OpenAPI/Swagger docs
- **Python API** (Auto-generated)
  - [RAG Module](api-reference/python/rag.md) - Vector stores, LLMs, embeddings
  - [ETL Module](api-reference/python/etl.md) - Document processing pipeline
  - [Models](api-reference/python/models.md) - Database models
  - [Cloud Module](api-reference/python/cloud.md) - Cloud storage

### Reference
Quick lookup documentation:

- [Data Sources](reference/data-sources.md) - Regulatory document catalog
- [Plugin API](reference/plugin-api.md) - Plugin development reference
- [Configuration Options](reference/config-reference.md) - All `.env` variables
- [CLI Commands](reference/cli-reference.md) - All CLI commands
- [Database Schema](reference/database-schema.md) - Tables and relationships
- [Glossary](reference/glossary.md) - RAG, LGA, NGER, ESG, etc.

## Quick Links

### Most Popular Guides
- [Quick Start Guide](getting-started/quickstart.md) - Get up and running fast
- [Adding Document Sources](contributor-guide/document-sources.md) - Contribute new regulations
- [Cloud Storage Guide](developer-guide/cloud-storage.md) - Multi-cloud setup
- [Vector Stores](user-guide/vector-stores.md) - FAISS vs Qdrant
- [Cloud Provider Comparison](.local/cloud-comparison.md) - Choose your cloud

### Common Tasks
- [Submit a query via API](user-guide/querying.md#api-usage)
- [Add a new document source](contributor-guide/document-sources.md#creating-a-new-plugin)
- [Switch from FAISS to Qdrant](user-guide/vector-stores.md#migrating-from-faiss-to-qdrant)
- [Deploy on AWS](deployment/aws.md)
- [Configure LLM provider](reference/config-reference.md#llm-configuration)

### Troubleshooting
- [Common installation issues](getting-started/installation.md#troubleshooting)
- [Vector store problems](user-guide/vector-stores.md#troubleshooting)
- [Cloud storage errors](developer-guide/cloud-storage.md#troubleshooting)
- [Deployment issues](deployment/production-checklist.md#common-issues)

## Technology Stack

**Backend:**
- Python 3.12
- FastAPI for REST API
- SQLModel for ORM
- LangChain for RAG
- PostgreSQL with pgvector

**RAG:**
- FAISS/Qdrant for vector storage
- HuggingFace embeddings
- Multi-LLM support (OpenAI, Anthropic, AWS Bedrock, Azure)

**ETL:**
- Airflow (local dev)
- GitHub Actions (production)
- Unstructured.io for PDF parsing

**Cloud:**
- AWS (ECS Fargate, S3, RDS)
- Azure (Container Apps, Blob Storage, PostgreSQL)
- Docker for containerization

## Project Status

**Current Version:** 0.1.0 (Pre-release)

**What's Working:**
- **RAG query pipeline with geospatial filtering
- **Multi-LLM support (OpenAI, Anthropic, AWS Bedrock, Azure)
- **Vector stores (FAISS, Qdrant)
- **Cloud storage (AWS S3, Azure Blob, Local)
- **ETL pipeline with plugin system
- **Legal-grade citations
- **AWS and Azure deployment

**In Progress:**
- 🚧 React frontend (API-first development)
- 🚧 User authentication (API currently open)
- 🚧 MkDocs static site for documentation

**Planned:**
- 📋 Multi-LGA query support
- 📋 Real-time document update webhooks
- 📋 Parcel-level geospatial queries
- 📋 Export to PDF/DOCX reports

## Support & Community

### Get Help

- **GitHub Issues:** [Report bugs or request features](https://github.com/sdp5/green-gov-rag/issues)
- **Email:** contact@sundeep.id.au
- **Documentation:** You're here! 📚

### Contributing

We welcome contributions! See the [Contributor Guide](contributor-guide/overview.md) to get started.

**Quick links:**
- [Code of Conduct](about/code-of-conduct.md)
- [Contributing Guidelines](contributor-guide/overview.md)
- [Development Setup](contributor-guide/dev-setup.md)
- [Pull Request Process](contributor-guide/pull-requests.md)

### Resources

- **GitHub Repository:** https://github.com/sdp5/green-gov-rag
- **Project Board:** https://github.com/sdp5/green-gov-rag/projects
- **Changelog:** [View release history](about/changelog.md)
- **License:** [MIT License](about/license.md)

## About

**Author:** Sundeep Anand (contact@sundeep.id.au)

**Purpose:** GreenGovRAG helps individuals, businesses, and government navigate Australia's complex environmental and planning regulations through AI-powered document retrieval.

**Data Sovereignty:** All regulatory documents are sourced from official Australian government websites. See [Data Sources](reference/data-sources.md) for details.

---

**Ready to get started?** Choose your path above or jump straight to the [Quick Start Guide](getting-started/quickstart.md)!

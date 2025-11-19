# Changelog

All notable changes to GreenGovRAG will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- User authentication (OAuth2/JWT)
- Multi-LGA query support
- Real-time document update webhooks
- Parcel-level geospatial queries
- Multi-lingual support (English priority)
- PDF/DOCX report exports
- Blue-green deployment support

## [0.1.0] - 2025-11-22

### Added
- Initial release of GreenGovRAG
- Core RAG pipeline with LangChain
- Multi-provider LLM support (OpenAI, Azure, Bedrock, Anthropic)
- Vector store abstraction (FAISS, Qdrant)
- Hybrid search (BM25 + vector similarity)
- PostgreSQL database with pgvector extension
- FastAPI backend with REST API
- Document source plugin system:
  - Federal legislation sources
  - State legislation sources
  - Local government sources
  - Emissions reporting sources
- Hierarchical PDF parsing with LLMSherpa
- Legal-grade citation metadata:
  - Section hierarchy tracking
  - Page numbers and ranges
  - Clause references
  - Deep linking
- Geospatial filtering:
  - LGA (Local Government Area) filtering
  - Location NER (Named Entity Recognition)
  - PostGIS integration
- ETL pipeline:
  - Document download and validation
  - Text chunking with overlap
  - Embedding generation
  - Vector indexing
  - Airflow orchestration (local dev)
  - GitHub Actions scheduling (production)
- Trust scoring system
- Query result caching (DynamoDB, Redis, PostgreSQL)
- AWS deployment:
  - ECS Fargate for backend
  - RDS PostgreSQL
  - EC2 Spot for Qdrant
  - S3 + CloudFront for frontend
  - DynamoDB for caching
  - API Gateway HTTP API
  - AWS CDK infrastructure-as-code
- Azure deployment:
  - Container Apps for backend
  - PostgreSQL Flexible Server
  - Container Instances for Qdrant
  - Blob Storage + Front Door
  - Cosmos DB for caching
  - Bicep infrastructure-as-code
- Docker Compose for local development
- Comprehensive monitoring:
  - Health check endpoints
  - CloudWatch Logs (AWS)
  - Application Insights (Azure)
  - Query analytics
  - Performance metrics
- CLI tool (greengovrag-cli):
  - ETL commands
  - RAG query commands
  - Database management
  - Vector store operations
  - Admin commands
- API documentation (Swagger/OpenAPI)
- MkDocs Material documentation site
- Automated testing suite (pytest)
- Code quality tools:
  - Ruff (linting and formatting)
  - MyPy (type checking)
  - Pre-commit hooks
- CI/CD pipelines (GitHub Actions)
- Example queries and use cases
- Development Docker environment with Airflow UI

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- Rate limiting on all API endpoints (30 requests/minute)
- CORS configuration for frontend origins
- Environment variable-based secrets management
- AWS Secrets Manager / Azure Key Vault integration
- HTTPS enforcement in production
- Private subnets for database and vector store

## Version History

### Release Versioning

GreenGovRAG follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backward compatible)
- **PATCH** version: Bug fixes (backward compatible)

### Release Schedule

- **Major releases**: As needed for breaking changes
- **Minor releases**: Quarterly (feature releases)
- **Patch releases**: As needed for bug fixes
- **Security patches**: Immediate upon discovery

### Supported Versions

| Version | Supported | End of Support |
|---------|-----------|----------------|
| 0.1.x   | Yes       | TBD            |

## Migration Guides

### From 0.1.0 to Future Versions

Migration guides will be provided here when new versions are released.

## Deprecation Policy

Features marked as deprecated will be:
1. Announced in changelog with deprecation version
2. Maintained for at least 2 minor versions
3. Removed in next major version

Deprecated features will emit warnings when used.

## Breaking Changes

### Future Breaking Changes

None currently planned. Any breaking changes will be clearly documented here before release.

## Contributors

See [GitHub Contributors](https://github.com/sdp5/green-gov-rag/graphs/contributors) for full list.

**Lead Developer**: Sundeep Anand (contact@sundeep.id.au)

## Acknowledgments

- **LangChain**: RAG framework
- **FastAPI**: Modern Python web framework
- **LLMSherpa**: Hierarchical PDF parsing
- **Qdrant**: Vector database
- **OpenAI**: GPT models
- **Anthropic**: Claude models
- **AWS**: Cloud infrastructure
- **Azure**: Cloud infrastructure
- **Material for MkDocs**: Documentation theme

## License

Copyright © 2025-2026 Sundeep Anand

This project is licensed under the MIT License - see the [LICENSE](license.md) file for details.

---

**Last Updated**: 2025-11-22

# License

## MIT License

Copyright © 2024-2025 Sundeep Anand

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Third-Party Licenses

GreenGovRAG incorporates open-source software licensed under various terms:

### Core Dependencies

#### LangChain
- **License**: MIT License
- **Project**: https://github.com/langchain-ai/langchain
- **Used for**: RAG pipeline framework

#### FastAPI
- **License**: MIT License
- **Project**: https://github.com/tiangolo/fastapi
- **Used for**: Backend API framework

#### SQLModel
- **License**: MIT License
- **Project**: https://github.com/tiangolo/sqlmodel
- **Used for**: Database ORM

#### Pydantic
- **License**: MIT License
- **Project**: https://github.com/pydantic/pydantic
- **Used for**: Data validation and settings management

#### PostgreSQL
- **License**: PostgreSQL License (similar to MIT/BSD)
- **Project**: https://www.postgresql.org/
- **Used for**: Database

#### pgvector
- **License**: PostgreSQL License
- **Project**: https://github.com/pgvector/pgvector
- **Used for**: Vector similarity search in PostgreSQL

### Vector Stores

#### FAISS
- **License**: MIT License
- **Project**: https://github.com/facebookresearch/faiss
- **Copyright**: Facebook AI Research
- **Used for**: Local vector search

#### Qdrant
- **License**: Apache License 2.0
- **Project**: https://github.com/qdrant/qdrant
- **Used for**: Production vector database

### LLM Providers

#### OpenAI Python SDK
- **License**: MIT License
- **Project**: https://github.com/openai/openai-python
- **Used for**: OpenAI API integration

#### Anthropic Python SDK
- **License**: MIT License
- **Project**: https://github.com/anthropics/anthropic-sdk-python
- **Used for**: Claude API integration

### PDF Processing

#### LLMSherpa
- **License**: Apache License 2.0
- **Project**: https://github.com/nlmatics/llmsherpa
- **Used for**: Hierarchical PDF parsing

#### PyPDF2
- **License**: BSD 3-Clause License
- **Project**: https://github.com/py-pdf/pypdf
- **Used for**: PDF text extraction

### Embedding Models

#### Sentence Transformers
- **License**: Apache License 2.0
- **Project**: https://github.com/UKPLab/sentence-transformers
- **Used for**: Text embedding generation

#### HuggingFace Transformers
- **License**: Apache License 2.0
- **Project**: https://github.com/huggingface/transformers
- **Used for**: Pre-trained model loading

### Web Framework

#### Uvicorn
- **License**: BSD 3-Clause License
- **Project**: https://github.com/encode/uvicorn
- **Used for**: ASGI server

#### Starlette
- **License**: BSD 3-Clause License
- **Project**: https://github.com/encode/starlette
- **Used for**: ASGI framework (FastAPI dependency)

### Development Tools

#### Pytest
- **License**: MIT License
- **Project**: https://github.com/pytest-dev/pytest
- **Used for**: Testing framework

#### Ruff
- **License**: MIT License
- **Project**: https://github.com/astral-sh/ruff
- **Used for**: Linting and formatting

#### MyPy
- **License**: MIT License
- **Project**: https://github.com/python/mypy
- **Used for**: Static type checking

#### Alembic
- **License**: MIT License
- **Project**: https://github.com/sqlalchemy/alembic
- **Used for**: Database migrations

### Frontend (React)

#### React
- **License**: MIT License
- **Project**: https://github.com/facebook/react
- **Used for**: Frontend UI framework

#### Vite
- **License**: MIT License
- **Project**: https://github.com/vitejs/vite
- **Used for**: Frontend build tool

#### TypeScript
- **License**: Apache License 2.0
- **Project**: https://github.com/microsoft/TypeScript
- **Used for**: Frontend type safety

### Documentation

#### MkDocs
- **License**: BSD 2-Clause License
- **Project**: https://github.com/mkdocs/mkdocs
- **Used for**: Documentation site generation

#### Material for MkDocs
- **License**: MIT License
- **Project**: https://github.com/squidfunk/mkdocs-material
- **Used for**: Documentation theme

#### mkdocstrings
- **License**: ISC License
- **Project**: https://github.com/mkdocstrings/mkdocstrings
- **Used for**: API documentation generation

### Infrastructure

#### Docker
- **License**: Apache License 2.0
- **Project**: https://github.com/docker/docker-ce
- **Used for**: Containerization

#### Docker Compose
- **License**: Apache License 2.0
- **Project**: https://github.com/docker/compose
- **Used for**: Multi-container orchestration

#### AWS CDK
- **License**: Apache License 2.0
- **Project**: https://github.com/aws/aws-cdk
- **Used for**: AWS infrastructure-as-code

## Data Sources Attribution

GreenGovRAG retrieves and processes publicly available Australian government documents:

### Federal Sources
- **Environment Protection and Biodiversity Conservation Act 1999** (Commonwealth of Australia)
- **National Greenhouse and Energy Reporting Act 2007** (Commonwealth of Australia)
- **Clean Energy Regulator Guidelines** (Clean Energy Regulator)
- Licensed under Creative Commons Attribution 4.0 International (where applicable)

### State Sources
- **NSW Environmental Planning & Assessment Act** (NSW Government)
- **SA Native Vegetation Act** (SA Government)
- Licensed under respective state government open data licenses

### Local Sources
- Various Local Government Area planning schemes
- Licensed under respective council open data licenses

### International Standards
- **GHG Protocol** (World Resources Institute & World Business Council for Sustainable Development)
- **ISSB Standards** (IFRS Foundation)
- Licensed under respective organizational terms

**Disclaimer**: GreenGovRAG provides information retrieval and analysis. Users should verify information with original sources for legal/regulatory compliance.

## Data Privacy

GreenGovRAG does not:

- Collect personal information from users
- Store user queries persistently (unless explicitly configured)
- Share data with third parties (except LLM providers for query processing)

Query logs (if enabled) are used solely for:

- System analytics and improvement
- Performance monitoring
- Debugging

## Trademarks

- OpenAI and GPT are trademarks of OpenAI, Inc.
- Claude is a trademark of Anthropic, PBC
- AWS, Amazon Bedrock are trademarks of Amazon.com, Inc.
- Azure is a trademark of Microsoft Corporation
- All other trademarks are property of their respective owners

## Commercial Use

GreenGovRAG is free to use commercially under the MIT License. However:

1. **LLM Provider Costs**: Usage incurs costs from OpenAI/Azure/Bedrock/Anthropic
2. **Cloud Infrastructure Costs**: AWS/Azure usage incurs cloud provider charges
3. **No Warranty**: Software provided "as is" without warranty (see MIT License above)

## Contributing

By contributing to GreenGovRAG, you agree that your contributions will be licensed under the MIT License.

See [Contributor Guide](../contributor-guide/overview.md) for contribution process.

## Questions

For licensing questions, contact:

- **GitHub Issues**: https://github.com/sdp5/green-gov-rag/issues

## Full License Text

The complete MIT License text is available at:

- **Repository**: https://github.com/sdp5/green-gov-rag/blob/main/LICENSE
- **OSI**: https://opensource.org/licenses/MIT

---

**Last Updated**: 2025-11-22

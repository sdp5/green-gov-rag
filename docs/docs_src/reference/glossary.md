# Glossary

> Key terms and concepts in GreenGovRAG

## General Terms

### RAG (Retrieval-Augmented Generation)
A pattern that combines information retrieval from a knowledge base with large language model generation to produce factual, grounded responses.

### Vector Embedding
A numerical representation of text in high-dimensional space, where semantically similar texts are positioned close together.

### Semantic Search
Search that understands meaning and context rather than just keyword matching. Uses vector embeddings to find conceptually similar content.

### Hybrid Search
Combination of keyword-based search (BM25) and semantic search (vector similarity) for improved retrieval accuracy.

### Chunking
Process of splitting large documents into smaller segments (chunks) suitable for embedding and retrieval.

### ETL (Extract, Transform, Load)
Pipeline for downloading source documents, processing them into chunks, generating embeddings, and loading into the vector store.

## Document Types

### Federal Legislation
Commonwealth/national-level laws and regulations applicable across Australia.

**Examples**: EPBC Act, NGER Act

### State Legislation
State-specific laws and regulations.

**Examples**: NSW Environmental Planning & Assessment Act, SA Native Vegetation Act

### Local Government Policy
Council-level planning schemes, development controls, and local laws.

**Examples**: City of Adelaide Development Plan, Local Environment Plans (LEPs)

### Emissions Reporting
Documents related to greenhouse gas emissions measurement, reporting, and verification.

**Examples**: NGER Guidelines, GHG Protocol, ISSB Standards

## Geographic Terms

### LGA (Local Government Area)
Geographic area under the jurisdiction of a local council. Identified by ABS (Australian Bureau of Statistics) codes.

**Example**: City of Adelaide (LGA code: 40070)

### Jurisdiction
Level of government authority:

- **Federal**: Commonwealth level
- **State**: NSW, VIC, SA, WA, QLD, TAS, NT, ACT
- **Local**: Council/LGA level

### Spatial Metadata
Geographic information about document applicability (state, LGA codes, spatial scope).

## Technical Terms

### Vector Store
Database optimized for storing and searching high-dimensional vectors.

**Implementations**:

- **FAISS** (Facebook AI Similarity Search): In-memory, file-based
- **Qdrant**: Persistent, distributed vector database

### pgvector
PostgreSQL extension for vector similarity search, enabling hybrid queries combining SQL and semantic search.

### Token
Unit of text for LLM processing. Roughly 0.75 words in English.

**Example**: "The quick brown fox" ≈ 5 tokens

### Embedding Model
Machine learning model that converts text into vector embeddings.

**Default**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)

### HNSW (Hierarchical Navigable Small World)
Graph-based algorithm for approximate nearest neighbor search in vector stores. Provides sub-linear search time.

## LLM Terms

### LLM (Large Language Model)
AI model trained on vast text corpora, capable of understanding and generating human-like text.

**Providers**: OpenAI (GPT-5-mini, GPT-5, GPT-4o), Anthropic (Claude), AWS (Bedrock), Azure (OpenAI)

### Prompt
Input text provided to an LLM to elicit a response.

### Temperature
Parameter controlling randomness in LLM output (0.0 = deterministic, 2.0 = very random).

**GreenGovRAG default**: 0.2 (low randomness for factual responses)

### Context Window
Maximum amount of text (in tokens) an LLM can process in a single request.

**Examples**:

- GPT-5-mini: 16K tokens
- GPT-4o: 128K tokens
- Claude 3: 200K tokens

### Hallucination
When an LLM generates plausible-sounding but factually incorrect information. RAG mitigates this by grounding responses in retrieved documents.

## RAG-Specific Terms

### Trust Score
Confidence metric (0.0-1.0) indicating how well the retrieved sources support the generated answer.

**Calculation**: Weighted average of source relevance scores

### Source Document
Original regulatory document retrieved to support an answer.

### Relevance Score
Similarity score (0.0-1.0) indicating how relevant a retrieved document is to the query.

### Citation
Reference to the specific section and page of a source document used in the response.

**Example**: `Clean Energy Regulator (2024), Scope 2 Emissions Guideline, Page 42, Section 3.2.1`

### Deep Link
URL pointing directly to a specific page or section within a source document.

**Example**: `https://example.gov.au/doc.pdf#page=42`

## ESG Terms

### ESG (Environmental, Social, Governance)
Framework for evaluating organizational impacts and sustainability practices.

### NGER (National Greenhouse and Energy Reporting)
Australian legislation requiring large emitters to report greenhouse gas emissions and energy consumption.

### ISSB (International Sustainability Standards Board)
Global body developing sustainability disclosure standards (IFRS S1/S2).

### GHG Protocol
International standard for measuring and reporting greenhouse gas emissions.

### Scope 1 Emissions
Direct emissions from owned or controlled sources.

**Examples**: Company vehicles, on-site fuel combustion

### Scope 2 Emissions
Indirect emissions from purchased electricity, steam, heating, cooling.

### Scope 3 Emissions
All other indirect emissions in the value chain (upstream and downstream).

**Examples**: Purchased goods, business travel, waste disposal, product use

### Carbon Neutral
Achieving net-zero carbon emissions by balancing emissions with carbon removal or offsets.

### GHG (Greenhouse Gas)
Gases that trap heat in the atmosphere: CO₂, CH₄, N₂O, SF₆, HFCs, PFCs, NF₃.

## Database Terms

### ORM (Object-Relational Mapping)
Programming technique that maps database tables to Python classes.

**GreenGovRAG uses**: SQLModel (built on SQLAlchemy + Pydantic)

### Migration
Versioned change to database schema, managed by Alembic.

### JSONB
PostgreSQL's binary JSON data type, allowing efficient querying of nested structured data.

### Index
Database structure that speeds up data retrieval.

**Types**:

- **B-tree**: Standard index for equality/range queries
- **GIN**: Generalized Inverted Index for JSONB/array data
- **IVFFlat**: Index for vector similarity search (pgvector)

### Connection Pool
Pre-established database connections reused for multiple queries, improving performance.

## Cloud Terms

### CDK (Cloud Development Kit)
AWS infrastructure-as-code framework using TypeScript/Python.

### Bicep
Azure's domain-specific language for infrastructure-as-code.

### ECS (Elastic Container Service)
AWS container orchestration service.

### Fargate
Serverless compute engine for containers (AWS ECS/EKS).

### Container Apps
Azure's serverless container platform.

### RDS (Relational Database Service)
AWS managed PostgreSQL/MySQL service.

### Spot Instance
AWS EC2 instance at reduced price (up to 70% off) with potential interruption.

### CloudWatch
AWS monitoring and logging service.

### Application Insights
Azure monitoring and telemetry service.

## API Terms

### REST API
Web API using HTTP methods (GET, POST, PUT, DELETE) for resource manipulation.

### FastAPI
Modern Python web framework for building APIs with automatic OpenAPI documentation.

### Swagger/OpenAPI
API documentation standard. GreenGovRAG auto-generates docs at `/docs`.

### CORS (Cross-Origin Resource Sharing)
Security mechanism allowing web apps from one domain to access resources from another.

### Rate Limiting
Restricting the number of API requests a client can make in a time period.

**GreenGovRAG default**: 30 requests/minute

### Endpoint
Specific URL path for accessing API functionality.

**Example**: `/api/query` (RAG query endpoint)

## Development Terms

### Docker
Platform for running applications in isolated containers.

### Docker Compose
Tool for defining and running multi-container Docker applications.

### Airflow
Workflow orchestration platform for scheduling and monitoring ETL pipelines.

**Note**: Used in local development only; production uses GitHub Actions.

### CI/CD (Continuous Integration/Continuous Deployment)
Automated testing and deployment pipeline.

**GreenGovRAG uses**: GitHub Actions

### Alembic
Database migration tool for SQLAlchemy/SQLModel.

### Ruff
Fast Python linter and code formatter.

### MyPy
Static type checker for Python.

### Pytest
Python testing framework.

## Performance Terms

### Latency
Time delay between request and response.

**Target**: < 2 seconds (p95) for RAG queries

### Throughput
Number of requests processed per unit time.

**Example**: 1000 queries/hour

### Cache Hit Rate
Percentage of requests served from cache rather than recomputed.

**Target**: > 50%

### p50, p95, p99
Percentile metrics:

- **p50** (median): 50% of requests faster than this
- **p95**: 95% faster (5% slower)
- **p99**: 99% faster (1% slower)

### Auto-scaling
Automatically adjusting compute resources based on load.

## Monitoring Terms

### Health Check
Endpoint verifying system components are operational.

**GreenGovRAG**: `/api/health`

### Alert
Automated notification when metrics exceed thresholds.

**Examples**: High CPU, error rate spike

### Dashboard
Visual display of system metrics and KPIs.

**Tools**: CloudWatch, Azure Monitor, Grafana

### Trace
Record of a request's path through distributed system components.

**Tools**: AWS X-Ray, Application Insights

### Log
Time-stamped record of events and errors.

**Formats**: JSON (structured), plain text

## Acronyms

| Acronym | Full Term |
|---------|-----------|
| ABS | Australian Bureau of Statistics |
| API | Application Programming Interface |
| AWS | Amazon Web Services |
| BM25 | Best Matching 25 (ranking function) |
| CDN | Content Delivery Network |
| CDK | Cloud Development Kit (AWS) |
| CER | Clean Energy Regulator |
| CLI | Command Line Interface |
| CORS | Cross-Origin Resource Sharing |
| CPU | Central Processing Unit |
| CRUD | Create, Read, Update, Delete |
| CSV | Comma-Separated Values |
| DDoS | Distributed Denial of Service |
| DNS | Domain Name System |
| ECS | Elastic Container Service (AWS) |
| EIA | Environmental Impact Assessment |
| EPBC | Environment Protection and Biodiversity Conservation (Act) |
| ESG | Environmental, Social, Governance |
| ETL | Extract, Transform, Load |
| FAISS | Facebook AI Similarity Search |
| GHG | Greenhouse Gas |
| GIN | Generalized Inverted Index |
| GPT | Generative Pre-trained Transformer |
| HNSW | Hierarchical Navigable Small World |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | HTTP Secure |
| IAM | Identity and Access Management |
| IaC | Infrastructure as Code |
| ISSB | International Sustainability Standards Board |
| JSON | JavaScript Object Notation |
| JSONB | JSON Binary (PostgreSQL) |
| JWT | JSON Web Token |
| KPI | Key Performance Indicator |
| LEP | Local Environment Plan |
| LGA | Local Government Area |
| LLM | Large Language Model |
| NER | Named Entity Recognition |
| NGER | National Greenhouse and Energy Reporting |
| NSG | Network Security Group (Azure) |
| OAuth | Open Authorization |
| OIDC | OpenID Connect |
| ORM | Object-Relational Mapping |
| PDF | Portable Document Format |
| PII | Personally Identifiable Information |
| PITR | Point-In-Time Recovery |
| QPS | Queries Per Second |
| RAG | Retrieval-Augmented Generation |
| RBAC | Role-Based Access Control |
| RDS | Relational Database Service (AWS) |
| REST | Representational State Transfer |
| RTO | Recovery Time Objective |
| RPO | Recovery Point Objective |
| S3 | Simple Storage Service (AWS) |
| SLA | Service Level Agreement |
| SQL | Structured Query Language |
| SSM | Systems Manager (AWS) |
| SSL | Secure Sockets Layer |
| TLS | Transport Layer Security |
| TTL | Time To Live |
| URL | Uniform Resource Locator |
| VNet | Virtual Network (Azure) |
| VPC | Virtual Private Cloud (AWS) |
| WAF | Web Application Firewall |
| YAML | YAML Ain't Markup Language |

## See Also

- [Configuration Reference](config-reference.md) - All configuration options
- [CLI Reference](cli-reference.md) - Command-line tools
- [Database Schema](database-schema.md) - Database structure
- [Plugin API](plugin-api.md) - Document source plugins

---

**Last Updated**: 2025-11-22

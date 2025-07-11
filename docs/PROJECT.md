## Repository Structure 

```bash
green-gov-rag/
├── .github/
│   └── workflows/             # CI/CD GitHub Actions (test, lint, deploy)
│       └── ci.yml
│
├── greengovrag/               # Python package root
│   ├── __init__.py
│   ├── app/                   # Streamlit frontend (still importable)
│   │   ├── __init__.py
│   │   ├── ui.py
│   │   ├── map.py
│   │   └── config.py
│   ├── api/                   # FastAPI backend
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── routes.py
│   ├── rag/                   # LangChain RAG logic
│   │   ├── __init__.py
│   │   ├── rag_chain.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   ├── filters.py
│   │   └── agent_tools.py
│   ├── etl/                   # ETL for doc processing
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   ├── chunker.py
│   │   ├── loader.py
│   │   ├── utils.py
│   │   └── validators.py
│   └── scripts/              # Optional: CLI tools (entry_points)
│       ├── __init__.py
│       ├── download_docs.py
│       ├── build_embeddings.py
│       └── evaluate_model.py
│
├── configs/
│   ├── documents_config.yml   # Source list with metadata + sovereignty flag
│   └── logging_config.yaml    # Logging, format, levels
│
├── data/
│   ├── raw/                   # Original downloaded documents (PDF, HTML)
│   ├── processed/             # Chunked docs, embeddings (cache)
│   └── geo/                   # GeoJSON files (ABS, LGAs, SA2s)
│
├── models/                    # LLMs or embedding models (if local)
│   └── README.md
│
├── notebooks/                 # Jupyter notebooks (exploration, evaluation)
│   └── evaluation.ipynb
│
├── tests/                     # Unit tests and test data
│   ├── test_rag.py
│   ├── test_etl.py
│   └── test_ui.py
│
├── deploy
│   ├── aws
│   │     ├── app.py
│   │     ├── buildspec.yml
│   │     ├── cdk.json
│   │     ├── greengovrag_stack.py
│   │     └── README.md
│   ├── docker
│   │     ├── airflow
│   │     │  ├── dags
│   │     │  │  └── rag_pipeline_dag.py
│   │     │  ├── Dockerfile
│   │     │  └── README.md
│   │     ├── docker-compose.airflow.yml
│   │     ├── docker-compose.yml
│   │     ├── Dockerfile
│   │     └── start.sh
│   └── README.md
│
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Optional (if using Poetry)
├── README.md
├── LICENSE
└── .env.example               # Env config sample (for OpenAI key, etc.)
```

## System Architecture (High-Level)

                        ┌──────────────────────────────┐
                        │        USER INTERFACE        │
                        │ ──────────────────────────── │
                        │  🌐 Streamlit App            │
                        │  🗺️ Folium Map + GeoJSON     │
                        │  🔍 Search Input Box         │
                        │  📎 Answer + Source View     │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
               ┌────────────────────────────────────────────┐
               │               QUERY HANDLER                │
               │ ─────────────────────────────────────────  │
               │  FastAPI backend / LangChain Agent         │
               │  → RAG Tool (LangChain Tool/Agent)         │
               └────────────────┬───────────────────────────┘
                                │
         ┌─────────────────────▼────────────────────────┐
         │            DOCUMENT RETRIEVAL ENGINE         │
         │ ──────────────────────────────────────────── │
         │  LangChain VectorStore (FAISS/Qdrant)        │
         │  Metadata Filtering (e.g., LGA, Topic)       │
         │  Embeddings (OpenAI / HuggingFace)           │
         └─────────────────────┬────────────────────────┘
                               │
             ┌────────────────▼────────────────────┐
             │         DOCUMENT CHUNK STORE        │
             │ ─────────────────────────────────── │
             │  Vector Index (FAISS/Qdrant)        │
             │  Metadata DB (PostgreSQL/PostGIS)   │
             └────────────────▲────────────────────┘
                              │
             ┌────────────────▼────────────────────┐
             │        DATA INGESTION PIPELINE      │
             │ ─────────────────────────────────── │
             │  YAML config for docs               │
             │  ETL (Airflow / Prefect)            │
             │    📥 Extract: PDF/HTML, GeoJSON    │
             │    🧹 Transform: Chunk, Clean, OCR  │
             │    📦 Load: FAISS + PostgreSQL      │
             │  Great Expectations (optional)      │
             └────────────────▲────────────────────┘
                              │
        ┌─────────────────────┴────────────────────────┐
        │             RAW DATA SOURCES                 │
        │ ───────────────────────────────────────────  │
        │ 🏛️ EPBC Act, EIA Policies (Fed/State)        │
        │ 🏙️ Council Policies (Adelaide, Sydney...)    │
        │ 🏗️ Building Codes (ABCB, NCC)                │
        │ 🗺️ Geo data (ABS, PostGIS, Shapefiles)       │
        └──────────────────────────────────────────────┘


## Components Summary

### Data Engineering Layer

| Component           | Description                                                                |
| ------------------- | -------------------------------------------------------------------------- |
| **ETL Pipeline**    | Modular scripts/DAGs to download, parse, clean, chunk documents            |
| **Metadata Store**  | PostgreSQL (or PostGIS) for storing document metadata + ingestion logs     |
| **Vector Store**    | FAISS or Qdrant used via LangChain for chunk storage and similarity search |
| **Data Validation** | Great Expectations or custom checks for document quality                   |

#### File Types for RAG Ingestion

| Type        | Description                    | Tools to Process                    |
| ----------- | ------------------------------ | ----------------------------------- |
| `.pdf`      | Most common for policies/laws  | PyMuPDF, OCR, pdfplumber            |
| `.html`     | Online policy pages            | BeautifulSoup, LangChain HTMLLoader |
| `.docx`     | Draft policies (less common)   | docx2txt, python-docx               |
| `.geojson`  | For maps/overlays              | geopandas, folium, streamlit-folium |
| `.csv/xlsx` | Tabular rules (offsets, zones) | pandas                              |


### Generative AI Layer

| Component           | Description                                                             |
| ------------------- | ----------------------------------------------------------------------- |
| **Embedding Model** | OpenAI or HuggingFace model to convert chunks into vector embeddings    |
| **RAG Chain**       | LangChain-based retrieval and answer generation pipeline                |
| **Agent Tooling**   | LangChain Tool & AgentExecutor for intelligent use of RAG with metadata |


### User Interface

| Component          | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| **Streamlit App**  | Frontend with search bar, results panel, and clickable map   |
| **Folium Map**     | Overlaid with GeoJSON of LGAs, clickable to filter questions |
| **Optional Voice** | Whisper for voice queries via mic                            |

### Deployment & Infra

| Component                 | Description                                 |
| ------------------------- | ------------------------------------------- |
| **Docker**                | Containerized deployment                    |
| **ECS / Streamlit Cloud** | Choice of AWS or managed PaaS deployment    |
| **S3 or Blob**            | Optional: Store raw documents & logs        |
| **Terraform/CDK**         | Optional: Infra as code for reproducibility |


## Example Flow

1. **Ingestion**:

   - Airflow downloads 10+ policy documents.
   - Extracts text, chunks with metadata.
   - Embeds to FAISS, logs metadata in PostgreSQL.

2. **User Query**:

   - User types or clicks a region (e.g. "Port Adelaide Enfield").
   - Query + metadata filters → LangChain RAG → LLM.

3. **Answer**:

   - Streamlit displays result, citations, and document source.

4. **Analytics (Optional)**:

   - Dashboards for LGA coverage, ingestion status, usage logs.


## What Makes It Unique?

| Feature                          | How It Helps                                                               |
| -------------------------------- | -------------------------------------------------------------------------- |
| **RAG-based QA**                 | Combines LLM reasoning with reliable source-grounded info                  |
| **LGA-aware Metadata Filtering** | Focuses answers based on location                                          |
| **Interactive Map UI**           | Select an LGA to auto-filter queries                                       |
| **PostgreSQL/PostGIS Backend**   | Enables advanced spatial joins and filtering                               |
| **Automated Ingestion Pipeline** | Keeps the regulatory dataset fresh and structured via ETL                  |
| **Agent-Driven Extensions**      | Allows chaining tools (e.g., summarisation, source explorer) via LangChain |

## Technology Stack

| Layer               | Component         | Tool(s) / Frameworks                                                             |
| ------------------- | ----------------- | -------------------------------------------------------------------------------- |
| **Frontend UI**     | Web Interface     | Streamlit, `streamlit-folium`, Folium, GeoJSON, Bootstrap Icons                  |
|                     | Map Integration   | Folium, GeoPandas, ABS GeoBoundaries (LGA, SA2)                                  |
| **Backend API**     | API Server        | FastAPI or Flask                                                                 |
| **RAG Engine**      | Retrieval         | LangChain VectorStore (FAISS or Qdrant), Metadata Filtering                      |
|                     | Generation        | OpenAI GPT, AWS Bedrock (Claude, Titan), Local LLM (e.g., Mistral)               |
|                     | Agent (optional)  | LangChain Tools + AgentExecutor                                                  |
| **Embedding**       | Text Embedding    | OpenAI Embeddings (text-embedding-3), HuggingFace Transformers, Instructor-XL    |
| **ETL Pipeline**    | Document Loader   | LangChain PDF/HTML loaders, PyMuPDF, BeautifulSoup, `langchain.document_loaders` |
|                     | ETL Orchestration | Airflow or Prefect, YAML-config ingestion, Cron jobs                             |
|                     | Data Validation   | Great Expectations (optional)                                                    |
| **Vector DB**       | Chunk Storage     | FAISS, Qdrant, Chroma                                                            |
| **Metadata Store**  | Metadata + Audit  | PostgreSQL or PostGIS for geo-aware metadata, timestamps, source info            |
| **Geospatial**      | Region Filters    | PostGIS, GeoPandas, ABS boundaries (LGA, SA2), QGIS for overlays                 |
| **Deployment**      | Containerization  | Docker, docker-compose                                                           |
|                     | Cloud Hosting     | AWS ECS/Fargate, Streamlit Community Cloud, Azure App Service (optional)         |
|                     | Infra as Code     | Terraform, AWS CDK (optional)                                                    |
| **Security & Auth** | Permissions       | Basic Auth, OAuth2 (optional for multi-user)                                     |
| **Logging & QA**    | Monitoring        | Streamlit logs, LangChain debug tools, Sentry (optional), Prometheus (advanced)  |

## Next-Level Robustness

| Area                 | Suggestion                                                           | Benefit                                        |
| -------------------- | -------------------------------------------------------------------- | ---------------------------------------------- |
| 🔐 Security          | Add WAF and restrict public ECS/ALB access                           | Meet stricter compliance                       |
| 📈 Observability     | Integrate Prometheus/Grafana or CloudWatch dashboards                | Monitor LLM latency, embedding cache hits      |
| 🧪 Testing           | Add integration tests for RAG chain and API                          | Catch regressions                              |
| 🔁 Orchestration     | Deploy Airflow or Step Functions for periodic ingestion              | Robust data ingestion                          |
| 📂 Model Abstraction | Abstract LLM choice (OpenAI vs Bedrock vs local LLM)                 | Easier to swap model providers                 |
| 🛰️ Service Mesh     | Use internal routing / service discovery between Streamlit & FastAPI | Scale to multi-container microservices cleanly |

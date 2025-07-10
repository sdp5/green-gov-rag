## Repo Structure

```bash
greengovrag/
├── .github/
│   └── workflows/             # CI/CD GitHub Actions (test, lint, deploy)
│       └── ci.yml
│
├── app/                       # Streamlit frontend app
│   ├── __init__.py
│   ├── ui.py                  # Streamlit logic (text UI + map + results)
│   ├── map.py                 # Folium + GeoJSON integration
│   └── config.py              # Frontend config, UI constants
│
├── api/                       # FastAPI backend (optional)
│   ├── __init__.py
│   ├── main.py                # API endpoints
│   └── routes.py              # Route handlers
│
├── rag/                       # LangChain RAG components
│   ├── __init__.py
│   ├── rag_chain.py           # LangChain RAG chain logic
│   ├── embeddings.py          # Embedding setup (OpenAI, HF)
│   ├── vector_store.py        # FAISS/Qdrant setup
│   ├── filters.py             # Metadata filter logic
│   └── agent_tools.py         # Agent tools (optional)
│
├── etl/                       # ETL pipeline (doc ingestion)
│   ├── __init__.py
│   ├── ingest.py              # Run full document ingestion
│   ├── chunker.py             # PDF/HTML chunking logic
│   ├── loader.py              # Load YAML config and source files
│   ├── utils.py               # Cleaning, preprocessing
│   └── validators.py          # (Optional) Great Expectations or manual checks
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
├── docker/
│   ├── compose/
│   │   ├── docker-compose.yml
│   │   ├── Dockerfile.streamlit
│   │   ├── Dockerfile.api
│   │   ├── .env
│   │   └── airflow.env
│   │
│   ├── airflow/                # Airflow setup (local only)
│   │   ├── dags/
│   │   │   ├── ingest_dag.py
│   │   │   └── preprocess_dag.py
│   │   ├── Dockerfile.airflow
│   │   ├── requirements.txt
│   │   └── airflow.cfg         # Optional override/mount
│   │
│   └── prod/
│       ├── Dockerfile.streamlit
│       ├── Dockerfile.api
│       ├── Dockerfile.etl
│       └── start.sh
│
├── scripts/                   # Dev and helper scripts
│   ├── download_docs.py       # Quick ingestion from URLs
│   ├── build_embeddings.py
│   └── evaluate_model.py
│
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Optional (if using Poetry)
├── README.md
├── LICENSE
└── .env.example               # Env config sample (for OpenAI key, etc.)
```

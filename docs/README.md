# GreenGovRAG

AI Assistant for Australian Environmental & Planning Regulations

## Overview

GreenGovRAG is a Retrieval-Augmented Generation (RAG) system that helps users navigate Australian environmental and planning regulations through AI-powered search with geospatial filtering.

## Problem

Australia's environmental regulations span federal, state, and local jurisdictions:

- **Buried** across hundreds of PDFs and web pages
- **Dense** legal language
- **Location-specific** (LGAs, postcodes)
- **Topic-specific** (biodiversity, emissions, zoning)

This makes it difficult for developers, planners, councils, and consultants to find timely, accurate answers.

## Solution

RAG-powered assistant with:

| Feature | Description |
|---------|-------------|
| **Metadata Tagging** | LGA, state, topic, ESG/NGER compliance |
| **Geospatial Filtering** | Map-based queries ("Show rules in Adelaide") |
| **Source Citations** | Grounded answers with page numbers & sections |
| **Hybrid Search** | Vector + spatial + metadata filtering |

## Target Users

| User | Use Case |
|------|----------|
| Urban Planners | Assess development requirements |
| Council Teams | Validate project compliance |
| Developers | Find permitted activities by region |
| Environmental Officers | Locate EIA/offset guidelines |
| Researchers | Monitor regulatory coverage |

## Example Queries

- "What are native vegetation clearance rules in SA?"
- "Environmental offsets required for land clearing in SA?"
- "Do I need an EIS for a wind farm in regional NSW?"
- "Zoning restrictions for industrial zones in City of Adelaide?"
- "Renewable energy incentives for residential buildings in Victoria?"

## Quick Start

```bash
# Start services
cd deploy/docker
docker-compose up

# Access
# - Frontend: http://localhost:3000
# - API: http://localhost:8000/docs
# - Streamlit: http://localhost:8501
```

## Architecture

```
User Interface (Streamlit/React + Map)
           ↓
    FastAPI Backend
           ↓
    RAG Query Engine
    ├─ Vector Store (FAISS/Qdrant)
    ├─ Metadata Filters (PostgreSQL)
    └─ LLM (OpenAI/Bedrock/Local)
           ↓
    Document Store
    ├─ Vector Index
    ├─ Metadata DB (PostGIS)
    └─ Raw Documents (S3/Local)
           ↓
    ETL Pipeline (Airflow)
    ├─ PDF/HTML Parsing
    ├─ Chunking + Embedding
    └─ Metadata Extraction
```

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, Streamlit, Mapbox/Folium |
| **Backend** | FastAPI, LangChain |
| **RAG** | FAISS/Qdrant, OpenAI/Bedrock |
| **ETL** | Airflow, LLMSherpa, PyMuPDF |
| **Database** | PostgreSQL/PostGIS, SQLModel |
| **Deployment** | Docker, AWS ECS, Azure Container Apps |

## Key Features

- **Hierarchical PDF Parsing** - Section-aware chunking with page numbers
- **ESG Metadata** - NGER/ISSB-compliant emission tracking
- **Spatial Metadata** - LGA-aware filtering with ABS codes
- **Plugin Architecture** - Easy document source contributions
- **Multi-Cloud** - AWS, Azure, or local deployment

## Why It Matters (2025)

- **EPBC Act Reform** - New Environment Protection Australia agency
- **Planning Complexity** - Delays in renewable energy approvals
- **AI in Government** - Services Australia AI Strategy 2025-27
- **Regulatory Demand** - Need for accessible location-specific policy info

## See Also

- [Data Sources](./DATA.md) - Document and geospatial data sources
- [Project Structure](./PROJECT.md) - Repository organization
- [Cloud Deployment](./CLOUD_MIGRATION.md) - Multi-cloud setup
- [Quick Start Guide](../backend/README.md) - Installation and usage

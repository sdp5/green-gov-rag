# GreenGovRAG

An AI Assistant for Navigating Environmental & Sustainability Regulations in Australia

## Problem Statement

Australia's local councils, sustainability officers, and land developers must navigate complex environmental policies (like the EPBC Act, state laws, and local council rules). These are often lengthy PDFs or webpages, difficult to search and understand.

**GreenGovRAG** will be a **generative AI-powered assistant** that uses **Retrieval-Augmented Generation (RAG)** to answer questions like:

- _“What are the native vegetation clearance rules in SA?”_
- _“Does this parcel of land require an EIS before development?”_
- _“Which emissions standards apply to industrial zones in NSW?”_

## System Architecture

                          ┌────────────────────┐
                          │  User Query (UI)   │
                          └────────┬───────────┘
                                   │
                         ┌────────▼────────┐
                         │  FastAPI/Flask  │  ← API Backend
                         └────────┬────────┘
                          Query Embedding
                                   │
       ┌────────────────────────────────────────────┐
       │ LangChain + VectorDB (FAISS or Qdrant)      │ ← Retrieve top chunks
       └────────────────────┬───────────────────────┘
                            │
                ┌───────────▼────────────┐
                │   LLM (OpenAI / Bedrock)│ ← Generate answer with context
                └───────────┬────────────┘
                            │
                    ┌───────▼──────────┐
                    │   Answer + Sources│
                    └───────────────────┘

## Data Sources

| Document Type       | Where to Get It                                                    |
| ------------------- | ------------------------------------------------------------------ |
| EPBC Act (Federal)  | [environment.gov.au](https://www.environment.gov.au)               |
| SA Gov policies     | [legislation.sa.gov.au](https://www.legislation.sa.gov.au)         |
| Local Council plans | e.g., Adelaide City, Port Adelaide Enfield                         |
| NSW Planning Portal | [planningportal.nsw.gov.au](https://www.planningportal.nsw.gov.au) |
| PDF building codes  | State building authorities (PDF scrapers + PyMuPDF)                |

## Sample Queries

- _"What are the environmental offsets required in SA for land clearing?"_
- _"Do I need an environmental impact statement for a wind farm in regional NSW?"_
- _"What are zoning restrictions for coastal development in Victoria?"_
- _"What are the renewable energy incentives available in Adelaide?"_

## Technology Stack

| Component     | Tool(s)                                   |
| ------------- | ----------------------------------------- |
| Backend API   | FastAPI                                   |
| RAG Engine    | LangChain + FAISS                         |
| LLM Provider  | OpenAI API / AWS Bedrock                  |
| Embedding     | OpenAI / HuggingFace + FAISS              |
| Storage       | S3 or Azure Blob (optional)               |
| DB (optional) | PostgreSQL for metadata                   |
| Deployment    | Docker, ECS or Azure App Service          |
| ETL           | PyMuPDF, BeautifulSoup, LangChain loaders |

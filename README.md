# GreenGovRAG

#### An AI Assistant for Navigating Australian Environmental & Planning Regulations

GreenGovRAG is an **AI assistant powered by Retrieval-Augmented Generation (RAG)** that answers user questions by retrieving relevant sections from a curated knowledge base of regulations.

### Data Sources

| Document Type       | Where to Get It                                                    |
| ------------------- | ------------------------------------------------------------------ |
| EPBC Act (Federal)  | [environment.gov.au](https://www.environment.gov.au)               |
| SA Gov policies     | [legislation.sa.gov.au](https://www.legislation.sa.gov.au)         |
| Local Council plans | e.g., Adelaide City, Port Adelaide Enfield                         |
| NSW Planning Portal | [planningportal.nsw.gov.au](https://www.planningportal.nsw.gov.au) |
| PDF building codes  | State building authorities (PDF scrapers + PyMuPDF)                |

### Sample Queries

- _"Do I need an environmental impact statement for a wind farm in regional NSW?"_
- _"What are zoning restrictions for coastal development in Victoria?"_
- _"What are the renewable energy incentives available in Adelaide?"_

### Project

| Folder/File | Purpose                                                |
| ----------- | ------------------------------------------------------ |
| `app/`      | Streamlit UI logic (text + map)                        |
| `rag/`      | LangChain RAG + Agent logic                            |
| `etl/`      | Ingest & process PDF/HTML to chunks + metadata         |
| `configs/`  | Document config YAML, logging setup, vector settings   |
| `data/`     | Source documents, processed text, and GeoJSON overlays |
| `docker/`   | Full containerized setup                               |
| `tests/`    | CI/CD-friendly tests for ingestion, RAG logic, and UI  |
| `scripts/`  | Developer tools for loading data, evaluating responses |

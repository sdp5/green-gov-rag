# GreenGovRAG

#### An AI Assistant for Navigating Australian Environmental & Planning Regulations

GreenGovRAG is an **AI assistant powered by Retrieval-Augmented Generation (RAG)** that answers user questions by retrieving relevant sections from a curated knowledge base of regulations.

## Data Sources

| Document Type       | Where to Get It                                                    |
| ------------------- | ------------------------------------------------------------------ |
| EPBC Act (Federal)  | [environment.gov.au](https://www.environment.gov.au)               |
| SA Gov policies     | [legislation.sa.gov.au](https://www.legislation.sa.gov.au)         |
| Local Council plans | e.g., Adelaide City, Port Adelaide Enfield                         |
| NSW Planning Portal | [planningportal.nsw.gov.au](https://www.planningportal.nsw.gov.au) |
| PDF building codes  | State building authorities (PDF scrapers + PyMuPDF)                |

## Use Cases

### 1. Environmental Impact Assessment (EIA) Pre-screening

```
User: Environmental consultant, planner, or developer
Goal: Determine whether a proposed project needs an EIS/EIA based on location and type.
```
Example Query:

> "Do I need an environmental impact assessment to build a solar farm in regional NSW?"

RAG Output:

- Summarizes relevant sections of the NSW planning portal and EPBC Act
- Cites sources and maps out exemption criteria

### 2. Native Vegetation Clearing Rules by Region

```
User: Local council officer or landowner
Goal: Understand what approvals are needed to clear vegetation in a specific region.
```
Example Query:

> "Can I clear native vegetation on my property near Murray Bridge, SA?"

RAG Output:

- Combines SA Government vegetation clearance policies
- Uses map filter (via LGA/SA2) for local rules
- Returns allowed/disallowed activities and buffer zones

### 3. Zoning Regulations and Permitted Uses

```
User: Urban planner or real estate developer
Goal: Identify permitted land uses for a parcel in a specific zone.
```
Example Query:

> "What are the zoning restrictions for coastal land in Mornington Peninsula, VIC?"

RAG Output:

- Retrieves overlays from council planning schemes
- Explains permitted uses, height limits, environmental constraints

### 4. Emission and Energy Standards Compliance

```
User: Sustainability advisor or industrial developer
Goal: Ensure new facility complies with environmental emission standards.
```
Example Query:

> "Which emissions standards apply to industrial zones in Greater Sydney?"

RAG Output:

- Points to NSW EPA and federal requirements
- Suggests offsets or sustainable alternatives
- Could plug into energy incentive schemes

## Project Structure

| Folder | Purpose                               |
|--------|---------------------------------------|
| `backend/` | Python: FastAPI + RAG + ETL + Airflow |
| `frontend/` | React + TypeScript                    |
| `deploy/` | Docker configs & CI/CD                |
| `data/` | Documents, vectors, GeoJSON           |
| `docs/` | Project Documentation                 |

## Quick Start

**Docker (Recommended):**
```bash
cd deploy/docker && cp .env.example .env
docker-compose up --build
```

**Local:**
```bash
# Backend
cd backend && pip install -e . && uvicorn green_gov_rag.api.main:app --reload

# Frontend (WIP)
cd frontend && npm install && npm run dev
```

**Access:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5173

See [SUMMARY](docs/IMPLEMENTATION_SUMMARY.md) for details.

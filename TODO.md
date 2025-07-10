## TODO

### Week 1 – Build the Core (ETL, RAG, Local Dev)

#### 📅 Day 1 – Project Setup
- [ ] Scaffold folder structure (`app/`, `etl/`, `rag/`, etc.)
- [ ] Create `docker/compose` with:
  - [ ] Streamlit
  - [ ] FastAPI (optional)
  - [ ] PostGIS
  - [ ] Airflow
- [ ] Prepare `configs/documents_config.yml`
- [ ] Add 5–10 environmental PDFs or web links

#### 📅 Day 2 – ETL Pipeline
- [ ] Write `chunker.py` for PDF/HTML splitting
- [ ] Write `loader.py` and `utils.py` for config, cleaning
- [ ] Generate document metadata
- [ ] Save raw & chunked files under `data/`

#### 📅 Day 3 – Vector Store & Embeddings
- [ ] Implement `embeddings.py` (OpenAI or HF)
- [ ] Implement `vector_store.py` (FAISS)
- [ ] Store document chunks + metadata in FAISS
- [ ] Test retrieval locally via script

#### 📅 Day 4 – LangChain RAG Chain
- [ ] Write `rag_chain.py` with:
  - [ ] Prompt template
  - [ ] Metadata filtering
  - [ ] Source linking
- [ ] Add `filters.py` for region/topic filters
- [ ] CLI/Streamlit test: prompt → answer → source

#### 📅 Day 5 – Airflow Integration
- [ ] Set up `docker/airflow/`
- [ ] Write DAGs:
  - [ ] `ingest_dag.py`
  - [ ] `preprocess_dag.py`
- [ ] Trigger DAG from Airflow UI
- [ ] Verify new docs land in FAISS

#### 📅 Day 6 – Streamlit UI
- [ ] Basic text input + response display
- [ ] Create `ui.py`, `config.py`
- [ ] Add `map.py` with:
  - [ ] Folium + GeoJSON LGA overlay
  - [ ] Click to select region

#### 📅 Day 7 – Integration & Testing
- [ ] End-to-end test: PDF → ETL → Embed → Ask
- [ ] Add tests:
  - [ ] `tests/test_etl.py`
  - [ ] `tests/test_rag.py`
- [ ] Commit code, push to GitHub
- [ ] Write initial `README.md`

---

### Week 2 – AWS Infra, Deployment, Polishing

#### 📅 Day 8 – AWS CDK Setup
- [ ] Create `deploy/greengovrag_stack.py`
- [ ] Provision:
  - [ ] VPC
  - [ ] ECS Cluster
  - [ ] S3 Bucket
  - [ ] RDS (PostGIS)
  - [ ] Secrets Manager
- [ ] Use context vars (`cdk.json` or CLI)

#### 📅 Day 9 – Docker & Deployment
- [ ] Build prod Dockerfiles (`docker/prod/`)
  - [ ] `Dockerfile.streamlit`
  - [ ] `Dockerfile.api`
- [ ] ECS Fargate deployment for dual containers
- [ ] Link ECS with Secrets + S3 bucket

#### 📅 Day 10 – Data Access & Logs
- [ ] Connect deployed app to:
  - [ ] S3 documents bucket
  - [ ] PostGIS metadata DB
- [ ] Add CloudWatch logging
- [ ] Secure IAM roles for ECS tasks

#### 📅 Day 11 – Frontend Polish
- [ ] Region dropdown or search on map
- [ ] Topic filters (emissions, EIS, etc.)
- [ ] Add loading spinners, error handling

#### 📅 Day 12 – Airflow Finalization
- [ ] Schedule daily ingestion in DAG
- [ ] Create `airflow.env` for secrets
- [ ] Store processed docs to S3 (optional)

#### 📅 Day 13 – Testing & CI/CD
- [ ] Add GitHub Action (`.github/workflows/ci.yml`)
- [ ] Include lint, test, and deploy steps
- [ ] Run smoke test on deployed app

#### 📅 Day 14 – Demo & Docs
- [ ] Record short walkthrough demo
- [ ] Update `README.md` with architecture diagram
- [ ] Add `LICENSE`, `CONTRIBUTING.md` if open-sourcing
- [ ] Draft blog post or pitch deck

### POTENTIAL EXTENSIONS

| Feature                          | Description                                                                                      |
| -------------------------------- | ------------------------------------------------------------------------------------------------ |
| 🗺️ **Geospatial Query Support** | Integrate **QGIS/PostGIS** and **GeoJSON overlays** to link policies to locations or boundaries. |
| 💬 Slack/MS Teams Bot            | Let council teams ask questions in their workspace (via webhook + backend query).                |
| 🗣️ Voice Interface (Whisper)    | Allow users to ask questions via speech, useful for accessibility and mobile field staff.        |


### Geospatial Query Support – Details

#### 📍 Integration Plan

- Use QGIS to prep regional vector boundaries (e.g. LGA, SA2, suburb boundaries from ABS)
- Store regions in GeoJSON, load using streamlit-folium or folium
- Let user click or select a region on the map, triggering:
  - a filtered retrieval (based on document metadata, postcode, or spatial join)
  - a policy summary using LangChain RAG pipeline
- Optional: Store region-polygon → document/topic mappings in PostGIS or PostgreSQL

#### 🧪 Example Queries

| User Action                                 | Query Sent to LLM                                 | Context Filter Applied                             |
| ------------------------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| Click on *Port Adelaide* LGA                | "What emissions rules apply here?"                | LGA=Port Adelaide                                  |
| Select "Wind farm" + Region: "Mid North SA" | "Do wind farms in Mid North SA need an EIS?"      | SA + topic: Wind farms + EPBC + SA Planning Code   |
| Search "native vegetation" in NSW map       | "What are the native vegetation clearance rules?" | State=NSW + topic=vegetation + metadata: zone type |

### Tools

| Component        | Tools/Libs                                 |
| ---------------- | ------------------------------------------ |
| Map UI           | Streamlit + `streamlit-folium` or `folium` |
| Spatial Metadata | GeoJSON + optional PostGIS                 |
| Document Tagging | Manual or NER-based location/topic tagging |
| Backend          | LangChain + FastAPI + FAISS + OpenAI       |
| Deployment       | ECS / Docker / Streamlit Cloud             |

#### 🗂️ Sample GeoJSON (Australia LGA)
You can get this from:
- ABS Geography Portal
- Or this open dataset: https://data.gov.au/data/dataset/psma-administrative-boundaries

Make sure the GeoJSON includes a field like LGA_NAME or LGA_CODE.

#### 📡 What to Do Next

Once an LGA is selected:

- Filter documents tagged with LGA_NAME = selected
- Pass the user’s natural language query through LangChain
- Optionally display citation and document metadata

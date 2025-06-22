## TODO

| Week       | Milestone                                                                                                                                                                                                                                          |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Week 1** | 🗂️ **Collect 10–20 documents** from federal/state/council sources (e.g. EPBC Act, SA Planning Code PDFs) <br> 🧠 **Set up basic RAG pipeline** using LangChain + FAISS <br> 🚀 **Launch local CLI or Streamlit MVP** for basic question answering |
| **Week 2** | 🏗️ **Add UI with citation view** for retrieved chunks <br> 🔍 **Improve chunking** (recursive vs fixed), enable metadata filtering by doc/state <br> 📌 Start storing document metadata (e.g., region, topic) in FAISS/PostgreSQL                 |
| **Week 3** | 📦 **Containerize and deploy** on ECS, Streamlit Cloud or Render <br> 🧪 **Add 10+ test queries** (e.g. "Do I need an EIS in SA?") <br> 📄 **Create README and short demo video (SpeakerDeck or YouTube)**                                         |
| **Week 4** | ✨ **Polish UI**, add location-based filtering (dropdown + embedded GeoJSON map) <br> 🌐 **Enable geospatial overlay** (Streamlit + QGIS/GeoJSON/Folium) <br> 🔔 **Package for open-source/pitch** with license, issue tracker, roadmap             |


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

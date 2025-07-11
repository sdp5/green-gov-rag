## Document & Data Sources

### Federal Government (Australia-wide)

| Source                                                      | Type                                 | URL                                                                                                                      |
| ----------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| **EPBC Act**                                                | Environmental legislation (PDF/HTML) | [https://www.legislation.gov.au/Series/C2004A00485](https://www.legislation.gov.au/Series/C2004A00485)                   |
| **Environment Protection Australia**                        | Reform updates, new rules            | [https://www.dcceew.gov.au/environment/epbc/epbc-act-reform](https://www.dcceew.gov.au/environment/epbc/epbc-act-reform) |
| **National Construction Code (NCC)**                        | Building standards (PDF)             | [https://ncc.abcb.gov.au/](https://ncc.abcb.gov.au/)                                                                     |
| **Clean Energy Regulator**                                  | Emissions reporting guidelines       | [https://www.cleanenergyregulator.gov.au/](https://www.cleanenergyregulator.gov.au/)                                     |
| **Australian Energy Infrastructure Commissioner**           | Wind/solar project rules             | [https://www.aeic.gov.au/](https://www.aeic.gov.au/)                                                                     |
| **National Native Vegetation Guidelines** (where available) | Guidelines, offsets                  | [https://www.dcceew.gov.au/](https://www.dcceew.gov.au/)                                                                 |


### State Government Sources

#### South Australia (SA)

| Source                              | URL                                                                                                                      |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Planning & Design Code              | [https://code.plan.sa.gov.au/](https://code.plan.sa.gov.au/)                                                             |
| SA Property Location Browser        | [https://location.sa.gov.au/viewer/](https://location.sa.gov.au/viewer/)                                                 |
| SA Environment Protection Authority | [https://www.epa.sa.gov.au/](https://www.epa.sa.gov.au/)                                                                 |
| Native Vegetation Council (SA)      | [https://www.environment.sa.gov.au/topics/native-vegetation](https://www.environment.sa.gov.au/topics/native-vegetation) |

#### New South Wales (NSW)

| Source                      | URL                                                                                                                                                                                  |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| NSW Planning Portal         | [https://www.planningportal.nsw.gov.au/](https://www.planningportal.nsw.gov.au/)                                                                                                     |
| Biodiversity Offsets Scheme | [https://www.environment.nsw.gov.au/topics/animals-and-plants/biodiversity-offsets-scheme](https://www.environment.nsw.gov.au/topics/animals-and-plants/biodiversity-offsets-scheme) |
| EIA Guidance Documents      | [https://www.planning.nsw.gov.au/policy-and-legislation/environmental-impact-assessment](https://www.planning.nsw.gov.au/policy-and-legislation/environmental-impact-assessment)     |

#### Victoria (VIC)

| Source                             | URL                                                                                                    |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Planning Schemes Online            | [https://planning-schemes.app.planning.vic.gov.au/](https://planning-schemes.app.planning.vic.gov.au/) |
| DELWP Environment Docs             | [https://www.environment.vic.gov.au/](https://www.environment.vic.gov.au/)                             |
| Victoria State Planning Provisions | [https://www.planning.vic.gov.au/](https://www.planning.vic.gov.au/)                                   |

#### Queensland (QLD)

| Source                                         | URL                                                                        |
| ---------------------------------------------- | -------------------------------------------------------------------------- |
| State Development Assessment Provisions (SDAP) | [https://planning.dsdmip.qld.gov.au/](https://planning.dsdmip.qld.gov.au/) |
| QLD Environmental Offsets Policy               | [https://environment.des.qld.gov.au/](https://environment.des.qld.gov.au/) |

### Local Council & LGA Policies

| Council                              | Example Resources (Development Plans, DCPs, Codes)  | How to Access                                                                  |
| ------------------------------------ | --------------------------------------------------- | ------------------------------------------------------------------------------ |
| City of Adelaide                     | Planning overlays, land use codes                   | [https://www.cityofadelaide.com.au](https://www.cityofadelaide.com.au)         |
| City of Port Adelaide Enfield (SA)   | Sustainability plans, development controls          | [https://www.cityofpae.sa.gov.au](https://www.cityofpae.sa.gov.au)             |
| Greater Sydney Region (various LGAs) | Development Control Plans (DCPs)                    | [https://www.planningportal.nsw.gov.au](https://www.planningportal.nsw.gov.au) |
| City of Melbourne                    | Environmental sustainability guidelines (ESD tools) | [https://www.melbourne.vic.gov.au](https://www.melbourne.vic.gov.au)           |
| Brisbane City Council                | Local Planning Codes                                | [https://www.brisbane.qld.gov.au](https://www.brisbane.qld.gov.au)             |

📝 Most council sites publish:

- Development Control Plans (DCPs)
- Environmental Impact requirements
- Land zoning overlays (GeoJSON/PDF)
- Strategic planning docs (PDFs)

### Geospatial Data

| Dataset                               | Type                                             | Source URL                                                                                                           |
| ------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| Australian Bureau of Statistics (ABS) | SA2 / LGA shapefiles                             | [https://www.abs.gov.au/statistics/mapping/geo-boundaries](https://www.abs.gov.au/statistics/mapping/geo-boundaries) |
| Data.gov.au                           | Government datasets incl. biodiversity, land use | [https://data.gov.au](https://data.gov.au)                                                                           |
| National Map (Geoscience)             | Map overlays, land zoning, climate data          | [https://nationalmap.gov.au/](https://nationalmap.gov.au/)                                                           |


## Data Sovereignty

| Action                                    | Required for AU Sovereignty Compliance       |
| ----------------------------------------- | -------------------------------------------- |
| Use AU-hosted cloud infra (e.g., AWS SYD) | ✅ Recommended                                |
| Avoid OpenAI API for production use cases | ✅ Unless explicit approval from stakeholders |
| Encrypt + tag regulatory data             | ✅ Especially geospatial + planning metadata  |
| Use sovereign LLM or local inference      | ✅ For councils, federal/state agency use     |

### Where Data Sovereignty Matters in GreenGovRAG

| Layer                       | Data Sovereignty Impact                                                                |
| --------------------------- |----------------------------------------------------------------------------------------|
| 📥 Document Storage         | If storing government policy documents (federal, state, council), best to host in AU   |
| 🧠 LLM Inference            | If using US-hosted APIs (OpenAI, Anthropic), text/query data may leave Australian soil |
| 🗃️ Vector Database (FAISS) | Location of embeddings store — keep in AU if it contains sensitive or unpublished data |
| 🗺️ Geospatial Metadata     | If using PostGIS with property/region coordinates — ensure it stays within jurisdiction |
| 🧑 User Query Logs          | If logging queries for audit/improvement — treat as potentially sensitive or personal  |

### Recommended Practices

1. Use Australian Data Centers
    - Prefer cloud providers with Sydney or Melbourne regions (e.g., AWS, Azure, GCP).
    - For deployment: use AWS ECS/Fargate in ap-southeast-2 (Sydney).

2. Use Sovereign LLMs Where Necessary
    - Avoid sending user queries to non-AU LLMs for production use in government or council settings.
    - Alternatives:
        - AWS Bedrock with Anthropic Claude, hosted in AWS AU region (still not fully sovereign)
        - Deploy HuggingFace models locally (e.g., mistral, phi-2, etc.)
        - Explore Sovereign LLM offerings like Indigai, Mycelium, or RedCloud AI (in dev phase in AU)

3. Data Classification and Access Control
    - Tag documents as public / restricted / internal and manage access accordingly.
    - Use IAM roles, S3 encryption, audit logs if hosted on AWS.

4. Avoid Unintended Leakage
    - If debugging or logging user input: don’t persist raw queries without pseudonymisation or consent.
    - Encrypt metadata DB (e.g., PostgreSQL with TDE or RDS with KMS keys)

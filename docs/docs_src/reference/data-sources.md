# Data Sources

## Federal Sources

| Source | Type | URL |
|--------|------|-----|
| EPBC Act | Legislation | https://www.legislation.gov.au/Series/C2004A00485 |
| Environment Protection Australia | Reform updates | https://www.dcceew.gov.au/environment/epbc/epbc-act-reform |
| National Construction Code | Building standards | https://ncc.abcb.gov.au/ |
| Clean Energy Regulator | Emissions guidelines | https://www.cleanenergyregulator.gov.au/ |
| Energy Infrastructure Commissioner | Wind/solar rules | https://www.aeic.gov.au/ |

## State Sources

### South Australia

| Source | URL |
|--------|-----|
| Planning & Design Code | https://code.plan.sa.gov.au/ |
| Property Location Browser | https://location.sa.gov.au/viewer/ |
| Environment Protection Authority | https://www.epa.sa.gov.au/ |
| Native Vegetation Council | https://www.environment.sa.gov.au/topics/native-vegetation |

### New South Wales

| Source | URL |
|--------|-----|
| Planning Portal | https://www.planningportal.nsw.gov.au/ |
| Biodiversity Offsets Scheme | https://www.environment.nsw.gov.au/topics/animals-and-plants/biodiversity-offsets-scheme |
| EIA Guidance | https://www.planning.nsw.gov.au/policy-and-legislation/environmental-impact-assessment |

### Victoria

| Source | URL |
|--------|-----|
| Planning Schemes Online | https://planning-schemes.app.planning.vic.gov.au/ |
| Environment Resources | https://www.environment.vic.gov.au/ |

### Queensland

| Source | URL |
|--------|-----|
| State Development Assessment | https://planning.dsdmip.qld.gov.au/ |
| Environmental Offsets Policy | https://environment.des.qld.gov.au/ |

## Local Government Sources

| Council | Resources | URL |
|---------|-----------|-----|
| City of Adelaide | Planning overlays, zoning | https://www.cityofadelaide.com.au |
| Port Adelaide Enfield | Sustainability plans, DCPs | https://www.cityofpae.sa.gov.au |
| Greater Sydney LGAs | Development Control Plans | https://www.planningportal.nsw.gov.au |
| City of Melbourne | ESD guidelines | https://www.melbourne.vic.gov.au |
| Brisbane City Council | Local planning codes | https://www.brisbane.qld.gov.au |

## Geospatial Data

| Dataset | Type | Source |
|---------|------|--------|
| ABS Boundaries | LGA/SA2 shapefiles | https://www.abs.gov.au/statistics/mapping/geo-boundaries |
| Data.gov.au | Biodiversity, land use | https://data.gov.au |
| National Map | Zoning, climate overlays | https://nationalmap.gov.au/ |

## Data Sovereignty

### Compliance Requirements

| Action | Required for AU Sovereignty |
|--------|----------------------------|
| Use AU-hosted cloud (AWS SYD, Azure AU) | Required |
| Avoid OpenAI API for production | Recommended |
| Encrypt + tag regulatory data | Required |
| Use sovereign LLM or local inference | Required for gov/council use |

### Data Sovereignty by Layer

| Layer | Impact | Recommendation |
|-------|--------|----------------|
| Document Storage | Gov policy documents | Host in AU regions |
| LLM Inference | Query data may leave AU | Use Bedrock AU or local LLM |
| Vector Database | Embeddings of sensitive data | Keep in AU if unpublished data |
| Geospatial Metadata | Property/region coordinates | Keep within jurisdiction |
| User Query Logs | Potentially sensitive | Treat as personal data |

### Best Practices

**1. Use Australian Data Centers**
- AWS: Sydney region (ap-southeast-2)
- Azure: Australia East/Southeast regions
- Deploy ECS/Fargate or Container Apps in AU

**2. Use Sovereign LLMs**
- AWS Bedrock (Claude in AU region)
- Local HuggingFace models (Mistral, Phi-2)
- AU sovereign options: Indigai, Mycelium, RedCloud AI

**3. Data Classification**
- Tag: public/restricted/internal
- Use IAM, S3 encryption, audit logs
- RDS encryption with KMS keys

**4. Avoid Data Leakage**
- Pseudonymise query logs
- Don't persist raw queries without consent
- Use PostgreSQL TDE or RDS encryption

## Adding Documents

See [Plugin Architecture](../developer-guide/architecture/plugin-system.md) for how to contribute new document sources.

## See Also

- [Cloud Deployment](../developer-guide/cloud-storage.md#migration-guide) - Multi-cloud setup with data sovereignty
- [Plugin Guide](../contributor-guide/document-sources.md) - Add new document sources
- [Metadata Enhancement](../developer-guide/metadata-standards.md) - ESG and spatial metadata

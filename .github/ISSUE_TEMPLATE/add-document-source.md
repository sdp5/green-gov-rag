---
name: Add Document Source
about: Add a new government document to the configuration
title: 'Add [Document Name] to document sources'
labels: 'good first issue, documentation, help wanted'
assignees: ''
---

## 📄 Add Document Source: [Document Name]

**Complexity:** 🟢 Good First Issue
**Estimated Time:** 30-60 minutes
**Skills Required:** YAML, basic understanding of Australian government documents

---

### 📋 What to do

Add the following document to the project's document configuration:

**Document:** [Full document title]
**Source:** [URL to official source]
**Jurisdiction:** [federal / state / local]
**Category:** [legislation / regulation / guideline / policy]
**Topic:** [e.g., emissions_reporting, biodiversity, planning]

### ✅ Acceptance Criteria

- [ ] Document entry added to `configs/documents_config.yml`
- [ ] All required fields populated correctly
- [ ] Download URLs are valid and publicly accessible
- [ ] Configuration validates without errors
- [ ] Document loads successfully via `load_document_sources()`

### 📝 Steps to Complete

#### 1. Add Document Configuration

Edit `configs/documents_config.yml` and add:

```yaml
- title: [Document Title]
  source_url: [Official source URL]
  download_urls:
    - [URL to PDF/HTML document]
  jurisdiction: [federal/state/local]
  category: [category]
  topic: [topic]
  region: [Region name]
  sovereign: true
```

**Tip:** Look at existing entries in the file for examples matching your document type.

#### 2. Determine Required Metadata

Depending on document type, you may need to add:

**For emissions/ESG documents:**
```yaml
  esg_metadata:
    frameworks: [NGER, GHG_Protocol, ISSB]
    emission_scopes: [scope_1, scope_2, scope_3]
    greenhouse_gases: [CO2, CH4, N2O]
    reportable_under_nger: true/false
```

**For state/local documents:**
```yaml
  spatial_metadata:
    spatial_scope: state  # or 'local'
    state: NSW  # or VIC, QLD, SA, WA, TAS, NT, ACT
    lga_codes: []  # for local documents: [40070]
    lga_names: []  # for local documents: ["City of Adelaide"]
    applies_to_all_lgas: true  # false for local documents
```

#### 3. Validate Your Configuration

Run the validation test:

```bash
python -c "
from green_gov_rag.etl.loader import load_document_sources

sources = load_document_sources()
for source in sources:
    if '[Document Name]' in source.config.get('title', ''):
        validation = source.validate()
        print(f'Valid: {validation.is_valid}')
        if not validation.is_valid:
            print(f'Errors: {validation.errors}')
            print(f'Warnings: {validation.warnings}')
        else:
            print(f'Metadata: {source.get_metadata()}')
            print(f'URLs: {source.get_download_urls()}')
"
```

#### 4. Submit Pull Request

Create a PR with:
- **Title:** `Add [Document Name] to document sources`
- **Description:** Brief description of the document and why it's relevant
- **Files changed:** `configs/documents_config.yml`

### 📚 Resources

- **Contributing Guide:** [CONTRIBUTING_DOCUMENT_SOURCES.md](../../docs/CONTRIBUTING_DOCUMENT_SOURCES.md)
- **Example Configs:** Check existing entries in `configs/documents_config.yml`
- **Plugin Types:**
  - Federal legislation → `FederalLegislationSource`
  - Emissions reporting → `EmissionsReportingSource`
  - State legislation → `StateLegislationSource`
  - Local government → `LocalGovernmentSource`

### 🆘 Need Help?

- **YAML syntax:** Check the [example configs](../../configs/documents_config.yml)
- **Metadata fields:** See [CONTRIBUTING_DOCUMENT_SOURCES.md](../../docs/CONTRIBUTING_DOCUMENT_SOURCES.md)
- **Questions:** Comment on this issue!

---

### 🎯 Example: Adding a Federal Legislation Document

```yaml
- title: National Greenhouse and Energy Reporting Act 2007
  source_url: https://www.legislation.gov.au/Series/C2007A00175
  download_urls:
    - https://www.legislation.gov.au/C2007A00175/latest/downloads/C2007A00175.pdf
  jurisdiction: federal
  category: legislation
  topic: emissions_reporting
  region: Australia
  sovereign: true
  esg_metadata:
    frameworks: [NGER]
    emission_scopes: [scope_1, scope_2]
    reportable_under_nger: true
  spatial_metadata:
    spatial_scope: federal
    state: null
    applies_to_all_lgas: true
    applies_to_point: false
```

---

**Ready to contribute?** Follow the steps above and submit your PR! 🚀

# Your First Query

> End-to-end tutorial for submitting your first RAG query

## Prerequisites

- GreenGovRAG running (see [Quick Start](quickstart.md))
- API access key configured
- ETL pipeline has ingested some documents

## Step 1: Verify System is Running

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## Step 2: Submit a Basic Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{
    "query": "What are the emissions reporting thresholds under NGER?"
  }'
```

## Step 3: Understanding the Response

```json
{
  "query": "What are the emissions reporting thresholds under NGER?",
  "answer": "Under the National Greenhouse and Energy Reporting (NGER) Act, facilities must report if they emit 25,000 tonnes CO2-e or more per year...",
  "sources": [
    {
      "title": "NGER Guidelines 2024",
      "page_number": 15,
      "citation": "Department of Climate Change, Energy, the Environment and Water (2024), NGER Technical Guidelines, Section 3.2, Page 15",
      "confidence_score": 0.92,
      "chunk_id": "abc123..."
    }
  ],
  "trust_score": 0.88,
  "response_time_ms": 1234.56,
  "total_sources_found": 5
}
```

## Step 4: Query with Location Filtering

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{
    "query": "Can I clear native vegetation for agriculture?",
    "lga_name": "City of Adelaide",
    "max_sources": 5
  }'
```

This filters results to regulations relevant to the City of Adelaide LGA.

## Step 5: Using the Python API

```python
from green_gov_rag.api.client import GreenGovRAGClient

# Initialize client
client = GreenGovRAGClient(
    base_url="http://localhost:8000",
    api_key="your-secret-key-here"
)

# Submit query
result = client.query(
    query="What are the environmental assessment triggers for solar farms?",
    lga_name="Dubbo Regional",
    max_sources=5
)

# Display results
print(f"Answer: {result.answer}\n")
print(f"Trust Score: {result.trust_score}\n")
print(f"Sources ({len(result.sources)}):")
for i, source in enumerate(result.sources, 1):
    print(f"{i}. {source.citation}")
```

## Advanced Query Options

### Control Response Length

```json
{
  "query": "Explain biodiversity offset requirements",
  "max_tokens": 500
}
```

### Adjust Retrieval Settings

```json
{
  "query": "What is a Matters of National Environmental Significance?",
  "max_sources": 10,
  "min_confidence": 0.7
}
```

### Filter by Document Type

```json
{
  "query": "Vegetation clearing permits",
  "document_types": ["legislation", "guidelines"]
}
```

## Next Steps

- [Explore all query options](../user-guide/querying.md)
- [Learn about trust scores](../developer-guide/citations.md)
- [Configure caching](../user-guide/caching.md) for faster responses

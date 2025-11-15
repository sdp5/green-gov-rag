# Querying the System

> Complete guide to querying GreenGovRAG for regulatory information

## Query Methods

### REST API

The primary method for querying is the REST API `POST /api/query` endpoint.

=== "cURL"
    ```bash
    curl -X POST http://localhost:8000/api/query \
      -H "Content-Type: application/json" \
      -H "X-API-Key: your-secret-key-here" \
      -d '{
        "query": "What are the emissions reporting requirements?",
        "max_sources": 5
      }'
    ```

=== "Python"
    ```python
    import requests

    response = requests.post(
        "http://localhost:8000/api/query",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": "your-secret-key-here"
        },
        json={
            "query": "What are the emissions reporting requirements?",
            "max_sources": 5
        }
    )

    result = response.json()
    print(result["answer"])
    ```

=== "JavaScript"
    ```javascript
    const response = await fetch('http://localhost:8000/api/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-secret-key-here'
      },
      body: JSON.stringify({
        query: 'What are the emissions reporting requirements?',
        max_sources: 5
      })
    });

    const result = await response.json();
    console.log(result.answer);
    ```

### Python Client

GreenGovRAG provides a Python client for easier integration:

```python
from green_gov_rag.api.client import GreenGovRAGClient

client = GreenGovRAGClient(
    base_url="http://localhost:8000",
    api_key="your-secret-key-here"
)

result = client.query(
    query="What permits are needed for vegetation clearing?",
    lga_name="City of Adelaide"
)
```

### CLI

```bash
source backend/.venv/bin/activate
greengovrag-cli rag query \
  --query "What are biodiversity offset requirements?" \
  --lga "Dubbo Regional" \
  --max-sources 5
```

## Query Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Natural language question about regulations |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lga_name` | string | null | Filter results by Local Government Area |
| `state` | string | null | Filter by Australian state (NSW, VIC, SA, etc.) |
| `max_sources` | integer | 5 | Maximum number of source documents to return |
| `min_confidence` | float | 0.0 | Minimum confidence score (0.0-1.0) |
| `document_types` | array | null | Filter by document type (legislation, guidelines, etc.) |
| `max_tokens` | integer | 1000 | Maximum tokens in response |
| `include_metadata` | boolean | true | Include detailed source metadata |

## Geospatial Filtering

### Filter by LGA

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{
    "query": "Native vegetation clearing regulations",
    "lga_name": "City of Adelaide"
  }'
```

### Filter by State

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key-here" \
  -d '{
    "query": "Environmental assessment triggers",
    "state": "NSW"
  }'
```

## Advanced Querying

### Multi-criteria Filtering

```json
{
  "query": "What are the water quality monitoring requirements?",
  "lga_name": "Hunter Valley",
  "document_types": ["legislation", "guidelines"],
  "min_confidence": 0.7,
  "max_sources": 10
}
```

### Controlling Response Detail

```json
{
  "query": "Explain the EPBC Act referral process",
  "max_tokens": 2000,
  "include_metadata": true
}
```

## Understanding Responses

### Response Structure

```json
{
  "query": "Original query text",
  "answer": "Generated answer with citations",
  "sources": [
    {
      "title": "Document title",
      "page_number": 42,
      "section": "3.2.1",
      "citation": "Full legal citation",
      "confidence_score": 0.92,
      "chunk_id": "unique-id",
      "document_type": "legislation",
      "jurisdiction": "Federal",
      "last_updated": "2024-01-15"
    }
  ],
  "trust_score": 0.88,
  "response_time_ms": 1234.56,
  "total_sources_found": 15,
  "cache_hit": false
}
```

### Trust Scores

The `trust_score` (0.0-1.0) indicates confidence in the answer:

- **0.8-1.0**: High confidence, multiple corroborating sources
- **0.6-0.8**: Medium confidence, some supporting evidence
- **0.4-0.6**: Low confidence, limited sources
- **< 0.4**: Very low confidence, answer may be unreliable

### Source Confidence

Each source has a `confidence_score` indicating relevance:

- **0.9-1.0**: Highly relevant, direct match
- **0.7-0.9**: Relevant, good semantic match
- **0.5-0.7**: Somewhat relevant, partial match
- **< 0.5**: Low relevance, may be tangential

## Best Practices

### Writing Effective Queries

****Good queries**:
- "What are the emissions reporting thresholds under NGER?"
- "Do I need an EIA for a solar farm in regional NSW?"
- "What are the biodiversity offset requirements in South Australia?"

****Poor queries**:
- "emissions" (too vague)
- "Tell me everything about environmental law" (too broad)
- "Is coal bad?" (subjective, not regulatory)

### Query Optimization Tips

1. **Be specific**: Include jurisdiction, regulation name, or activity type
2. **Use terminology**: Regulatory terms like "EPBC", "NGER", "EIA" improve results
3. **Include location**: LGA or state filtering improves relevance
4. **Set appropriate max_sources**: More sources = higher confidence but slower
5. **Check trust scores**: Low scores indicate uncertain answers

## Rate Limiting

The API enforces rate limits to ensure fair usage:

- **Default**: 30 requests per minute
- **Production**: 100 requests per minute (configurable)

Rate limit headers in response:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1609459200
```

## Error Handling

### Common Errors

**401 Unauthorized**
```json
{
  "detail": "Missing or invalid API key"
}
```
Solution: Include valid `X-API-Key` header

**422 Validation Error**
```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
Solution: Check required parameters

**429 Too Many Requests**
```json
{
  "detail": "Rate limit exceeded"
}
```
Solution: Wait before retrying, implement exponential backoff

**503 Service Unavailable**
```json
{
  "detail": "Vector store unavailable"
}
```
Solution: Check service health, retry after delay

## Performance Optimization

### Enable Caching

Cached queries return results in <100ms:

```bash
# In .env
ENABLE_CACHE=true
CACHE_TTL=3600
```

See [Caching Guide](caching.md) for details.

### Batch Queries

For multiple queries, use batch processing:

```python
queries = [
    "What are NGER thresholds?",
    "What is a referral trigger?",
    "Explain biodiversity offsets"
]

results = []
for query in queries:
    result = client.query(query=query)
    results.append(result)
```

## See Also

- [First Query Tutorial](../getting-started/first-query.md)
- [API Reference](../api-reference/rest-api.md)
- [Caching Guide](caching.md)
- [Troubleshooting](troubleshooting.md)

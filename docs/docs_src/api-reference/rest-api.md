# REST API Reference

> Interactive API documentation

## Interactive Explorer

The API provides interactive documentation via Swagger UI and ReDoc:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Authentication

All endpoints (except `/api/health`) require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/api/...
```

## Public Endpoints

### Query

**POST** `/api/query`

Submit a natural language query about Australian environmental regulations.

**Request**:
```json
{
  "query": "What are the emissions reporting thresholds under NGER?",
  "lga_name": "City of Adelaide",
  "state": "SA",
  "max_sources": 5,
  "min_confidence": 0.7,
  "document_types": ["legislation", "guidelines"],
  "max_tokens": 1000,
  "include_metadata": true
}
```

**Response**:
```json
{
  "query": "What are the emissions reporting thresholds under NGER?",
  "answer": "Under the NGER Act, facilities must report if...",
  "sources": [
    {
      "title": "NGER Guidelines 2024",
      "page_number": 15,
      "section": "3.2.1",
      "citation": "DCCEEW (2024), NGER Technical Guidelines, Page 15",
      "confidence_score": 0.92,
      "chunk_id": "abc123",
      "document_type": "guidelines",
      "jurisdiction": "Federal"
    }
  ],
  "trust_score": 0.88,
  "response_time_ms": 1234.56,
  "total_sources_found": 15,
  "cache_hit": false
}
```

### List Documents

**GET** `/api/documents`

List all available regulatory documents.

**Query Parameters**:

- `jurisdiction` (optional): Filter by jurisdiction (Federal, NSW, VIC, etc.)
- `document_type` (optional): Filter by type (legislation, guidelines, etc.)
- `skip` (optional): Pagination offset
- `limit` (optional): Results per page (default: 100)

**Response**:
```json
{
  "documents": [
    {
      "id": "epbc-act-2024",
      "title": "EPBC Act 1999",
      "jurisdiction": "Federal",
      "document_type": "legislation",
      "last_updated": "2024-01-15",
      "chunk_count": 1523
    }
  ],
  "total": 42,
  "skip": 0,
  "limit": 100
}
```

### Analytics

**GET** `/api/analytics`

Get usage statistics and analytics.

**Response**:
```json
{
  "total_queries": 1523,
  "avg_response_time_ms": 1234.56,
  "cache_hit_rate": 0.65,
  "top_queries": [
    {"query": "emissions reporting", "count": 45}
  ],
  "queries_by_lga": {
    "City of Adelaide": 120
  },
  "avg_trust_score": 0.82
}
```

### Health Check

**GET** `/api/health`

Check system health (no authentication required).

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## Admin Endpoints

All admin endpoints require admin-level API key.

### System Health

**GET** `/api/admin/system/health`

Detailed system health metrics.

### Cache Management

**GET** `/api/admin/cache/metrics` - Cache performance metrics

**POST** `/api/admin/cache/clear` - Clear cache

**DELETE** `/api/admin/cache/{key}` - Delete specific cache entry

### Document Management

**POST** `/api/admin/documents/reprocess` - Reprocess all documents

**DELETE** `/api/admin/documents/{document_id}` - Delete document

## Rate Limiting

Default rate limits:

- **Public endpoints**: 30 requests/minute
- **Admin endpoints**: 100 requests/minute

Rate limit headers:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 27
X-RateLimit-Reset: 1609459200
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid query parameter"
}
```

### 401 Unauthorized
```json
{
  "detail": "Missing or invalid API key"
}
```

### 422 Validation Error
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

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error",
  "error_id": "abc-123-def"
}
```

## OpenAPI Specification

Download the full OpenAPI specification:

```bash
curl http://localhost:8000/openapi.json > api-schema.json
```

## See Also

- [Querying Guide](../user-guide/querying.md) - Detailed query examples
- [Authentication](../getting-started/configuration.md#authentication) - API key setup
- [Rate Limiting](../getting-started/configuration.md#api-configuration) - Configure limits

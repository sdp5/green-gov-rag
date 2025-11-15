# Monitoring

> Monitoring GreenGovRAG system health and performance

## Health Checks

### API Health Endpoint

```bash
curl http://localhost:8000/api/health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "checks": {
    "database": "healthy",
    "vector_store": "healthy",
    "llm_provider": "healthy"
  }
}
```

### Detailed System Health (Admin)

```bash
curl http://localhost:8000/api/admin/system/health \
  -H "X-API-Key: your-admin-key"
```

Response:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "database": {
    "status": "healthy",
    "connection_pool": {
      "active": 5,
      "idle": 10,
      "max": 20
    },
    "total_documents": 1250,
    "total_chunks": 45000
  },
  "vector_store": {
    "status": "healthy",
    "type": "qdrant",
    "collection_size": 45000,
    "index_status": "ready"
  },
  "llm": {
    "status": "healthy",
    "provider": "azure",
    "model": "gpt-4o",
    "rate_limit_remaining": 95
  },
  "cache": {
    "status": "healthy",
    "hit_rate": 0.65,
    "total_keys": 1234
  }
}
```

## Metrics

### Query Analytics

```bash
curl http://localhost:8000/api/analytics \
  -H "X-API-Key: your-api-key"
```

Response:
```json
{
  "total_queries": 1523,
  "avg_response_time_ms": 1234.56,
  "cache_hit_rate": 0.65,
  "top_queries": [
    {"query": "emissions reporting", "count": 45},
    {"query": "biodiversity offsets", "count": 32}
  ],
  "queries_by_lga": {
    "City of Adelaide": 120,
    "Dubbo Regional": 85
  },
  "avg_trust_score": 0.82
}
```

### Cache Metrics (Admin)

```bash
curl http://localhost:8000/api/admin/cache/metrics \
  -H "X-API-Key: your-admin-key"
```

Response:
```json
{
  "total_keys": 1234,
  "hit_rate": 0.65,
  "miss_rate": 0.35,
  "avg_response_time_cached_ms": 45.2,
  "avg_response_time_uncached_ms": 1250.5,
  "cache_size_mb": 125.4,
  "evictions": 42
}
```

## Logging

### Log Levels

Configure in `.env`:
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Log Format

```
2024-01-15 10:30:45 INFO [green_gov_rag.api.routes.query] Query received: query="emissions reporting" lga=None
2024-01-15 10:30:45 INFO [green_gov_rag.rag.vector_store] Vector search: found 5 results, top_score=0.92
2024-01-15 10:30:46 INFO [green_gov_rag.rag.enhanced_response] LLM response generated: tokens=234, time_ms=1200
```

### Docker Logs

```bash
# View backend logs
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# Filter for errors
docker-compose logs backend | grep ERROR
```

### Production Logging

For production deployments, logs are sent to:

**AWS**: CloudWatch Logs
```bash
aws logs tail /ecs/greengovrag-backend --follow
```

**Azure**: Application Insights
```bash
az monitor app-insights query \
  --app greengovrag-insights \
  --analytics-query "traces | where timestamp > ago(1h)"
```

## Performance Monitoring

### Response Time Tracking

Response times are logged for all queries:

- **Cached queries**: <100ms
- **Vector search**: 200-500ms
- **LLM generation**: 1000-3000ms
- **Total**: 1200-3500ms

### Slow Query Log

Queries taking >5s are logged at WARNING level:

```
2024-01-15 10:30:45 WARNING [green_gov_rag.api.routes.query] Slow query detected: time_ms=5234, query="complex multi-part question"
```

## Alerting

### Health Check Monitoring

Set up external monitoring with services like:

- **UptimeRobot**: Ping `/api/health` every 5 minutes
- **Pingdom**: Monitor API availability
- **DataDog**: Full observability stack

### Example: UptimeRobot Configuration

- **URL**: `https://your-domain.com/api/health`
- **Interval**: 5 minutes
- **Expected response**: `status: "healthy"`
- **Alert on**: HTTP error or unhealthy status

### Custom Alerts

For production, configure alerts on:

- Response time > 5s (sustained)
- Error rate > 5%
- Cache hit rate < 50%
- Vector store connection failures
- LLM API rate limit approaching

## Dashboards

### Admin Dashboard

Access at: `/admin/dashboard` (future feature)

Displays:
- Query volume over time
- Response time distribution
- Trust score distribution
- Document coverage by LGA
- Cache performance
- Error rates

### Grafana (Production)

For production deployments, use Grafana dashboards:

- **System metrics**: CPU, memory, disk
- **Application metrics**: Query rate, latency, errors
- **Business metrics**: Trust scores, document usage

## Resource Usage

### Database Connection Pool

Monitor active connections:

```sql
SELECT
    count(*) AS total,
    state,
    query
FROM pg_stat_activity
WHERE datname = 'greengovrag'
GROUP BY state, query;
```

### Vector Store Size

```bash
# Qdrant collection size
curl http://localhost:6333/collections/greengovrag

# FAISS index size
du -sh data/vectors/faiss_index
```

### Disk Space

```bash
# Check available space
df -h

# Database size
du -sh /var/lib/postgresql/data

# Vector index size
du -sh data/vectors/
```

## Troubleshooting Common Issues

### High Memory Usage

Check vector store configuration:
```bash
# Reduce batch size
CHUNK_BATCH_SIZE=50  # Down from 100
```

### Slow Queries

Enable query caching:
```bash
ENABLE_CACHE=true
CACHE_TTL=3600
```

### Database Connection Errors

Increase connection pool:
```python
# In config.py
DATABASE_POOL_SIZE=20  # Up from 10
```

## See Also

- [Deployment: Monitoring](../deployment/monitoring.md) - Production monitoring setup
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Admin API Reference](../api-reference/rest-api.md#admin-endpoints)

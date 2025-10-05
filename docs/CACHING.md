# LLM Response Caching

## Overview

The GreenGovRAG application includes a comprehensive caching layer for LLM responses to reduce costs and improve response times.

## Features

- **Multi-level caching**: In-memory (fast) + Redis (distributed)
- **Automatic cache invalidation**: When documents are updated or deleted
- **Cache metrics**: Monitor hit rates and cost savings
- **Configurable TTL**: Set how long responses are cached
- **Admin controls**: View metrics and clear cache via API

## Configuration

Add these settings to your `.env` file:

```bash
# Enable/disable caching
ENABLE_CACHE=true

# Enable Redis for distributed caching (requires Redis server)
ENABLE_REDIS_CACHE=false

# Redis connection
REDIS_HOST=localhost
REDIS_PORT=6379

# Cache time-to-live in seconds (default: 1 hour)
CACHE_TTL=3600

# Experimental: semantic similarity caching
ENABLE_SEMANTIC_CACHE=false
```

## How It Works

### 1. Query Processing

When a user submits a query:

1. **Retrieve documents** from vector store (based on query + filters)
2. **Check cache** using hash of (query + context + filters)
3. **If cached**: Return cached response immediately (50ms)
4. **If not cached**:
   - Call LLM to generate answer (~2 seconds)
   - Store response in cache
   - Return answer to user

### 2. Cache Key Generation

Cache keys are MD5 hashes of:
- User query text
- Retrieved context (documents)
- Applied filters (region, jurisdiction, topics)

This ensures:
- Same query + same context = cache hit
- Different filters = different cache entry
- Different retrieved documents = different cache entry

### 3. Cache Invalidation

Cache entries are automatically invalidated when:

- **Document reprocessed**: All queries using that document
- **Document deleted**: All queries using that document
- **Admin clears cache**: All entries removed
- **TTL expires**: Entries older than `CACHE_TTL` seconds

## Cost Savings

### Example Calculation

**Scenario**: 1000 queries/day, 70% cache hit rate

```
Without caching:
- 1000 queries × $0.02/query = $20/day
- Annual cost: $7,300

With 70% cache hit rate:
- 300 API calls × $0.02 = $6/day
- 700 cached responses × $0.00 = $0/day
- Annual cost: $2,190
- **Savings: $5,110/year (70%)**
```

### Real-World Impact

| Daily Queries | Hit Rate | Monthly Cost (No Cache) | Monthly Cost (With Cache) | Monthly Savings |
|--------------|----------|------------------------|--------------------------|-----------------|
| 100          | 60%      | $60                    | $24                      | $36             |
| 500          | 70%      | $300                   | $90                      | $210            |
| 1,000        | 75%      | $600                   | $150                     | $450            |
| 5,000        | 80%      | $3,000                 | $600                     | $2,400          |

## API Endpoints

### View Cache Metrics

```bash
GET /api/admin/cache/metrics
```

Response:
```json
{
  "total_requests": 1000,
  "cache_hits": 750,
  "cache_misses": 250,
  "hit_rate_percent": 75.0,
  "memory_cache_size": 100,
  "estimated_cost_savings_usd": 15.0,
  "redis_enabled": false
}
```

### Clear Cache

```bash
POST /api/admin/cache/clear
```

Response:
```json
{
  "status": "success",
  "message": "Cache cleared"
}
```

## Using Redis (Optional)

### Why Redis?

- **Distributed caching**: Share cache across multiple API instances
- **Persistence**: Cache survives application restarts
- **Scalability**: Handle millions of entries
- **Better performance**: Faster than database lookups

### Setup

1. **Install Redis**:
   ```bash
   # macOS
   brew install redis
   brew services start redis

   # Ubuntu/Debian
   sudo apt-get install redis-server
   sudo systemctl start redis

   # Docker
   docker run -d -p 6379:6379 redis:latest
   ```

2. **Enable in config**:
   ```bash
   ENABLE_REDIS_CACHE=true
   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

3. **Verify connection**:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

## Memory vs Redis Caching

| Feature | In-Memory | Redis |
|---------|-----------|-------|
| Speed | Very Fast (µs) | Fast (ms) |
| Capacity | Limited (~1000 entries) | Large (millions) |
| Persistence | Lost on restart | Persisted |
| Distributed | No | Yes |
| Best for | Single server | Multi-server |

## Best Practices

### 1. Set Appropriate TTL

```bash
# Regulations change infrequently
CACHE_TTL=3600  # 1 hour (good default)

# Highly dynamic content
CACHE_TTL=300   # 5 minutes

# Static reference data
CACHE_TTL=86400 # 24 hours
```

### 2. Monitor Cache Performance

Check metrics regularly:
- **Target hit rate**: >60% for cost savings
- **Monitor cache size**: Ensure not exceeding memory
- **Track cost savings**: Validate ROI

### 3. Clear Cache Strategically

Clear cache when:
- Bulk document updates
- System configuration changes
- Debugging incorrect responses

**Don't clear** for:
- Single document updates (auto-invalidation handles this)
- Regular operations

### 4. Production Deployment

For production, enable Redis:

```bash
# Production .env
ENABLE_CACHE=true
ENABLE_REDIS_CACHE=true
REDIS_HOST=redis.production.internal
REDIS_PORT=6379
CACHE_TTL=3600
```

## Troubleshooting

### Cache Not Working

1. **Check if enabled**:
   ```bash
   curl http://localhost:8000/api/admin/cache/metrics
   ```

2. **View logs**:
   ```bash
   # Look for cache initialization
   grep "Cache enabled" logs/app.log
   ```

3. **Verify Redis connection**:
   ```bash
   redis-cli ping
   ```

### Low Hit Rate

Possible causes:
- Highly varied queries (expected)
- Short TTL (increase `CACHE_TTL`)
- Frequent document updates (expected)
- Different filters per query (expected)

### Redis Connection Errors

```python
# Error: "Redis connection failed"
# Solution: Falls back to memory cache automatically
# Check Redis is running: redis-cli ping
```

## Performance Metrics

### Response Times

| Scenario | Time | Notes |
|----------|------|-------|
| Cache Hit (Memory) | 10-50ms | Instant response |
| Cache Hit (Redis) | 50-100ms | Network overhead |
| Cache Miss | 1,500-3,000ms | LLM generation |

### Cost Per Query

| Provider | Model | Cost/Query | Cached Cost |
|----------|-------|------------|-------------|
| OpenAI | GPT-4 | $0.03 | $0.00 |
| OpenAI | GPT-3.5 | $0.002 | $0.00 |
| Anthropic | Claude | $0.024 | $0.00 |

## Future Enhancements

### Semantic Caching (Experimental)

Match similar queries even if worded differently:

```bash
ENABLE_SEMANTIC_CACHE=true
```

Example:
- Query 1: "What are NSW emissions limits?"
- Query 2: "What are the emissions limits in NSW?"
- Result: Query 2 uses cached response from Query 1

### Proactive Cache Warming

Pre-populate cache with common queries:

```python
# Run on startup or schedule
POST /api/admin/cache/warm
{
  "queries": [
    "What are emissions limits in NSW?",
    "What are biodiversity requirements in VIC?"
  ]
}
```

## Summary

Caching provides:
- **60-90% cost reduction** on LLM API calls
- **10-50x faster** response times for cached queries
- **Automatic invalidation** when documents change
- **Easy monitoring** via admin endpoints
- **Zero configuration** for basic use (memory cache)
- **Redis support** for production scalability

Enable it in your `.env`:
```bash
ENABLE_CACHE=true
```

That's it! Start saving money immediately.

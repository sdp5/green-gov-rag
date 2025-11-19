# Troubleshooting

> Solutions to common issues

## Authentication Issues

### 403 Forbidden - Missing API Key

**Symptoms**:
```json
{
  "detail": "Forbidden"
}
```

**Cause**: Missing or invalid `X-API-Key` header

**Solution**:
```bash
# Ensure API key header is included
curl -H "X-API-Key: your-secret-key-here" ...

# Verify API_ACCESS_KEY is set in .env
grep API_ACCESS_KEY backend/.env
```

### 401 Unauthorized

**Symptoms**:
```json
{
  "detail": "Invalid API key"
}
```

**Cause**: API key doesn't match server configuration

**Solution**:
1. Check `API_ACCESS_KEY` in backend/.env
2. Regenerate key if compromised:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

## Database Issues

### Connection Refused

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server
```

**Cause**: PostgreSQL not running or incorrect connection string

**Solution**:
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Verify DATABASE_URL in .env
grep DATABASE_URL backend/.env

# Restart PostgreSQL
docker-compose restart postgres
```

### pgvector Extension Not Found

**Symptoms**:
```
ERROR: extension "vector" does not exist
```

**Cause**: pgvector extension not installed

**Solution**:
```bash
# For Docker Compose
docker-compose down -v
docker-compose up  # Will run init-pgvector.sql

# For local PostgreSQL
psql -d greengovrag -c "CREATE EXTENSION vector;"
```

### Migration Errors

**Symptoms**:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Cause**: Database schema out of sync

**Solution**:
```bash
cd backend

# Check current revision
alembic current

# Upgrade to latest
alembic upgrade head

# If still failing, reset database (WARNING: data loss)
alembic downgrade base
alembic upgrade head
```

## Vector Store Issues

### Qdrant Connection Timeout

**Symptoms**:
```
httpx.ConnectTimeout: timed out
```

**Cause**: Qdrant not running or wrong URL

**Solution**:
```bash
# Check Qdrant is running
curl http://localhost:6333/health

# Verify QDRANT_URL in .env
grep QDRANT_URL backend/.env

# Restart Qdrant
docker-compose restart qdrant
```

### Collection Not Found

**Symptoms**:
```
qdrant_client.exceptions.UnexpectedResponse: Collection 'greengovrag' not found
```

**Cause**: Collection hasn't been created

**Solution**:
```bash
# Run ETL pipeline to create collection
docker-compose up etl

# Or manually create via API
curl -X PUT http://localhost:6333/collections/greengovrag \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 384,
      "distance": "Cosine"
    }
  }'
```

### FAISS Index Missing

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'data/vectors/faiss_index'
```

**Cause**: FAISS index not yet created

**Solution**:
```bash
# Create data directory
mkdir -p data/vectors

# Run ETL to build index
greengovrag-cli etl run-pipeline --config configs/documents_config.yml
```

## LLM Provider Issues

### OpenAI Rate Limit

**Symptoms**:
```
openai.error.RateLimitError: Rate limit reached
```

**Cause**: Exceeded OpenAI rate limits

**Solution**:

1. Wait and retry with exponential backoff
2. Upgrade OpenAI plan for higher limits
3. Switch to Azure OpenAI (higher limits):
   ```bash
   LLM_PROVIDER=azure
   ```

### Invalid API Key

**Symptoms**:
```
openai.error.AuthenticationError: Incorrect API key provided
```

**Cause**: Invalid or expired LLM API key

**Solution**:
```bash
# Verify key is set
grep OPENAI_API_KEY backend/.env

# Test key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# For Azure, check endpoint and key
grep AZURE_OPENAI backend/.env
```

### Model Not Found

**Symptoms**:
```
openai.error.InvalidRequestError: The model 'gpt-5' does not exist
```

**Cause**: Model name doesn't exist or isn't available

**Solution**:
```bash
# For Azure, use deployment name (not model name)
LLM_MODEL=your-deployment-name  # e.g., "gpt-4o"

# For OpenAI, use valid model name
LLM_MODEL=gpt-4o  # or gpt-4o-mini
```

## ETL Issues

### Document Download Failed

**Symptoms**:
```
requests.exceptions.HTTPError: 404 Client Error
```

**Cause**: Source URL is broken or moved

**Solution**:

1. Check document source URL in `configs/documents_config.yml`
2. Manually verify URL in browser
3. Update config with new URL
4. Disable source if permanently unavailable:
   ```yaml
   - type: federal_epbc
     enabled: false  # Temporarily disable
   ```

### PDF Parsing Errors

**Symptoms**:
```
unstructured.errors.PartitionError: Failed to parse PDF
```

**Cause**: Corrupted PDF or unsupported format

**Solution**:
```bash
# Check PDF is valid
file document.pdf

# Try different parser strategy
UNSTRUCTURED_STRATEGY=fast  # Options: hi_res, fast, auto

# Skip problematic document
# Edit configs/documents_config.yml to exclude
```

### Out of Memory During Indexing

**Symptoms**:
```
MemoryError: Unable to allocate array
```

**Cause**: Too many chunks being processed at once

**Solution**:
```bash
# Reduce batch size in .env
CHUNK_BATCH_SIZE=50  # Down from 100

# Increase Docker memory limit
# docker-compose.yml: mem_limit: 4g
```

## Performance Issues

### Slow Query Response

**Symptoms**: Queries taking >5 seconds

**Possible causes and solutions**:

1. **Cache disabled**:
   ```bash
   ENABLE_CACHE=true
   CACHE_TTL=3600
   ```

2. **Too many sources requested**:
   ```json
   {"max_sources": 3}  // Instead of 10
   ```

3. **Vector store not optimized**:
   - Switch from FAISS to Qdrant for production
   - Enable HNSW index in Qdrant

4. **LLM response slow**:
   - Use faster model: `gpt-4o-mini` instead of `gpt-4o`
   - Reduce `max_tokens` in query

### High Memory Usage

**Symptoms**: Container OOM killed

**Solution**:
```bash
# Increase Docker memory
docker-compose.yml:
  services:
    backend:
      mem_limit: 4g  # Up from 2g

# Reduce vector store memory usage
VECTOR_STORE_TYPE=qdrant  # Qdrant uses less memory than FAISS
```

## Docker Issues

### Port Already in Use

**Symptoms**:
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solution**:
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Use port 8001 instead
```

### Container Won't Start

**Symptoms**: Container exits immediately after starting

**Solution**:
```bash
# Check logs
docker-compose logs backend

# Common causes:
# 1. Missing environment variables
#    Solution: Verify .env file exists and is complete

# 2. Database migration needed
#    Solution: Run migrations manually
docker-compose exec backend alembic upgrade head

# 3. Dependency conflict
#    Solution: Rebuild images
docker-compose build --no-cache
```

## Network Issues

### Cannot Reach API from Host

**Symptoms**: Connection refused when calling API

**Solution**:
```bash
# Check API is running
docker-compose ps

# Check API is listening
docker-compose exec backend netstat -tlnp | grep 8000

# Test from inside container
docker-compose exec backend curl http://localhost:8000/api/health

# If working inside, check port mapping
docker-compose ps  # Should show 0.0.0.0:8000->8000/tcp
```

## Getting Help

If you're still stuck:

1. **Check logs**: `docker-compose logs -f backend`
2. **Enable debug logging**: `LOG_LEVEL=DEBUG` in `.env`
3. **Search issues**: [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
4. **Create issue**: Include logs, .env (redacted), and error messages

## See Also

- [Monitoring Guide](monitoring.md) - System health monitoring
- [Configuration Guide](../getting-started/configuration.md) - Environment variables
- [Deployment Guide](../deployment/overview.md) - Production deployment

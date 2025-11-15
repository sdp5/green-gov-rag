# Monitoring Guide

> Comprehensive monitoring setup for GreenGovRAG in production

## Overview

Effective monitoring is critical for production RAG systems. This guide covers:
- Health checks and uptime monitoring
- Logging configuration
- Performance metrics
- Alerting strategies
- Debugging tools

## Health Checks

### API Health Endpoint

**Endpoint**: `GET /api/health`

**Response** (healthy):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T12:34:56Z",
  "components": {
    "database": "healthy",
    "vector_store": "healthy",
    "llm_provider": "healthy",
    "cache": "healthy"
  },
  "version": "1.0.0",
  "uptime_seconds": 86400
}
```

**Response** (unhealthy):
```json
{
  "status": "unhealthy",
  "timestamp": "2025-11-15T12:34:56Z",
  "components": {
    "database": "healthy",
    "vector_store": "unhealthy",
    "llm_provider": "healthy",
    "cache": "healthy"
  },
  "errors": ["Qdrant connection timeout"]
}
```

### Health Check Implementation

**File**: `backend/green_gov_rag/api/routes/health.py`

```python
from fastapi import APIRouter, status
from green_gov_rag.api.services.health_service import HealthService

router = APIRouter()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Comprehensive health check."""
    health_service = HealthService()
    result = await health_service.check_all()

    if result["status"] == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=result
        )

    return result
```

### Uptime Monitoring

**External Monitoring Services**:
- **Pingdom**: https://www.pingdom.com (paid)
- **UptimeRobot**: https://uptimerobot.com (free tier available)
- **AWS CloudWatch Synthetics**: Canary monitoring
- **Azure Application Insights Availability Tests**: URL ping tests

**Setup (UptimeRobot example)**:
1. Create monitor: HTTP(S)
2. URL: `https://your-api.com/api/health`
3. Interval: 5 minutes
4. Alert contacts: email, Slack

## Logging

### Log Levels

```python
# In .env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**Development**: `DEBUG` (verbose)
**Production**: `INFO` (default) or `WARNING` (minimal)

### Structured Logging

**Format**: JSON for machine parsing

```json
{
  "timestamp": "2025-11-15T12:34:56.789Z",
  "level": "INFO",
  "logger": "green_gov_rag.api.routes.query",
  "message": "RAG query processed",
  "query": "What are NGER requirements?",
  "response_time_ms": 1234.56,
  "sources_count": 5,
  "trust_score": 0.85,
  "user_id": "anonymous",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### AWS CloudWatch Logs

**View logs**:
```bash
# Tail logs
aws logs tail /ecs/greengovrag-backend --follow

# Last 100 lines
aws logs tail /ecs/greengovrag-backend --since 1h

# Filter for errors
aws logs filter-pattern /ecs/greengovrag-backend --pattern "ERROR"

# Search for specific query
aws logs filter-pattern /ecs/greengovrag-backend --pattern "RAG query processed"
```

**Query logs with Insights**:
```bash
# Top 10 slowest queries
fields @timestamp, query, response_time_ms
| filter level = "INFO" and message = "RAG query processed"
| sort response_time_ms desc
| limit 10

# Error rate by hour
fields @timestamp, level
| filter level = "ERROR"
| stats count() by bin(1h)

# Average trust score
fields trust_score
| filter level = "INFO" and message = "RAG query processed"
| stats avg(trust_score) as avg_trust_score
```

### Azure Log Analytics

**Query logs**:
```kusto
// Last 100 errors
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "greengovrag-backend"
| where Level_s == "ERROR"
| order by TimeGenerated desc
| take 100

// Slow queries (> 2s)
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "greengovrag-backend"
| where Message_s contains "RAG query processed"
| extend response_time = todouble(extract("response_time_ms\":(\\d+\\.\\d+)", 1, Message_s))
| where response_time > 2000
| order by response_time desc

// Error rate over time
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "greengovrag-backend"
| where Level_s == "ERROR"
| summarize count() by bin(TimeGenerated, 1h)
| render timechart
```

### Local Docker Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend

# Filter for errors
docker-compose logs backend | grep ERROR

# Follow with timestamp
docker-compose logs -f -t backend
```

## Metrics

### Key Performance Indicators (KPIs)

| Metric | Target | Critical Threshold |
|--------|--------|--------------------|
| **API Response Time (p95)** | < 2s | > 5s |
| **Vector Search Latency** | < 100ms | > 500ms |
| **Database Query Time** | < 50ms | > 200ms |
| **Cache Hit Rate** | > 50% | < 20% |
| **Error Rate** | < 0.1% | > 1% |
| **Uptime** | > 99.9% | < 99% |
| **Trust Score (avg)** | > 0.7 | < 0.5 |

### AWS CloudWatch Metrics

**View metrics**:
```bash
# ECS CPU utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=greengovrag-service \
  --start-time 2025-11-15T00:00:00Z \
  --end-time 2025-11-15T23:59:59Z \
  --period 3600 \
  --statistics Average

# API Gateway 5XX errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --start-time 2025-11-15T00:00:00Z \
  --end-time 2025-11-15T23:59:59Z \
  --period 300 \
  --statistics Sum
```

**Custom Metrics**:
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Publish custom metric
cloudwatch.put_metric_data(
    Namespace='GreenGovRAG',
    MetricData=[
        {
            'MetricName': 'QueryTrustScore',
            'Value': 0.85,
            'Unit': 'None',
            'Timestamp': datetime.utcnow()
        }
    ]
)
```

### Azure Monitor Metrics

**View in Azure Portal**: Monitor → Metrics → Select resource

**Query with CLI**:
```bash
# CPU percentage
az monitor metrics list \
  --resource greengovrag-backend \
  --resource-group greengovrag-rg \
  --resource-type Microsoft.App/containerApps \
  --metric "CpuPercentage" \
  --start-time 2025-11-15T00:00:00Z \
  --end-time 2025-11-15T23:59:59Z \
  --interval PT1H

# HTTP request count
az monitor metrics list \
  --resource greengovrag-backend \
  --resource-group greengovrag-rg \
  --resource-type Microsoft.App/containerApps \
  --metric "Requests" \
  --aggregation Total
```

**Custom Metrics (Application Insights)**:
```python
from applicationinsights import TelemetryClient

tc = TelemetryClient(instrumentation_key=os.getenv('APPINSIGHTS_KEY'))

# Track custom metric
tc.track_metric('QueryTrustScore', 0.85)
tc.flush()
```

### Prometheus + Grafana (Advanced)

**Install Prometheus exporter**:

```python
# backend/requirements.txt
prometheus-fastapi-instrumentator==6.1.0

# backend/green_gov_rag/api/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
```

**Scrape metrics**:
```bash
curl http://localhost:8000/metrics
```

**Example metrics**:
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",path="/api/query",status="200"} 1234

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.5"} 890
http_request_duration_seconds_bucket{le="1.0"} 1200
http_request_duration_seconds_bucket{le="2.0"} 1230
```

## Alerting

### Alert Channels

**Email**: Direct email notifications
**Slack**: Webhook integration
**PagerDuty**: On-call escalation
**SMS**: Critical alerts only

### AWS CloudWatch Alarms

**High CPU Alert**:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name greengovrag-high-cpu \
  --alarm-description "Alert when CPU > 80% for 5 minutes" \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=greengovrag-service \
  --statistic Average \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:greengovrag-alerts
```

**High Error Rate Alert**:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name greengovrag-high-errors \
  --alarm-description "Alert when 5XX errors > 10/minute" \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --statistic Sum \
  --period 60 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:greengovrag-alerts
```

### Azure Monitor Alerts

**High Memory Alert**:
```bash
az monitor metrics alert create \
  --name HighMemoryAlert \
  --resource-group greengovrag-rg \
  --scopes /subscriptions/.../resourceGroups/greengovrag-rg/providers/Microsoft.App/containerApps/greengovrag-backend \
  --condition "avg MemoryPercentage > 90" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email=contact@sundeep.id.au
```

**Failed Health Check Alert**:
```bash
az monitor metrics alert create \
  --name FailedHealthCheck \
  --resource-group greengovrag-rg \
  --scopes /subscriptions/.../resourceGroups/greengovrag-rg/providers/Microsoft.App/containerApps/greengovrag-backend \
  --condition "avg Replicas < 1" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email=contact@sundeep.id.au
```

### Slack Integration

**AWS SNS → Slack**:
1. Create SNS topic: `greengovrag-alerts`
2. Subscribe webhook: `https://hooks.slack.com/services/YOUR/WEBHOOK/URL`
3. Configure CloudWatch alarms to publish to SNS topic

**Azure Action Group**:
```bash
az monitor action-group create \
  --name greengovrag-slack \
  --resource-group greengovrag-rg \
  --action webhook greengovrag-webhook https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### PagerDuty Integration

1. Create PagerDuty service
2. Get integration key
3. Configure SNS subscription (AWS) or Action Group (Azure)
4. Set escalation policy

## Tracing

### AWS X-Ray

**Enable X-Ray**:

```python
# backend/requirements.txt
aws-xray-sdk==2.12.0

# backend/green_gov_rag/api/main.py
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

app = FastAPI()
app.add_middleware(XRayMiddleware, recorder=xray_recorder)
```

**View traces**:
```bash
# AWS Console: X-Ray → Traces
# Or CLI
aws xray get-trace-summaries \
  --start-time 2025-11-15T00:00:00Z \
  --end-time 2025-11-15T23:59:59Z \
  --filter-expression 'service("greengovrag-backend")'
```

### Azure Application Insights

**Enable tracing**:

```python
# backend/requirements.txt
opencensus-ext-azure==1.1.13
opencensus-ext-fastapi==0.7.1

# backend/green_gov_rag/api/main.py
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.fastapi import FastAPIMiddleware

app = FastAPI()
app.add_middleware(
    FastAPIMiddleware,
    exporter=AzureExporter(connection_string=os.getenv('APPINSIGHTS_CONNECTION_STRING'))
)
```

**View traces**: Azure Portal → Application Insights → Transaction search

## Dashboards

### CloudWatch Dashboard

**Create dashboard**:
```bash
aws cloudwatch put-dashboard \
  --dashboard-name greengovrag-dashboard \
  --dashboard-body file://dashboard.json
```

**dashboard.json**:
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "title": "API Response Time (p95)",
        "metrics": [
          ["GreenGovRAG", "QueryResponseTime", {"stat": "p95"}]
        ],
        "period": 300,
        "region": "us-east-1"
      }
    },
    {
      "type": "metric",
      "properties": {
        "title": "Error Rate",
        "metrics": [
          ["AWS/ApiGateway", "5XXError", {"stat": "Sum"}]
        ],
        "period": 60,
        "region": "us-east-1"
      }
    }
  ]
}
```

### Azure Monitor Dashboard

**Create in Portal**: Azure Portal → Dashboards → New dashboard

**Pin metrics**:
1. Navigate to Container App
2. Click "Metrics"
3. Select metric (CPU, Memory, Requests)
4. Click "Pin to dashboard"

### Grafana Dashboard

**Install Grafana**:
```bash
docker run -d -p 3000:3000 grafana/grafana
```

**Add Prometheus data source**: Configuration → Data sources → Add Prometheus

**Create dashboard**:
1. New dashboard
2. Add panel
3. Query: `rate(http_requests_total[5m])`
4. Visualization: Time series

**Import community dashboard**: Dashboard ID 1860 (Node Exporter)

## Debugging

### Live Debugging

**AWS ECS Exec** (SSH into container):
```bash
aws ecs execute-command \
  --cluster greengovrag-cluster \
  --task <task-id> \
  --container greengovrag-backend \
  --interactive \
  --command "/bin/bash"
```

**Azure Container Instance Exec**:
```bash
az container exec \
  --resource-group greengovrag-rg \
  --name greengovrag-backend \
  --exec-command "/bin/bash"
```

### Database Queries

**Check document count**:
```sql
SELECT COUNT(*) FROM documents;
```

**Check recent queries**:
```sql
SELECT * FROM query_logs
ORDER BY created_at DESC
LIMIT 10;
```

**Check cache hit rate**:
```sql
SELECT
  SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS cache_hit_rate
FROM query_logs
WHERE created_at > NOW() - INTERVAL '24 hours';
```

### Vector Store Debugging

**Qdrant API**:
```bash
# Collection info
curl http://qdrant-instance:6333/collections/greengovrag

# Count documents
curl http://qdrant-instance:6333/collections/greengovrag/points/count

# Search test
curl -X POST http://qdrant-instance:6333/collections/greengovrag/points/search \
  -H 'Content-Type: application/json' \
  -d '{
    "vector": [0.1, 0.2, ...],
    "limit": 5
  }'
```

## Performance Profiling

### Python Profiling

**cProfile**:
```bash
python -m cProfile -o profile.stats -m uvicorn green_gov_rag.api.main:app

# Analyze
python -m pstats profile.stats
> sort cumtime
> stats 20
```

**py-spy** (production-safe):
```bash
pip install py-spy

# Profile running process
py-spy top --pid <backend-pid>

# Flame graph
py-spy record -o profile.svg --pid <backend-pid>
```

### API Load Testing

**Apache Bench**:
```bash
ab -n 1000 -c 10 http://localhost:8000/api/health
```

**Locust** (more advanced):
```python
# locustfile.py
from locust import HttpUser, task

class GreenGovRAGUser(HttpUser):
    @task
    def query(self):
        self.client.post("/api/query", json={
            "query": "What are NGER requirements?",
            "max_sources": 5
        })

# Run
locust -f locustfile.py --host http://localhost:8000
```

## Cost Monitoring

### AWS Cost Explorer

**View costs**:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-30 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

**Cost alert**:
```bash
aws budgets create-budget \
  --account-id 123456789012 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

### Azure Cost Management

**View costs**: Azure Portal → Cost Management → Cost analysis

**Create budget**:
```bash
az consumption budget create \
  --budget-name greengovrag-budget \
  --amount 100 \
  --time-grain Monthly \
  --start-date 2025-11-01 \
  --end-date 2026-11-01 \
  --resource-group greengovrag-rg
```

## Best Practices

### Logging
1. Use structured logging (JSON)
2. Include request IDs for tracing
3. Don't log sensitive data (API keys, PII)
4. Use appropriate log levels
5. Aggregate logs centrally

### Metrics
1. Track business metrics (trust score, query success rate)
2. Monitor the four golden signals: latency, traffic, errors, saturation
3. Use percentiles (p50, p95, p99) not averages
4. Set appropriate thresholds

### Alerting
1. Alert on symptoms, not causes
2. Avoid alert fatigue (tune thresholds)
3. Use runbooks for common alerts
4. Escalate critical alerts (PagerDuty)
5. Review and update alerts regularly

### Dashboards
1. Keep dashboards simple and focused
2. Use consistent time ranges
3. Group related metrics
4. Share dashboards with team
5. Update dashboards as system evolves

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0

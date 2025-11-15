# Production Checklist

> Pre-launch verification for GreenGovRAG deployment

## Infrastructure

### Compute

- [ ] Backend service deployed and running
- [ ] Auto-scaling configured (min 1, max 10)
- [ ] Health checks passing (HTTP 200 on `/api/health`)
- [ ] Container image tagged with version (not `latest`)
- [ ] Resource limits set (CPU, memory)
- [ ] Graceful shutdown configured (SIGTERM handling)

### Database

- [ ] PostgreSQL deployed and accessible
- [ ] `pgvector` extension installed
- [ ] Database migrations applied (run `alembic upgrade head`)
- [ ] Connection pooling configured (max 20 connections)
- [ ] SSL/TLS enabled for connections
- [ ] Automated backups enabled (7-day retention minimum)
- [ ] Point-in-time recovery (PITR) configured
- [ ] Database credentials stored in secrets manager

### Vector Store

- [ ] Qdrant deployed (EC2 Spot for AWS, Container Instance for Azure)
- [ ] Persistent storage configured (EBS/Azure Files)
- [ ] Collections created (`greengovrag` collection exists)
- [ ] HNSW index configured for performance
- [ ] Backup strategy in place (weekly snapshots)
- [ ] Auto-restart policy configured

### Storage

- [ ] S3 bucket / Blob Storage created for documents
- [ ] Lifecycle policies configured (archive after 90 days)
- [ ] Versioning enabled
- [ ] Public access blocked (private only)
- [ ] CORS configured for frontend domain
- [ ] CDN (CloudFront / Front Door) configured
- [ ] HTTPS enforced

### Caching

- [ ] DynamoDB / Cosmos DB configured
- [ ] TTL enabled (1 hour for queries)
- [ ] On-demand billing enabled (or appropriate provisioned capacity)
- [ ] Backup enabled

## Security

### Authentication & Authorization

- [ ] API keys rotated from development defaults
- [ ] Admin endpoints protected (future: add authentication)
- [ ] Rate limiting enabled (30 requests/minute)
- [ ] CORS whitelist configured (not `*`)
- [ ] JWT secret set (if using authentication)

### Network Security

- [ ] HTTPS enforced (redirect HTTP → HTTPS)
- [ ] SSL certificates valid and auto-renewing
- [ ] Private subnets for database and Qdrant
- [ ] Security groups / NSGs configured (least privilege)
- [ ] VPC / VNet configured with public/private subnets
- [ ] Bastion host configured for SSH access (if needed)

### Secrets Management

- [ ] All secrets in AWS Secrets Manager / Azure Key Vault
- [ ] `.env` files excluded from version control (in `.gitignore`)
- [ ] No hardcoded API keys in code
- [ ] Secrets rotated every 90 days
- [ ] LLM API keys stored securely
- [ ] Database passwords strong (20+ characters)

### Compliance

- [ ] Data retention policy defined
- [ ] GDPR compliance reviewed (if applicable)
- [ ] Logging excludes sensitive data (PII, API keys)
- [ ] Backup encryption enabled
- [ ] Data at rest encryption enabled

## Configuration

### Environment Variables

- [ ] `LLM_PROVIDER` set correctly (`openai`, `azure`, `bedrock`)
- [ ] `LLM_MODEL` set to production model (`gpt-5-mini` recommended)
- [ ] `VECTOR_STORE_TYPE` set to `qdrant` (not `faiss`)
- [ ] `DATABASE_URL` points to production database
- [ ] `CLOUD_PROVIDER` set (`aws` or `azure`)
- [ ] `LOG_LEVEL` set to `INFO` (not `DEBUG` in production)
- [ ] `ENVIRONMENT` set to `production`
- [ ] `API_RATE_LIMIT` configured appropriately

### LLM Configuration

- [ ] API keys valid and working
- [ ] Model deployed (for Azure OpenAI)
- [ ] Fallback LLM configured (optional but recommended)
- [ ] Token limits configured (max 4000 for responses)
- [ ] Temperature set appropriately (0.2 for factual responses)

### ETL Pipeline

- [ ] Document sources configured (`configs/documents_config.yml`)
- [ ] ETL scheduled to run daily (2 AM UTC via GitHub Actions)
- [ ] Initial ETL run completed (vector store populated)
- [ ] Document validation passing (no broken URLs)
- [ ] Chunking parameters tuned (500 tokens, 100 overlap)

## Monitoring & Logging

### Logging

- [ ] Centralized logging configured (CloudWatch / Log Analytics)
- [ ] Log retention set (30 days minimum)
- [ ] Error logs monitored (alerts on 5XX errors)
- [ ] Access logs enabled
- [ ] Structured logging format (JSON)

### Monitoring

- [ ] Uptime monitoring configured (external service or CloudWatch/Azure Monitor)
- [ ] Health check endpoint monitored (`/api/health`)
- [ ] CPU/Memory metrics tracked
- [ ] Database connection pool metrics tracked
- [ ] Vector search latency tracked
- [ ] API response time tracked (p50, p95, p99)

### Alerts

- [ ] High CPU alert (> 80% for 5 minutes)
- [ ] High memory alert (> 90% for 5 minutes)
- [ ] High error rate alert (> 10 5XX errors/minute)
- [ ] Database connection alert (> 80% pool usage)
- [ ] Disk space alert (> 85% used)
- [ ] Failed health check alert (3 consecutive failures)
- [ ] ETL pipeline failure alert

### Observability

- [ ] Distributed tracing enabled (X-Ray / Application Insights)
- [ ] Custom metrics tracked (query success rate, trust scores)
- [ ] Dashboard created (Grafana / CloudWatch / Azure Monitor)
- [ ] Anomaly detection configured (optional)

## Performance

### API Performance

- [ ] Response time < 2s (p95) for queries
- [ ] Vector search < 100ms
- [ ] Database queries optimized (indexes created)
- [ ] Connection pooling configured
- [ ] Caching working (> 50% cache hit rate for repeated queries)

### Scaling

- [ ] Auto-scaling tested (load test performed)
- [ ] Database can handle expected load (connection limit check)
- [ ] Qdrant can handle expected vector search load
- [ ] CDN caching configured (static assets)
- [ ] API Gateway caching enabled (optional)

### Load Testing

- [ ] Load test performed (simulate 1000 concurrent users)
- [ ] Stress test performed (find breaking point)
- [ ] Sustained load test (24 hours at expected traffic)
- [ ] Spike test performed (sudden traffic increase)

## Backup & Disaster Recovery

### Backups

- [ ] Database automated backups enabled (daily)
- [ ] Qdrant snapshots scheduled (weekly)
- [ ] Configuration backed up (IaC code in Git)
- [ ] Document sources backed up (S3 / Blob Storage)
- [ ] Backup restoration tested (at least once)

### Disaster Recovery

- [ ] Recovery Time Objective (RTO) defined (target: 4 hours)
- [ ] Recovery Point Objective (RPO) defined (target: 24 hours)
- [ ] DR plan documented and tested
- [ ] Database restore procedure documented
- [ ] Qdrant restore procedure documented
- [ ] Failover DNS configured (optional multi-region)

## CI/CD

### GitHub Actions

- [ ] Deploy workflow configured (`.github/workflows/deploy-aws.yml` or `deploy-azure.yml`)
- [ ] ETL scheduled workflow configured (`.github/workflows/etl-scheduled.yml`)
- [ ] Test workflow configured (runs on PRs)
- [ ] GitHub Secrets configured (API keys, cloud credentials)
- [ ] Manual approval required for production deploy (optional)

### Deployment Process

- [ ] Blue-green deployment or rolling updates configured
- [ ] Rollback procedure documented and tested
- [ ] Database migration strategy defined (forward-only migrations)
- [ ] Zero-downtime deployment verified
- [ ] Deployment notifications configured (Slack, email)

## Testing

### Functional Testing

- [ ] All unit tests passing (`pytest tests/`)
- [ ] Integration tests passing (API endpoints)
- [ ] End-to-end tests passing (full RAG query flow)
- [ ] Admin API tests passing

### Data Quality

- [ ] Vector store populated (> 0 documents)
- [ ] Sample queries return relevant results
- [ ] Trust scores calculated correctly
- [ ] Citations formatted properly
- [ ] Geospatial filtering working (LGA queries)

### Security Testing

- [ ] OWASP Top 10 vulnerabilities checked
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified
- [ ] CSRF protection enabled (if using cookies)
- [ ] Rate limiting tested (blocked after limit)
- [ ] Secrets not exposed in logs or errors

## Documentation

### Internal Documentation

- [ ] Architecture diagram created
- [ ] Deployment runbook created
- [ ] Incident response plan documented
- [ ] On-call rotation defined (if applicable)
- [ ] Monitoring dashboard documented

### Public Documentation

- [ ] API documentation generated (`/docs` Swagger UI)
- [ ] User guide published
- [ ] Deployment guide published
- [ ] Troubleshooting guide published
- [ ] Changelog maintained

## Legal & Compliance

### Data Governance

- [ ] Data retention policy defined and implemented
- [ ] Data deletion procedure documented
- [ ] Privacy policy published (if public-facing)
- [ ] Terms of service published (if public-facing)
- [ ] GDPR compliance reviewed (if applicable to EU users)

### Licensing

- [ ] Open source licenses reviewed (dependencies)
- [ ] License file included (LICENSE.md)
- [ ] Attribution for third-party libraries

## Cost Management

### Cost Monitoring

- [ ] Cost alerts configured (> $100/month)
- [ ] Cost breakdown by service tracked
- [ ] Unused resources identified and removed
- [ ] Reserved instances considered (AWS RDS, EC2)
- [ ] Spot instances used where appropriate (Qdrant)

### Cost Optimization

- [ ] Right-sized instances (not over-provisioned)
- [ ] Idle resources scheduled to stop (dev/test environments)
- [ ] Storage lifecycle policies configured (S3/Blob)
- [ ] CDN caching maximized
- [ ] DynamoDB/Cosmos DB on-demand pricing verified

## Launch

### Pre-Launch

- [ ] Final smoke test performed
- [ ] All stakeholders notified of launch
- [ ] Rollback plan ready
- [ ] Monitoring dashboard open
- [ ] On-call engineer available

### Launch Day

- [ ] DNS updated to production (if applicable)
- [ ] Frontend deployed
- [ ] Backend deployed
- [ ] Health checks passing
- [ ] Sample queries tested end-to-end
- [ ] Logs monitored for errors
- [ ] Metrics look normal

### Post-Launch

- [ ] Monitor for 24 hours (close attention first 4 hours)
- [ ] Review error logs
- [ ] Check performance metrics
- [ ] Verify auto-scaling working
- [ ] Collect user feedback
- [ ] Document lessons learned

## Post-Production

### Week 1

- [ ] Daily log review
- [ ] Performance metrics review
- [ ] Cost tracking review
- [ ] User feedback collected
- [ ] Bugs triaged and prioritized

### Month 1

- [ ] Performance tuning based on real traffic
- [ ] Cost optimization opportunities identified
- [ ] Security audit performed
- [ ] Backup restoration tested
- [ ] Disaster recovery plan reviewed

### Ongoing

- [ ] Monthly security updates
- [ ] Quarterly dependency updates
- [ ] Quarterly DR drill
- [ ] Annual security audit
- [ ] Continuous monitoring and optimization

---

## Checklist Summary

**Total Items**: 150+

**Critical Items** (must be done):
- Infrastructure deployed and healthy
- Security configured (HTTPS, secrets, CORS)
- Monitoring and alerts configured
- Backups enabled
- Testing passed

**Important Items** (should be done):
- Load testing performed
- DR plan documented
- Cost monitoring configured
- Documentation complete

**Nice to Have** (can be done post-launch):
- Advanced observability (X-Ray, custom metrics)
- Multi-region failover
- Blue-green deployments
- Comprehensive load testing

---

**Last Updated**: 2025-11-15
**Version**: 1.0.0

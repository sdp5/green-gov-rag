# Cloud Provider Comparison

## Quick Comparison

| Feature | AWS | Azure | Local |
|---------|-----|-------|-------|
| **Setup Complexity** | Medium | Medium | Low |
| **Monthly Cost (Dev)** | $60-80 | $30-50 | $0 |
| **Monthly Cost (Prod)** | $250-300 | $230-260 | $100* |
| **Scalability** | Excellent | Excellent | Limited |
| **Australia Region** | Sydney | Australia East | N/A |
| **Data Sovereignty** | IRAP certified | IRAP certified | Self-managed |
| **Container Platform** | ECS Fargate | Container Apps | Docker Compose |
| **PostgreSQL** | RDS | Azure Database | Docker |
| **Storage** | S3 | Blob Storage | Filesystem |
| **LLM Integration** | Bedrock | Azure OpenAI | OpenAI API |
| **IaC** | CDK (Python) | Bicep | Docker Compose |

*Local = electricity + internet only

## AWS

### Pros
- Mature ecosystem, extensive services
- Strong Sydney presence (low latency)
- Bedrock for LLMs (Claude, Titan)
- ECS Fargate serverless containers
- S3 durability (11 9's)

### Cons
- Complex pricing
- Steeper learning curve
- VPC networking required

### Costs (AUD/month)

**Development:**
- ECS Fargate (0.25 vCPU): $15
- RDS (db.t3.micro): $20
- S3 (10GB): $0.30
- ALB: $20
- **Total: ~$60-80**

**Production:**
- ECS Fargate (2 tasks, 1 vCPU): $120
- RDS (db.t3.small, Multi-AZ): $80
- S3 (100GB): $3
- CloudWatch: $10
- **Total: ~$250-300**

### Deploy

```bash
cd deploy/aws
cdk deploy
```

## Azure

### Pros
- Container Apps (excellent serverless platform)
- Azure OpenAI native integration
- Simpler, more predictable pricing
- Managed Identity (no credentials)
- Cleaner IaC with Bicep

### Cons
- Smaller ecosystem than AWS
- Azure OpenAI requires approval
- Less extensive documentation

### Costs (AUD/month)

**Development:**
- Container Apps (0.25 vCPU): $12
- PostgreSQL (B1ms): $18
- Blob Storage (10GB): $0.25
- **Total: ~$30-50**

**Production:**
- Container Apps (2 instances): $90
- PostgreSQL (D2s_v3): $120
- Blob Storage (100GB): $2.50
- App Gateway: $25
- **Total: ~$230-260**

### Deploy

```bash
cd deploy/azure
./deploy.sh
```

## Local / On-Premises

### Pros
- Zero cloud costs
- Full control, complete privacy
- Fast iteration, no internet dependency
- Great for development

### Cons
- No auto-scaling
- Maintenance burden
- No HA (single point of failure)
- Hardware upfront costs

### Costs

**Initial:**
- Server hardware: $1,000-3,000
- UPS: $200-500
- **Total: ~$1,300-3,800**

**Ongoing:**
- Electricity: $20/month
- Internet: $80/month
- **Total: ~$100/month**

**Break-even:** 12-18 months vs cloud

### Deploy

```bash
cd deploy/docker
docker-compose up -d
```

## Decision Matrix

### Choose AWS if:
- Already on AWS
- Need AWS Bedrock (Claude, Titan)
- Multi-region deployment
- AWS expertise in-house
- Complex pricing acceptable

### Choose Azure if:
- Already on Azure/Microsoft
- Need Azure OpenAI Service
- Want simpler pricing
- Prefer serverless-first (Container Apps)
- Microsoft 365 integration

### Choose Local if:
- Development/testing phase
- Strict data privacy requirements
- Limited budget
- Need full control
- Learning the technology

## Migration Path

```
Local Development → Cloud Staging → Cloud Production → Multi-Cloud (optional)
  (Weeks 1-4)        (Weeks 5-8)      (Week 9+)         (Future)
```

**Phase 1:** Local dev and testing
**Phase 2:** Cloud staging with production-like data
**Phase 3:** Production deployment with backups/DR
**Phase 4:** Optional multi-cloud redundancy

## Australian Government Considerations

### Data Sovereignty

| Provider | Region | Certifications |
|----------|--------|----------------|
| AWS | Sydney (ap-southeast-2) | IRAP, ISO 27001 |
| Azure | Australia East/Southeast | IRAP, ISO 27001 |
| Local | Your datacenter | Your compliance |

### Recommendations by Agency

1. **Federal agencies:** AWS or Azure (IRAP certified)
2. **State agencies:** Based on existing contracts
3. **Local councils:** Azure (Microsoft agreements) or Local
4. **Development:** Local, then migrate to cloud

## TCO Comparison (1 Year)

**AWS Production:**
- Monthly: $300 × 12 = $3,600
- Setup: 40 hours × $150/hr = $6,000
- **Year 1: $9,600**

**Azure Production:**
- Monthly: $250 × 12 = $3,000
- Setup: 35 hours × $150/hr = $5,250
- **Year 1: $8,250**

**Local Production:**
- Hardware: $2,500 (one-time)
- Setup: 50 hours × $150/hr = $7,500
- Monthly: $100 × 12 = $1,200
- **Year 1: $11,200**

**Break-even:** Azure vs Local = 6 years, AWS vs Local = 5 years

## Performance

### Latency (Sydney users)

| Provider | API | Storage |
|----------|-----|---------|
| AWS | ~5ms | ~10ms |
| Azure | ~5ms | ~10ms |
| Local (same DC) | <1ms | <1ms |

### Throughput

| Provider | Max Requests/sec | Storage GB/s |
|----------|------------------|--------------|
| AWS | Auto-scales | 5-10 |
| Azure | Auto-scales | 5-10 |
| Local | Hardware limited | Hardware limited |

## Recommendations by Scenario

**Startup/MVP:** Local → Azure (lower cost)
**Government:** AWS or Azure (IRAP)
**Enterprise:** Multi-Cloud (AWS + Azure for DR)
**Research/Academic:** Local or Azure Education credits

## Summary Ratings

| Requirement | AWS | Azure | Local |
|-------------|-----|-------|-------|
| Cost-effective | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Scalability | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Easy to start | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Enterprise ready | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Government use | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## Final Recommendation

1. **Start local** for development
2. **Choose Azure** for production (simpler, cheaper)
3. **Use AWS** if already invested in AWS
4. **Multi-cloud** for enterprise HA

## See Also

- [Cloud Migration](./CLOUD_MIGRATION.md) - Migration guide and scripts
- [Data Sources](./DATA.md) - Data sovereignty considerations
- [Overview](README.md) - System architecture

# Deployment Overview

> Comprehensive deployment options for GreenGovRAG

## Architecture Options

GreenGovRAG supports multiple deployment architectures to suit different requirements and budgets:

### 1. Local Development (Docker Compose)
- **Best for**: Development, testing, proof-of-concept
- **Complexity**: Low
- **Setup time**: 5 minutes
- **Scalability**: Limited to single machine

### 2. AWS Deployment (ECS Fargate)
- **Best for**: Production, scalable applications
- **Complexity**: Medium
- **Setup time**: 30-45 minutes
- **Scalability**: Auto-scaling to thousands of requests

### 3. Azure Deployment (Container Apps)
- **Best for**: Enterprise Azure environments
- **Complexity**: Medium
- **Setup time**: 30-45 minutes
- **Scalability**: Auto-scaling with KEDA

## Component Architecture

All deployment options include these core components:

### Backend API (FastAPI)
- RESTful API for RAG queries
- Admin endpoints for management
- Swagger/OpenAPI documentation
- Health check endpoints

### Vector Store
- **Development**: FAISS (in-memory)
- **Production**: Qdrant (persistent, scalable)

### Database (PostgreSQL)
- Document metadata storage
- Query analytics
- User sessions (future)
- pgvector extension for hybrid search

### LLM Provider (External API)
- OpenAI GPT-5-mini (recommended)
- Azure OpenAI
- AWS Bedrock (Claude, Titan)
- Anthropic Claude

### Frontend (React)
- User interface for queries
- Document browser
- Analytics dashboard

### ETL Pipeline
- **Development**: Airflow (Docker)
- **Production**: GitHub Actions (scheduled)

## Deployment Comparison

| Feature | Local Docker | AWS | Azure |
|---------|-------------|-----|-------|
| **Setup** | 5 min | 45 min | 45 min |
| **Auto-scaling** | No | Yes | Yes |
| **High Availability** | No | Yes | Yes |
| **Monitoring** | Basic | CloudWatch | App Insights |
| **CI/CD** | Manual | GitHub Actions | Azure DevOps |
| **Best for** | Dev/Test | Production | Enterprise |

See [Cloud Comparison](cloud-comparison.md) for detailed analysis.

## Prerequisites

### All Deployments
- Git repository access
- LLM API key (OpenAI, Azure, or Bedrock)
- Basic understanding of Docker and containers

### AWS Deployment
- AWS account with billing enabled
- AWS CLI configured (`aws configure`)
- Node.js 18+ (for AWS CDK)
- IAM permissions for:
  - ECS, EC2, RDS, S3, CloudFront, DynamoDB, IAM, CloudFormation

### Azure Deployment
- Azure subscription
- Azure CLI installed (`az login`)
- Resource group creation permissions
- Contributor role on subscription

## Security Considerations

### API Keys and Secrets
- Store in environment variables (`.env` for local)
- Use AWS Secrets Manager (AWS)
- Use Azure Key Vault (Azure)
- Never commit to version control

### Network Security
- Use HTTPS only in production
- Configure CORS for frontend domain
- Implement rate limiting (default: 30 req/min)
- Use VPC private subnets (AWS) or VNet (Azure)

### Database Security
- Enable SSL connections
- Use strong passwords (20+ characters)
- Restrict access to backend only
- Enable automatic backups

### Authentication (Future)
- OAuth2/OIDC integration
- JWT token-based auth
- Role-based access control (RBAC)

## Monitoring and Logging

### Development
- Docker Compose logs: `docker-compose logs -f`
- FastAPI logs: `uvicorn` stdout
- PostgreSQL logs: In container

### AWS
- CloudWatch Logs for all services
- CloudWatch Metrics for performance
- X-Ray for distributed tracing
- CloudWatch Alarms for errors

### Azure
- Application Insights for telemetry
- Log Analytics workspace
- Azure Monitor alerts
- Container Apps metrics

See [Monitoring Guide](monitoring.md) for detailed setup.

## Backup and Disaster Recovery

### Database Backups
- **Local**: Manual PostgreSQL dumps
- **AWS**: Automated RDS snapshots (daily)
- **Azure**: Automated PostgreSQL backups (7-day retention)

### Vector Store Backups
- **FAISS**: File-based, commit to S3/Blob Storage
- **Qdrant**: Snapshot API + scheduled backups

### Configuration Backups
- Version control (Git) for infrastructure code
- Environment variables in secret manager
- Document source configs in repository

## CI/CD Pipeline

### GitHub Actions Workflows
- **Deploy Backend (AWS)**: `.github/workflows/deploy-aws.yml`
- **Deploy Frontend**: `.github/workflows/deploy-frontend.yml`
- **ETL Scheduled**: `.github/workflows/etl-scheduled.yml` (daily 2 AM UTC)
- **Tests**: `.github/workflows/test.yml` (on PRs)

### Manual Deployment
- AWS: `cd deploy/aws && cdk deploy`
- Azure: `cd deploy/azure && az deployment group create`
- Local: `docker-compose up --build`

## Cost Optimization

### Development
- Use local Docker (free)
- Use FAISS instead of Qdrant
- Use OpenAI free tier (if available)
- Use SQLite instead of PostgreSQL (not recommended)

### Production
- Use AWS Spot instances for Qdrant
- Use CDN caching to reduce backend requests
- Use DynamoDB for query result caching
- Use gpt-5-mini instead of gpt-5
- Schedule ETL during off-peak hours
- Auto-scale down during low traffic

## Getting Started

Choose your deployment path:

1. **Quick Start**: [Local Docker Deployment](local-docker.md) (5 minutes)
2. **Production**: [AWS Deployment](aws.md) (45 minutes)
3. **Enterprise**: [Azure Deployment](azure.md) (45 minutes)

---

**Last Updated**: 2025-11-22

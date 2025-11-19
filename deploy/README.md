# GreenGovRAG Deployment Guide

Complete deployment guide for GreenGovRAG with multi-cloud support, cost-optimized architecture, and automated CI/CD pipelines.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Cost Breakdown](#cost-breakdown)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [AWS Deployment](#aws-deployment)
- [Azure Deployment](#azure-deployment)
- [GitHub Actions CI/CD](#github-actions-cicd)
- [Documentation Deployment](#documentation-deployment)
- [ETL Pipeline](#etl-pipeline)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)

---

## Architecture Overview

### Production Architecture (AWS)

```
┌─────────────┐
│  CloudFront │ ← Frontend (S3 + CDN)
└──────┬──────┘
       │
┌──────▼──────────┐
│  API Gateway    │ ← REST API
│   (HTTP API)    │
└──────┬──────────┘
       │
┌──────▼──────────┐
│  ECS Fargate    │ ← Backend (FastAPI)
│  (2 tasks)      │
└──────┬──────────┘
       │
       ├─→ RDS PostgreSQL (t4g.micro + pgvector)
       ├─→ DynamoDB (caching)
       ├─→ EC2 Spot (Qdrant on t4g.micro)
       ├─→ S3 (document storage)
       └─→ CloudWatch (monitoring)

GitHub Actions ─→ ECR → ECS (auto-deploy)
GitHub Actions ─→ S3 → CloudFront (frontend)
GitHub Actions ─→ ETL Pipeline (scheduled)
GitHub Actions ─→ GitHub Pages (documentation)
```

### Development Architecture (Local)

```
┌──────────────┐
│   Frontend   │ ← React Dev Server (5173)
└──────┬───────┘
       │
┌──────▼───────┐
│   Backend    │ ← FastAPI (8000)
└──────┬───────┘
       │
       ├─→ PostgreSQL + pgvector (5432)
       ├─→ Qdrant (6333)
       ├─→ Local Storage
       └─→ Airflow UI (8080) - optional
```

**Docker Compose Profiles:**
- Default: Backend + Database + Qdrant
- Dev Profile: Adds Airflow UI for pipeline management

---

## Prerequisites

### Required Tools

```bash
# Check versions
python --version  # 3.12+
node --version    # 20+
docker --version  # 24+

# AWS deployment
aws --version     # AWS CLI v2
cdk --version     # AWS CDK v2

# Azure deployment
az --version      # Azure CLI

# Optional
terraform --version
```

### API Keys Required

```bash
# LLM Provider (choose one)
OPENAI_API_KEY=sk-...           # Recommended: gpt-4o-mini
# OR
AZURE_OPENAI_API_KEY=...        # Best cost/performance
# OR
ANTHROPIC_API_KEY=...
# OR
AWS_ACCESS_KEY_ID=...           # For Bedrock

# Optional
VITE_MAPBOX_TOKEN=...           # For map features (future)
```

---

## Local Development

### Quick Start (Docker Compose)

```bash
# Navigate to docker directory
cd deploy/docker

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: DATABASE_URL, OPENAI_API_KEY (or other LLM provider)
nano .env

# Start services (no Airflow)
docker-compose up -d

# OR with Airflow UI for pipeline management
docker-compose --profile dev up -d

# Access services
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:3000
# - Airflow UI: http://localhost:8080 (dev profile only)
#   - Username: admin
#   - Password: admin
```

### Service Management

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Restart a service
docker-compose restart backend

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# Update images
docker-compose pull
docker-compose up -d
```

### Manual Local Setup (Without Docker)

```bash
# 1. Backend
cd backend
pip install -e .[dev]
cp .env.example .env
# Edit .env
alembic upgrade head
uvicorn green_gov_rag.api.main:app --reload

# 2. Frontend
cd frontend
npm install
cp .env.example .env
# Edit .env
npm run dev

# 3. PostgreSQL (install separately)
# Install pgvector extension
# Create database: greengovrag

# 4. Qdrant (optional, can use FAISS)
docker run -p 6333:6333 qdrant/qdrant
```

---

## AWS Deployment

### 1. Prerequisites

```bash
# Install AWS CDK
npm install -g aws-cdk

# Configure AWS credentials
aws configure

# Install Python dependencies
cd deploy/aws
pip install -r requirements.txt
```

### 2. Bootstrap CDK

```bash
# One-time setup per AWS account/region
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

### 3. Deploy Infrastructure

```bash
# Review changes
cdk diff

# Deploy stack
cdk deploy GreenGovRAGStack

# Note the outputs:
# - BackendECRRepository
# - FrontendS3Bucket
# - CloudFrontDistributionURL
# - APIGatewayURL
```

### 4. Store Secrets in AWS Systems Manager

```bash
# OpenAI API Key
aws ssm put-parameter \
  --name "/greengovrag/prod/openai-api-key" \
  --value "sk-..." \
  --type "SecureString"

# Database password (if not auto-generated)
aws ssm put-parameter \
  --name "/greengovrag/prod/db-password" \
  --value "your-secure-password" \
  --type "SecureString"

# Optional: Other LLM providers
aws ssm put-parameter \
  --name "/greengovrag/prod/anthropic-api-key" \
  --value "..." \
  --type "SecureString"
```

### 5. Deploy Backend (Manual)

```bash
# Get ECR repository URI from CDK outputs
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepository`].OutputValue' \
  --output text)

# Build Docker image
cd ../..
docker build -t greengovrag-backend -f deploy/docker/backend.Dockerfile .

# Tag and push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ECR_URI

docker tag greengovrag-backend:latest $ECR_URI:latest
docker push $ECR_URI:latest

# ECS will auto-deploy new image
```

### 6. Deploy Frontend

Frontend deploys automatically via GitHub Actions on push to `main`.

**Manual deployment:**

```bash
cd frontend
npm run build

# Get S3 bucket name from CDK outputs
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendS3Bucket`].OutputValue' \
  --output text)

# Upload to S3
aws s3 sync dist/ s3://$S3_BUCKET/ --delete

# Invalidate CloudFront cache
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionID`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $DISTRIBUTION_ID \
  --paths "/*"
```

---

## Azure Deployment

### 1. Prerequisites

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Set subscription
az account set --subscription "Your Subscription"
```

### 2. Deploy Infrastructure

```bash
cd deploy/azure

# Create resource group
az group create \
  --name greengovrag-rg \
  --location eastus

# Deploy Bicep template
az deployment group create \
  --resource-group greengovrag-rg \
  --template-file main.bicep \
  --parameters @parameters.json
```

### 3. Store Secrets in Azure Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name greengovrag-kv \
  --resource-group greengovrag-rg \
  --location eastus

# Store secrets
az keyvault secret set \
  --vault-name greengovrag-kv \
  --name openai-api-key \
  --value "sk-..."

az keyvault secret set \
  --vault-name greengovrag-kv \
  --name db-password \
  --value "your-secure-password"
```

### 4. Deploy Backend Container

```bash
# Build and push to Azure Container Registry
az acr build \
  --registry greengovragacr \
  --image greengovrag-backend:latest \
  --file deploy/docker/backend.Dockerfile \
  .

# Update Container App
az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --image greengovragacr.azurecr.io/greengovrag-backend:latest
```

---

## GitHub Actions CI/CD

### Required Secrets

Configure these in **Settings → Secrets and variables → Actions**:

```
# AWS Deployment
AWS_ROLE_ARN                    # IAM role ARN for OIDC
AWS_REGION                      # us-east-1

# Azure Deployment (alternative)
AZURE_CREDENTIALS               # Service Principal JSON

# LLM Providers
OPENAI_API_KEY                  # OpenAI API key
AZURE_OPENAI_API_KEY            # Azure OpenAI (optional)
ANTHROPIC_API_KEY               # Anthropic (optional)

# Frontend
VITE_MAPBOX_TOKEN               # MapBox token (optional)
VITE_API_URL                    # Backend API URL (set after deployment)
```

### Workflows Overview

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci-backend.yml` | Push to `dev`, PR | Backend tests + lint |
| `ci-frontend.yml` | Push to `dev`, PR | Frontend build + lint |
| `aws-deploy-backend.yml` | Push to `main` | Deploy backend to ECS |
| `aws-deploy-frontend.yml` | Push to `main` | Deploy frontend to S3 |
| `aws-etl-scheduled.yml` | Daily 2 AM UTC | Run ETL pipeline |
| `aws-backup-monitoring.yml` | Weekly | Database backups |
| `docs-deploy.yml` | Push to `main`/`docs` | Deploy documentation |

### Setting up AWS OIDC

```bash
# Create OIDC provider (one-time)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1

# Create IAM role with trust policy
# See: deploy/aws/github-actions-trust-policy.json

# Add permissions policy
# See: deploy/aws/github-actions-permissions-policy.json

# Get role ARN
aws iam get-role --role-name GitHubActionsRole --query 'Role.Arn'

# Add to GitHub Secrets as AWS_ROLE_ARN
```

### Manual Workflow Triggers

```bash
# Via GitHub UI
# Actions → Select workflow → Run workflow

# Via GitHub CLI
gh workflow run aws-etl-scheduled.yml
gh workflow run docs-deploy.yml
```

---

## Documentation Deployment

Documentation is automatically deployed to GitHub Pages:

### Automatic Deployment

- **Trigger**: Push to `main` or `docs` branches (when `docs/**` changes)
- **Workflow**: `.github/workflows/docs-deploy.yml`
- **URL**: https://sdp5.github.io/green-gov-rag/

### Manual Deployment

```bash
# Option 1: GitHub Actions
# Actions → Deploy Documentation → Run workflow

# Option 2: MkDocs CLI
cd docs
mkdocs gh-deploy --force
```

### First-Time Setup

1. Go to **Settings → Pages**
2. Set **Source** to "GitHub Actions"
3. Push to `main` to trigger deployment

See [docs/README.md](../docs/README.md) for more details.

---

## ETL Pipeline

### Scheduled Execution (Production)

ETL runs automatically via GitHub Actions daily at 2 AM UTC.

**To trigger manually:**

```bash
# Via GitHub UI
# Actions → ETL Pipeline - Scheduled → Run workflow

# Via GitHub CLI
gh workflow run aws-etl-scheduled.yml
```

### Local Execution

```bash
# Using Docker Compose (with Airflow UI)
docker-compose --profile dev up -d
# Open: http://localhost:8080
# Trigger: greengovrag_full_pipeline DAG

# Using CLI (without Airflow)
docker-compose exec backend greengovrag-cli etl run-pipeline

# Direct Python
cd backend
python -m green_gov_rag.cli etl run-pipeline --config configs/documents_config.yml
```

### Adding Document Sources

See [backend/green_gov_rag/etl/sources/README.md](../backend/green_gov_rag/etl/sources/README.md)

---

## Monitoring & Logging

### Health Checks

```bash
# API health
curl https://your-cloudfront-url/api/health

# System health (admin endpoint)
curl https://your-cloudfront-url/api/admin/system/health

# ECS service status
aws ecs describe-services \
  --cluster GreenGovRAG-Cluster \
  --services GreenGovRAG-BackendService
```

### Logs

**AWS:**

```bash
# Backend logs
aws logs tail /ecs/greengovrag-backend --follow

# ETL logs
aws logs tail /aws/lambda/greengovrag-etl --follow

# CloudFront access logs
aws s3 sync s3://greengovrag-logs/cloudfront/ ./logs/
```

**Docker:**

```bash
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f qdrant
```

### Metrics & Dashboards

**AWS CloudWatch:**
- ECS CPU/Memory utilization
- RDS connections and query performance
- API Gateway request count and latency
- Lambda execution duration

**Custom Metrics:**
- Query latency (p50, p95, p99)
- Cache hit rate
- LLM token usage
- Trust score distribution

**Access Dashboard:**
```bash
# CloudWatch dashboard URL from CDK outputs
aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue'
```

---

## Troubleshooting

### Common Issues

#### 1. Qdrant Spot Instance Terminated

**Symptom**: Vector search fails, 503 errors

**Solution**: Auto-recovery Lambda will launch new instance within 5 minutes. Check:

```bash
# Check instance status
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=GreenGovRAG-Qdrant" \
  --query 'Reservations[*].Instances[*].[InstanceId,State.Name]'

# Check Lambda logs
aws logs tail /aws/lambda/greengovrag-qdrant-recovery --follow
```

#### 2. ECS Task Fails to Start

**Symptom**: Service shows 0 running tasks

**Solution**:

```bash
# Get latest task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster GreenGovRAG-Cluster \
  --service-name GreenGovRAG-BackendService \
  --query 'taskArns[0]' --output text)

# Describe task
aws ecs describe-tasks \
  --cluster GreenGovRAG-Cluster \
  --tasks $TASK_ARN

# Check logs
aws logs tail /ecs/greengovrag-backend --follow
```

Common causes:
- Invalid environment variables
- Missing secrets in SSM Parameter Store
- ECR image not found (push latest image)

#### 3. Frontend Not Loading

**Symptom**: Blank page or 404 errors

**Solution**:

```bash
# Verify files in S3
aws s3 ls s3://greengovrag-frontend-bucket/

# Rebuild and redeploy
cd frontend
npm run build
aws s3 sync dist/ s3://greengovrag-frontend-bucket/ --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

#### 4. Database Connection Pool Exhausted

**Symptom**: 500 errors, "too many connections" in logs

**Solution**:

```bash
# Check current connections
aws rds describe-db-instances \
  --db-instance-identifier greengovrag-db \
  --query 'DBInstances[0].DBInstanceStatus'

# Increase connection pool size in .env
DATABASE_POOL_SIZE=50
DATABASE_MAX_OVERFLOW=20

# Or scale up RDS instance
aws rds modify-db-instance \
  --db-instance-identifier greengovrag-db \
  --db-instance-class db.t4g.small \
  --apply-immediately
```

#### 5. ETL Pipeline Fails

**Symptom**: Documents not updating, ETL workflow failed

**Solution**:

```bash
# Check GitHub Actions logs
gh run list --workflow=aws-etl-scheduled.yml
gh run view RUN_ID --log

# Run locally for debugging
docker-compose exec backend greengovrag-cli etl run-pipeline --debug

# Check document source configuration
cat backend/configs/documents_config.yml
```

### Performance Tuning

**Backend:**
- Reduce `CHUNK_SIZE` for faster processing
- Increase `TOP_K_RESULTS` for better recall
- Enable `ENABLE_CACHE` for repeated queries
- Use `gpt-4o-mini` instead of `gpt-4o` for cost savings

**Database:**
- Create indexes on frequently queried columns
- Increase `shared_buffers` for RDS
- Use read replicas for high read load

**Vector Store:**
- Use Qdrant for production (faster than FAISS)
- Adjust `HNSW_EF` parameter for accuracy vs. speed tradeoff

---

## Cleanup

### AWS

```bash
# Empty S3 buckets first (required)
aws s3 rm s3://greengovrag-frontend-bucket --recursive
aws s3 rm s3://greengovrag-documents --recursive
aws s3 rm s3://greengovrag-logs --recursive

# Delete ECR images
aws ecr batch-delete-image \
  --repository-name greengovrag-backend \
  --image-ids imageTag=latest

# Destroy CDK stack
cd deploy/aws
cdk destroy GreenGovRAGStack

# Delete secrets (optional)
aws ssm delete-parameter --name "/greengovrag/prod/openai-api-key"
aws ssm delete-parameter --name "/greengovrag/prod/db-password"
```

### Azure

```bash
# Delete resource group (deletes all resources)
az group delete --name greengovrag-rg --yes --no-wait

# Delete Key Vault (soft-delete protection)
az keyvault purge --name greengovrag-kv
```

### Local Docker

```bash
cd deploy/docker

# Stop and remove containers + volumes
docker-compose down -v

# Remove images
docker rmi greengovrag-backend
docker rmi greengovrag-frontend
```

---

## Cost Optimization Tips

1. **Use Spot Instances**: Qdrant on EC2 Spot saves 60-70%
2. **Right-size RDS**: Start with t4g.micro, scale as needed
3. **Enable Caching**: DynamoDB caching reduces LLM API calls
4. **Use gpt-4o-mini**: 15x cheaper than GPT-4 for most queries
5. **S3 Lifecycle Policies**: Archive old documents to Glacier
6. **CloudWatch Log Retention**: Reduce from 30 to 7 days
7. **Fargate Spot**: Consider Fargate Spot for 70% savings
8. **Monitor Usage**: Set up billing alerts and budgets

---

## Security Best Practices

1. **Secrets Management**: Use AWS SSM/Azure Key Vault, never commit secrets
2. **Network Security**: Use VPC endpoints, private subnets for RDS
3. **IAM Roles**: Use least-privilege IAM roles for ECS tasks
4. **Encryption**: Enable encryption at rest (S3, RDS, EBS)
5. **HTTPS Only**: Enforce HTTPS via CloudFront/API Gateway
6. **Rate Limiting**: Configure API Gateway throttling
7. **Database**: Use strong passwords, rotate credentials
8. **Dependency Scanning**: Use Dependabot for security updates

---

## Additional Resources

- **Main Documentation**: https://sdp5.github.io/green-gov-rag/
- **AWS CDK Stack**: [deploy/aws/app.py](aws/app.py)
- **Azure Bicep**: [deploy/azure/main.bicep](azure/main.bicep)
- **Docker Compose**: [deploy/docker/docker-compose.yml](docker/docker-compose.yml)
- **Backend README**: [../backend/README.md](../backend/README.md)
- **Frontend README**: [../frontend/README.md](../frontend/README.md)

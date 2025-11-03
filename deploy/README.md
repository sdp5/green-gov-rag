# GreenGovRAG Deployment Guide

Complete deployment guide for GreenGovRAG hybrid architecture with cost-optimized managed services.

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Cost Breakdown](#cost-breakdown)
- [Prerequisites](#prerequisites)
- [Local Development](#local-development)
- [AWS Deployment](#aws-deployment)
- [GitHub Actions Setup](#github-actions-setup)
- [ETL Pipeline](#etl-pipeline)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### Production (Hybrid)
```
CloudFront → API Gateway → ECS Fargate
              ├→ RDS PostgreSQL (t4g.micro + pgvector)
              ├→ DynamoDB (caching)
              └→ EC2 Spot (Qdrant on t4g.micro)
```

### Development (Local)
```bash
# No Airflow
docker-compose up

# With Airflow UI (http://localhost:8080)
docker-compose --profile dev up
```

---

## Cost Breakdown

### AWS: **$47/month**
- VPC Endpoint: $7.31
- RDS t4g.micro: $14.71
- ECS Fargate: $14.83
- Qdrant Spot: $2.64
- Other: $7.51

### Azure: **$45/month**
- Container Apps: $15.77
- PostgreSQL: $16.34
- Qdrant Spot VM: $4.50
- Other: $8.39

---

## Prerequisites

```bash
# Required
- AWS CLI v2
- AWS CDK v2
- Docker Desktop
- Python 3.12+
- Node.js 20+

# Get API keys
- OpenAI API key
- MapBox token (optional)
```

---

## Local Development

```bash
# Quick start
cd deploy/docker
cp .env.example .env  # Edit with your keys

docker-compose up -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000

# With Airflow
docker-compose --profile dev up -d
# Airflow UI: http://localhost:8080
```

---

## AWS Deployment

### 1. Bootstrap CDK
```bash
cd deploy/aws
pip install -r requirements.txt
cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

### 2. Deploy Stack
```bash
cdk deploy GreenGovRAGStack
```

### 3. Store Secrets
```bash
aws ssm put-parameter \
  --name "/greengovrag/prod/openai-api-key" \
  --value "sk-..." \
  --type "SecureString"
```

### 4. Push Backend Image
```bash
# Get ECR URI from CDK outputs
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepository`].OutputValue' \
  --output text)

# Build and push
docker build -t $ECR_URI:latest -f deploy/docker/backend.Dockerfile .
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker push $ECR_URI:latest
```

### 5. Deploy Frontend
Use GitHub Actions or manual:
```bash
cd frontend
npm run build
# Outputs go to S3 via CDK or GitHub Actions
```

---

## GitHub Actions Setup

### Required Secrets
```
AWS_ROLE_ARN              # IAM role for OIDC
OPENAI_API_KEY
VITE_MAPBOX_TOKEN
```

### Workflows
1. `deploy-aws.yml` - Deploy backend on push
2. `deploy-frontend.yml` - Deploy frontend
3. `etl-scheduled.yml` - Daily ETL at 2 AM UTC
4. `backup-and-monitoring.yml` - Weekly backups

---

## ETL Pipeline

### Via GitHub Actions
```
Actions → ETL Pipeline - Scheduled → Run workflow
```

### Via CLI (local/dev)
```bash
docker-compose exec backend \
  greengovrag-cli etl run-pipeline
```

---

## Monitoring

### Health Checks
```bash
# API
curl https://your-cf-url/api/health

# ECS Service
aws ecs describe-services \
  --cluster GreenGovRAG-Cluster \
  --services GreenGovRAG-BackendService
```

### Logs
```bash
aws logs tail /ecs/backend --follow
```

---

## Troubleshooting

### Qdrant Spot Terminated
Normal! Auto-recovery Lambda will launch new instance.

### ECS Task Fails
```bash
aws ecs describe-tasks --cluster GreenGovRAG-Cluster --tasks TASK-ID
aws logs tail /ecs/backend --follow
```

### Frontend Not Loading
```bash
# Invalidate CloudFront
aws cloudfront create-invalidation \
  --distribution-id DIST-ID \
  --paths "/*"
```

---

## Cleanup

```bash
# Empty S3 buckets first
aws s3 rm s3://BUCKET --recursive

# Destroy stack
cd deploy/aws
cdk destroy
```

---

*Last updated: 2025-01-16*
*Cost estimate based on us-east-1 pricing*

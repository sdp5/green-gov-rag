# GreenGovRAG Deployment Guide

This directory contains Infrastructure as Code (IaC) templates and deployment scripts for deploying GreenGovRAG to various cloud providers.

## 🌥️ Cloud-Agnostic Architecture

GreenGovRAG is designed to run on **AWS**, **Azure**, or **locally** with minimal code changes. The cloud abstraction layer automatically selects the appropriate backend based on the `CLOUD_PROVIDER` environment variable.

## Deployment Options Comparison

| Component            | AWS Option                               | Azure Option                                   | Local Option                     |
| -------------------- | ---------------------------------------- | ---------------------------------------------- | -------------------------------- |
| App hosting (API/UI) | ECS Fargate or Lambda + API Gateway      | Azure Container Apps                           | Docker Compose                   |
| Vector DB            | Self-host FAISS in ECS/EKS or EC2        | Self-host FAISS in Azure Container Apps or VM  | Local FAISS                      |
| RDBMS (metadata)     | Amazon RDS (PostgreSQL)                  | Azure Database for PostgreSQL                  | PostgreSQL container             |
| LLM Provider         | AWS Bedrock (Claude/Titan) or OpenAI API | Azure OpenAI Service (GPT-4, GPT-3.5)          | OpenAI API                       |
| File storage (PDFs)  | S3                                       | Azure Blob Storage                             | Local filesystem                 |
| Scheduler (ETL)      | EventBridge + Lambda or ECS + Celery     | Azure Logic Apps + Function App or Azure Batch | Cron jobs                        |
| Monitoring/CI        | CloudWatch + CodePipeline                | Azure Monitor + GitHub Actions                 | Docker logs + GitHub Actions     |
| Secrets Management   | AWS Secrets Manager                      | Azure Key Vault                                | Environment variables / .env     |

## 📦 Cloud Abstraction Layer

The application uses a unified storage interface that works across all providers:

```python
from green_gov_rag.cloud import StorageClient

# Automatically selects provider based on CLOUD_PROVIDER env var
storage = StorageClient()

# Same API across all providers
storage.upload_file("document.pdf", "my-container", "docs/document.pdf")
storage.download_file("my-container", "docs/document.pdf", "/tmp/doc.pdf")
storage.list_files("my-container", prefix="docs/")
```

**Supported Providers:**
- `CLOUD_PROVIDER=aws` → Uses AWS S3
- `CLOUD_PROVIDER=azure` → Uses Azure Blob Storage
- `CLOUD_PROVIDER=local` → Uses local filesystem

---

## 🚀 Deployment Instructions

### AWS Deployment (ECS Fargate)

**Prerequisites:**
- AWS CLI installed and configured
- AWS CDK installed: `npm install -g aws-cdk`
- Python 3.12+
- Valid AWS credentials

**Deployment Steps:**

```bash
cd deploy/aws

# Install CDK dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Review infrastructure changes
cdk diff

# Deploy all resources
cdk deploy

# Get deployment outputs
cdk outputs
```

**Environment Configuration:**
```bash
export CLOUD_PROVIDER=aws
export AWS_DEFAULT_REGION=ap-southeast-2
export STORAGE_CONTAINER=greengovrag-documents
```

**Resources Deployed:**
- VPC with public/private subnets across 2 AZs
- ECS Fargate cluster
- Application Load Balancer
- S3 bucket for document storage (encrypted, versioned)
- RDS PostgreSQL instance (13.7, Burstable)
- AWS Secrets Manager for API keys
- CloudWatch log groups
- IAM roles and policies

**Estimated Monthly Cost:** ~$50-100 USD (depending on usage)

---

### Azure Deployment (Container Apps)

**Prerequisites:**
- Azure CLI installed and configured
- Active Azure subscription
- Python 3.12+

**Deployment Steps:**

```bash
cd deploy/azure

# Login to Azure
az login

# Set subscription (optional)
az account set --subscription "Your-Subscription-Name"

# Run deployment script
chmod +x deploy.sh
./deploy.sh

# Or deploy manually:
RESOURCE_GROUP=greengovrag-rg
LOCATION=australiaeast

az group create --name $RESOURCE_GROUP --location $LOCATION

az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

**Environment Configuration:**
```bash
export CLOUD_PROVIDER=azure
export CLOUD_REGION=australiaeast
export STORAGE_CONTAINER=documents
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
```

**Resources Deployed:**
- Azure Container Apps environment
- Azure Container Registry (Basic tier)
- Storage Account with blob containers
- Azure Database for PostgreSQL Flexible Server (Burstable B1ms)
- Azure Key Vault for secrets
- User Assigned Managed Identity (for secure access)
- Log Analytics workspace
- Role assignments for RBAC

**Estimated Monthly Cost:** ~$40-80 USD (depending on usage)

---

### Local Deployment (Docker Compose)

**Prerequisites:**
- Docker and Docker Compose installed
- Python 3.12+ (for CLI tools)
- Optional: Portainer for container management

**Deployment Steps:**

```bash
cd deploy/docker

# Copy environment template
cp ../../.env.example .env

# Edit .env and configure for local deployment
# Set CLOUD_PROVIDER=local
# Set LOCAL_STORAGE_PATH=./data/storage

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access services:
# - Streamlit UI: http://localhost:8501
# - FastAPI: http://localhost:8000
# - PostgreSQL: localhost:5432
# - Portainer: http://localhost:9000

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

**Environment Configuration:**
```bash
export CLOUD_PROVIDER=local
export LOCAL_STORAGE_PATH=./data/storage
export DATABASE_URL=postgresql://greengovrag:greengovrag@postgres:5432/greengovrag
```

**Services:**
- Streamlit UI (port 8501)
- FastAPI backend (port 8000)
- PostgreSQL 14 (port 5432)
- Portainer CE (port 9000) - optional

**Estimated Cost:** $0 (runs on local hardware)

---

## 🔧 Post-Deployment Setup

### 1. Configure Cloud Storage

**AWS:**
```bash
# Storage is automatically configured via CDK deployment
# Bucket name available in CDK outputs
```

**Azure:**
```bash
# Get storage connection string
az storage account show-connection-string \
  --name <storage-account-name> \
  --resource-group greengovrag-rg
```

**Local:**
```bash
# Ensure directory exists and has correct permissions
mkdir -p ./data/storage
chmod 755 ./data/storage
```

### 2. Ingest Documents

```bash
# Set cloud provider
export CLOUD_PROVIDER=aws  # or azure, local

# Run document ingestion
greengovrag-cli ingest-docs --config configs/documents_config.yml

# Parse documents (PDF/HTML to text)
greengovrag-cli parse-docs --input-dir data/raw --output-dir data/processed

# Chunk documents
greengovrag-cli chunk-docs --input-dir data/processed

# Generate embeddings
greengovrag-cli embed-docs --chunked-dir data/processed/chunks

# Build vector store
greengovrag-cli build-vector-store --embedding-dir data/processed/embeddings
```

### 3. Access the Application

**AWS:**
```bash
# Get Load Balancer URL from CDK outputs
cdk outputs | grep LoadBalancerUrl
# Open: http://<load-balancer-url>
```

**Azure:**
```bash
# Get Container App URL
az containerapp show \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv
# Open: https://<container-app-url>
```

**Local:**
```
Open: http://localhost:8501
```

---

## 🔄 Multi-Cloud Migration

To migrate data between cloud providers:

```python
from green_gov_rag.cloud import StorageClient

# Source provider
source = StorageClient(provider="aws")
source_files = source.list_files("greengovrag-documents")

# Destination provider
dest = StorageClient(provider="azure")

# Migrate each file
for file_key in source_files:
    print(f"Migrating {file_key}...")

    # Download from source
    source.download_file("greengovrag-documents", file_key, f"/tmp/{file_key}")

    # Upload to destination
    dest.upload_file(f"/tmp/{file_key}", "documents", file_key)

    print(f"✅ Migrated {file_key}")
```

---

## 📊 Monitoring and Logging

### AWS CloudWatch
```bash
# View application logs
aws logs tail /ecs/greengovrag-streamlit --follow

# Get CPU utilization metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=greengovrag \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Average
```

### Azure Monitor
```bash
# View application logs
az containerapp logs show \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --follow

# View metrics
az monitor metrics list \
  --resource <container-app-id> \
  --metric-names CPUUsage,MemoryUsage
```

### Local Docker Logs
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f streamlit
docker-compose logs -f api
docker-compose logs -f postgres
```

---

## 🔒 Security Best Practices

1. **Never commit secrets to version control**
   - Use AWS Secrets Manager / Azure Key Vault
   - Use `.env` files (add to `.gitignore`)

2. **Use managed identities when possible**
   - AWS: IAM roles for ECS tasks
   - Azure: Managed Identity for Container Apps
   - Avoid hardcoded access keys

3. **Enable encryption**
   - S3: Server-side encryption (SSE-S3 or SSE-KMS)
   - Azure Blob: Encryption at rest (enabled by default)
   - RDS/PostgreSQL: Enable encryption

4. **Network security**
   - Use private subnets for databases
   - Configure security groups / NSGs
   - Enable VPC/VNet peering if needed

5. **Regular updates**
   - Keep base Docker images updated
   - Update Python dependencies regularly
   - Monitor security advisories

---

## 🧹 Cleanup

### AWS
```bash
cd deploy/aws
cdk destroy
# Confirm deletion when prompted
```

### Azure
```bash
# Delete entire resource group
az group delete --name greengovrag-rg --yes --no-wait

# Or delete specific resources
az deployment group delete --resource-group greengovrag-rg --name main
```

### Local
```bash
cd deploy/docker

# Stop and remove containers
docker-compose down

# Also remove volumes (data will be lost)
docker-compose down -v
```

---

## 📚 Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Main Project README](../README.md)

---

## 💡 Troubleshooting

### Storage Access Issues

**AWS S3:**
- Verify IAM role has `s3:GetObject`, `s3:PutObject` permissions
- Check bucket policy and CORS settings
- Ensure bucket exists in the correct region

**Azure Blob:**
- Verify Managed Identity has "Storage Blob Data Contributor" role
- Check storage account firewall rules
- Verify connection string format

**Local:**
- Check directory permissions: `chmod 755 ./data/storage`
- Ensure parent directories exist
- Verify disk space availability

### Database Connection Issues

- Verify credentials in environment variables / secrets
- Check security groups (AWS) / NSGs (Azure) allow port 5432
- Confirm database is running: `psql -h <host> -U <user> -d greengovrag`
- Check connection string format

### Container Startup Failures

1. Check logs: `docker logs <container-id>` or cloud provider logs
2. Verify all required environment variables are set
3. Ensure secrets are accessible
4. Check resource limits (CPU/memory)
5. Verify image was built correctly

---

## 🤝 Support

For deployment issues or questions, please open an issue on GitHub or consult the respective cloud provider documentation.

# Cloud Migration Guide

## Overview

GreenGovRAG supports multi-cloud deployment with unified abstraction layer for:

- **AWS** (S3, ECS Fargate, RDS)
- **Azure** (Blob Storage, Container Apps, PostgreSQL)
- **Local** (Filesystem, Docker Compose)

## Quick Start

### Storage Client Usage

```python
from green_gov_rag.cloud import StorageClient

# Auto-detect from CLOUD_PROVIDER env var
storage = StorageClient()

# Or explicitly specify
storage = StorageClient(provider="aws")  # or "azure", "local"

# Unified interface
storage.upload_file(local_path, container, key)
storage.download_file(container, key, local_path)
storage.list_files(container, prefix)
storage.delete_file(container, key)
storage.file_exists(container, key)
```

## Environment Configuration

### AWS

```bash
export CLOUD_PROVIDER=aws
export AWS_DEFAULT_REGION=ap-southeast-2
export STORAGE_CONTAINER=greengovrag-documents
# Configure: aws configure
```

### Azure

```bash
export CLOUD_PROVIDER=azure
export CLOUD_REGION=australiaeast
export STORAGE_CONTAINER=documents
export AZURE_STORAGE_CONNECTION_STRING="..."
```

### Local

```bash
export CLOUD_PROVIDER=local
export LOCAL_STORAGE_PATH=./data/storage
export STORAGE_CONTAINER=greengovrag-documents
```

## Installation

```bash
# Base
pip install -e .

# AWS support
pip install -e ".[aws]"

# Azure support
pip install -e ".[azure]"

# All providers
pip install -e ".[cloud]"
```

## Migration Scripts

### AWS to Azure

```python
from green_gov_rag.cloud import StorageClient
from pathlib import Path

aws = StorageClient(provider="aws")
azure = StorageClient(provider="azure")

files = aws.list_files("greengovrag-documents")
for file_key in files:
    temp_path = f"/tmp/{Path(file_key).name}"
    aws.download_file("greengovrag-documents", file_key, temp_path)
    azure.upload_file(temp_path, "documents", file_key)
    Path(temp_path).unlink()
```

### Local to Cloud

```python
local = StorageClient(provider="local")
cloud = StorageClient(provider="aws")  # or azure

for file_key in local.list_files("greengovrag-documents"):
    temp_path = f"/tmp/{Path(file_key).name}"
    local.download_file("greengovrag-documents", file_key, temp_path)
    cloud.upload_file(temp_path, "greengovrag-documents", file_key)
    Path(temp_path).unlink()
```

## Infrastructure Deployment

### AWS (CDK)

```bash
cd deploy/aws
pip install -r requirements.txt
cdk bootstrap
cdk deploy
```

### Azure (Bicep)

```bash
cd deploy/azure
az group create --name greengovrag-rg --location australiaeast
az deployment group create \
  --resource-group greengovrag-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

### Local (Docker Compose)

```bash
cd deploy/docker
cp .env.example .env
docker-compose up -d
```

## Code Integration

### ETL Pipeline

```python
from green_gov_rag.cloud.config import get_storage_client

def save_document(doc_path: str, doc_id: str):
    storage = get_storage_client()
    container = os.getenv("STORAGE_CONTAINER", "greengovrag-documents")
    storage.upload_file(doc_path, container, f"documents/{doc_id}.pdf")
```

### RAG Vector Store

```python
from green_gov_rag.cloud.config import get_storage_client

def save_vector_store(index_path: str):
    storage = get_storage_client()
    storage.upload_file(index_path, container, "vector_store/faiss.index")
```

## Testing

```bash
# Test local
export CLOUD_PROVIDER=local
python examples/cloud_storage_example.py

# Test AWS (requires credentials)
export CLOUD_PROVIDER=aws
python examples/cloud_storage_example.py

# Test Azure (requires connection string)
export CLOUD_PROVIDER=azure
export AZURE_STORAGE_CONNECTION_STRING="..."
python examples/cloud_storage_example.py
```

## Migration Checklist

- [ ] Update `CLOUD_PROVIDER` environment variable
- [ ] Update provider credentials
- [ ] Update `STORAGE_CONTAINER` name
- [ ] Migrate documents using migration script
- [ ] Update vector store location
- [ ] Update database connection string
- [ ] Test application
- [ ] Update monitoring/logging config
- [ ] Update IaC scripts
- [ ] Update CI/CD pipelines
- [ ] Document in runbook

## Troubleshooting

### AWS: NoCredentialsError

```bash
aws configure
# Or use environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### Azure: Connection String Required

```bash
# Get from Azure Portal → Storage Account → Access Keys
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
```

### Local: Permission Denied

```bash
chmod 755 ./data/storage
```

## Performance Tips

**AWS S3:**
- Use Transfer Acceleration for large files
- Enable multipart upload for files >100MB
- Use VPC endpoints for private access

**Azure Blob:**
- Use Azure CDN for frequent access
- Enable lifecycle management
- Use private endpoints

**Local:**
- Use SSD storage
- Implement file watching for sync
- Consider NFS/SMB for shared access

## Security Best Practices

1. **Never hardcode credentials** - Use env vars or secret managers
2. **Encrypt at rest** - S3 SSE-KMS, Azure default encryption
3. **Encrypt in transit** - Always HTTPS/TLS
4. **Access controls** - IAM policies, RBAC, file permissions

## See Also

- [Cloud Provider Comparison](./CLOUD_PROVIDER_COMPARISON.md) - Choose your provider
- [Data Sources](./DATA.md) - Data sovereignty considerations
- [Project Structure](./PROJECT.md) - Repository organization

# Cloud-Agnostic Migration Guide

This document describes the cloud abstraction layer implemented in GreenGovRAG and how to migrate between cloud providers.

## Overview

GreenGovRAG now supports **multi-cloud deployment** with a unified abstraction layer that allows seamless migration between:

- **AWS** (S3, ECS Fargate, RDS)
- **Azure** (Blob Storage, Container Apps, PostgreSQL)
- **Local** (Filesystem, Docker Compose)

## Architecture

### Storage Abstraction Layer

The core abstraction is the `StorageClient` class located in `green_gov_rag/cloud/storage.py`:

```python
from green_gov_rag.cloud import StorageClient

# Automatically detects provider from CLOUD_PROVIDER env var
storage = StorageClient()

# Or explicitly specify
storage = StorageClient(provider="aws")  # or "azure", "local"
```

### Supported Operations

All storage backends support the same interface:

| Operation | Description |
|-----------|-------------|
| `upload_file(local_path, container, key)` | Upload a file |
| `download_file(container, key, local_path)` | Download a file |
| `upload_fileobj(fileobj, container, key)` | Upload from file-like object |
| `download_fileobj(container, key, fileobj)` | Download to file-like object |
| `list_files(container, prefix)` | List files with prefix |
| `delete_file(container, key)` | Delete a file |
| `file_exists(container, key)` | Check if file exists |

## Environment Configuration

### AWS Configuration

```bash
export CLOUD_PROVIDER=aws
export AWS_DEFAULT_REGION=ap-southeast-2
export STORAGE_CONTAINER=greengovrag-documents

# AWS credentials via CLI or IAM role
# aws configure
```

### Azure Configuration

```bash
export CLOUD_PROVIDER=azure
export CLOUD_REGION=australiaeast
export STORAGE_CONTAINER=documents
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
```

### Local Configuration

```bash
export CLOUD_PROVIDER=local
export LOCAL_STORAGE_PATH=./data/storage
export STORAGE_CONTAINER=greengovrag-documents
```

## Installation

### Base Installation

```bash
pip install -e .
```

### With AWS Support

```bash
pip install -e ".[aws]"
```

### With Azure Support

```bash
pip install -e ".[azure]"
```

### With All Cloud Providers

```bash
pip install -e ".[cloud]"
```

## Migration Examples

### 1. AWS to Azure Migration

```python
from green_gov_rag.cloud import StorageClient
from pathlib import Path

# Connect to both providers
aws = StorageClient(provider="aws")
azure = StorageClient(provider="azure")

# List all files in AWS
files = aws.list_files("greengovrag-documents")

# Migrate each file
for file_key in files:
    print(f"Migrating {file_key}...")

    # Download from AWS
    temp_path = f"/tmp/{Path(file_key).name}"
    aws.download_file("greengovrag-documents", file_key, temp_path)

    # Upload to Azure
    azure.upload_file(temp_path, "documents", file_key)

    # Cleanup
    Path(temp_path).unlink()

    print(f"✅ Migrated {file_key}")
```

### 2. Local to Cloud Migration

```python
from green_gov_rag.cloud import StorageClient

# Source: Local
local = StorageClient(provider="local")

# Destination: AWS
aws = StorageClient(provider="aws")

# Migrate all documents
local_files = local.list_files("greengovrag-documents")

for file_key in local_files:
    # Download from local storage
    temp_path = f"/tmp/{Path(file_key).name}"
    local.download_file("greengovrag-documents", file_key, temp_path)

    # Upload to AWS
    aws.upload_file(temp_path, "greengovrag-documents", file_key)

    Path(temp_path).unlink()
```

### 3. Cloud to Local (for backup)

```python
from green_gov_rag.cloud import StorageClient

# Source: Azure
azure = StorageClient(provider="azure")

# Destination: Local
local = StorageClient(provider="local")

# Backup all files
files = azure.list_files("documents")

for file_key in files:
    # Download from Azure
    temp_path = f"/tmp/{Path(file_key).name}"
    azure.download_file("documents", file_key, temp_path)

    # Save to local storage
    local.upload_file(temp_path, "backup", file_key)

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

See `deploy/aws/greengovrag_stack.py` for details.

### Azure (Bicep)

```bash
cd deploy/azure
./deploy.sh
```

Or manually:

```bash
az group create --name greengovrag-rg --location australiaeast
az deployment group create \
  --resource-group greengovrag-rg \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

See `deploy/azure/main.bicep` for details.

### Local (Docker Compose)

```bash
cd deploy/docker
docker-compose up -d
```

See `deploy/docker/docker-compose.yml` for details.

## Code Integration Examples

### ETL Pipeline Integration

```python
# green_gov_rag/etl/ingest.py

from green_gov_rag.cloud.config import get_storage_client

def save_document(doc_path: str, doc_id: str):
    """Save document to cloud storage."""
    storage = get_storage_client()
    container = os.getenv("STORAGE_CONTAINER", "greengovrag-documents")

    # Upload document
    storage.upload_file(
        local_path=doc_path,
        container=container,
        key=f"documents/{doc_id}.pdf"
    )
```

### RAG Integration

```python
# green_gov_rag/rag/vector_store.py

from green_gov_rag.cloud.config import get_storage_client

def save_vector_store(index_path: str):
    """Save FAISS index to cloud storage."""
    storage = get_storage_client()
    container = os.getenv("STORAGE_CONTAINER", "greengovrag-documents")

    # Upload index files
    storage.upload_file(index_path, container, "vector_store/faiss.index")
```

## Testing

### Unit Tests

```python
# tests/test_cloud_storage.py

import pytest
from green_gov_rag.cloud import StorageClient

def test_local_storage():
    """Test local storage backend."""
    storage = StorageClient(provider="local")

    # Upload test file
    storage.upload_file("test.txt", "test-container", "test.txt")

    # Verify exists
    assert storage.file_exists("test-container", "test.txt")

    # Cleanup
    storage.delete_file("test-container", "test.txt")
```

### Integration Tests

Run the example script:

```bash
# Test with local storage
export CLOUD_PROVIDER=local
python examples/cloud_storage_example.py

# Test with AWS (requires credentials)
export CLOUD_PROVIDER=aws
python examples/cloud_storage_example.py

# Test with Azure (requires connection string)
export CLOUD_PROVIDER=azure
export AZURE_STORAGE_CONNECTION_STRING="..."
python examples/cloud_storage_example.py
```

## Migration Checklist

When migrating between cloud providers:

- [ ] Update `CLOUD_PROVIDER` environment variable
- [ ] Update provider-specific credentials (AWS keys, Azure connection string)
- [ ] Update `STORAGE_CONTAINER` to match new container/bucket name
- [ ] Migrate existing documents using migration script
- [ ] Update vector store location
- [ ] Update database connection string
- [ ] Test application with new provider
- [ ] Update monitoring and logging configuration
- [ ] Update deployment scripts (IaC)
- [ ] Update CI/CD pipelines
- [ ] Document migration in runbook

## Troubleshooting

### AWS Issues

**Problem:** `NoCredentialsError: Unable to locate credentials`

**Solution:**
```bash
# Configure AWS CLI
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### Azure Issues

**Problem:** `ValueError: AZURE_STORAGE_CONNECTION_STRING environment variable is required`

**Solution:**
```bash
# Get connection string from Azure Portal
# Storage Account -> Access Keys -> Connection String
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
```

### Local Issues

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Fix directory permissions
chmod 755 ./data/storage
```

## Performance Considerations

### AWS S3
- Use S3 Transfer Acceleration for large files
- Enable multipart upload for files > 100MB
- Use VPC endpoints for private access

### Azure Blob Storage
- Use Azure CDN for frequently accessed files
- Enable lifecycle management for archival
- Use private endpoints for secure access

### Local Storage
- Use SSD storage for better performance
- Implement file watching for real-time sync
- Consider using NFS/SMB for shared access

## Security Best Practices

1. **Never hardcode credentials**
   - Use environment variables
   - Use cloud provider secret managers
   - Use managed identities when possible

2. **Encrypt data at rest**
   - AWS: Enable S3 encryption (SSE-S3 or SSE-KMS)
   - Azure: Encryption enabled by default
   - Local: Use encrypted filesystems

3. **Encrypt data in transit**
   - Always use HTTPS/TLS
   - Verify SSL certificates
   - Use VPN for local deployments

4. **Implement access controls**
   - AWS: Use IAM policies and bucket policies
   - Azure: Use RBAC and SAS tokens
   - Local: Use file permissions

## Future Enhancements

Potential additions to the cloud abstraction layer:

- [ ] GCP support (Google Cloud Storage)
- [ ] MinIO support (self-hosted S3-compatible)
- [ ] Secrets management abstraction
- [ ] Database abstraction (RDS, Azure SQL, PostgreSQL)
- [ ] Monitoring abstraction
- [ ] Logging abstraction
- [ ] Queue/messaging abstraction (SQS, Azure Queue, RabbitMQ)
- [ ] Caching abstraction (ElastiCache, Azure Cache, Redis)

## References

- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Azure SDK for Python](https://learn.microsoft.com/en-us/azure/developer/python/sdk/)
- [Cloud Design Patterns](https://learn.microsoft.com/en-us/azure/architecture/patterns/)
- [12-Factor App](https://12factor.net/)

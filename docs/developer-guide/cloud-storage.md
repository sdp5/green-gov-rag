# Cloud Storage Guide

## Overview

GreenGovRAG supports multi-cloud storage for the ETL pipeline, enabling seamless operation across:

- **AWS S3** - Production-grade object storage with global availability
- **Azure Blob Storage** - Microsoft Azure's object storage service
- **Local Filesystem** - For development and testing

The cloud storage abstraction layer provides a unified interface across all providers, making it easy to switch between them or migrate data.

## Table of Contents

1. [Architecture](#architecture)
2. [Providers](#providers)
3. [Configuration](#configuration)
4. [ETL Storage Adapter](#etl-storage-adapter)
5. [Usage Examples](#usage-examples)
6. [Airflow Integration](#airflow-integration)
7. [Database Integration](#database-integration)
8. [Migration Guide](#migration-guide)
9. [AWS Deep Dive](#aws-deep-dive)
10. [Azure Deep Dive](#azure-deep-dive)
11. [Troubleshooting](#troubleshooting)
12. [Performance Considerations](#performance-considerations)

## Architecture

### Storage Path Structure

All storage backends use a consistent hierarchical path structure:

```
{container}/
├── documents/
│   └── {jurisdiction}/
│       └── {category}/
│           └── {topic}/
│               └── {filename}
├── metadata/
│   └── {jurisdiction}/
│       └── {category}/
│           └── {topic}/
│               └── {filename}.json
└── chunks/
    └── {document_id}/
        └── {chunk_index}.json
```

**Example**:
```
greengovrag-documents/
├── documents/federal/environment/emissions/nger-guidelines.pdf
├── metadata/federal/environment/emissions/nger-guidelines.pdf.json
└── chunks/abc123def456/000001.json
```

### Components

1. **Storage Adapter** (`green_gov_rag/etl/storage_adapter.py`)
   - Cloud-agnostic interface for ETL operations
   - Handles downloads, uploads, metadata management
   - Automatic provider detection

2. **Cloud Storage Backend** (`green_gov_rag/cloud/storage.py`)
   - Low-level storage operations
   - Provider-specific implementations (AWS, Azure, Local)
   - Connection pooling and retry logic

3. **ETL Modules** (Cloud-aware)
   - `ingest.py` - Downloads documents to cloud/local storage
   - `pipeline.py` - Processes documents from storage
   - `loader.py` - Loads documents and chunks from storage
   - `db_writer.py` - Tracks storage paths in database

4. **Airflow DAGs**
   - `greengovrag_pipeline_cloud.py` - Cloud-aware workflow orchestration
   - `greengovrag_s3_sensor` - AWS S3 monitoring (auto-trigger)
   - `greengovrag_azure_sensor` - Azure Blob monitoring (auto-trigger)

## Providers

### AWS S3

**Use Cases:**
- Production deployments requiring high availability
- Global document distribution via CloudFront
- Integration with AWS services (ECS, Lambda, RDS)
- Cost-effective storage with lifecycle policies

**Pricing**: ~$0.023/GB/month (Standard tier)

### Azure Blob Storage

**Use Cases:**
- Azure-native deployments (Container Apps, AKS)
- Integration with Azure services (Functions, Cosmos DB)
- Hybrid cloud scenarios with on-premises Azure Stack
- Australian data residency requirements (australiaeast region)

**Pricing**: ~$0.02/GB/month (Hot tier)

### Local Filesystem

**Use Cases:**
- Development and testing
- Air-gapped or offline deployments
- Single-server deployments
- Data privacy constraints

**Pricing**: Storage hardware costs only

See [Cloud Provider Comparison](../.local/cloud-comparison.md) for detailed comparison matrix.

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Provider Selection
CLOUD_PROVIDER=aws              # Options: local, aws, azure
STORAGE_CONTAINER=greengovrag-documents
LOCAL_STORAGE_PATH=./data/storage

# AWS S3 Configuration (if CLOUD_PROVIDER=aws)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1            # or ap-southeast-2 for Sydney

# Azure Blob Storage Configuration (if CLOUD_PROVIDER=azure)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net

# Optional: Cloud Region Override
CLOUD_REGION=us-east-1          # or australiaeast for Azure
```

### Validation

The configuration is automatically validated on startup. To skip validation during development:

```bash
DEBUG=true  # Skips credential validation
```

### Installation

```bash
# Base installation
pip install -e .

# AWS support
pip install -e ".[aws]"

# Azure support
pip install -e ".[azure]"

# All cloud providers
pip install -e ".[cloud]"
```

## ETL Storage Adapter

The `ETLStorageAdapter` provides a high-level, cloud-agnostic interface for ETL operations.

### Basic Usage

```python
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

# Initialize (auto-detects provider from settings)
adapter = ETLStorageAdapter()

# Or specify provider explicitly
adapter = ETLStorageAdapter(provider='aws', container='my-bucket')

# Get storage info
info = adapter.get_storage_info()
print(info)
# {'provider': 'aws', 'container': 'greengovrag-documents', 'backend_type': 'AWSBackend'}
```

### Document Operations

#### Download from URL

```python
# Download and store document
metadata = {
    "title": "NGER Guidelines 2024",
    "jurisdiction": "federal",
    "category": "environment",
    "topic": "emissions_reporting",
    "source_url": "https://example.com/nger-guidelines.pdf"
}

doc_id = adapter.download_from_url(
    "https://example.com/nger-guidelines.pdf",
    metadata=metadata,
    retries=3  # Optional: retry attempts
)

print(f"Document ID: {doc_id}")
```

#### Save Document Content

```python
# Save document content directly
with open("local_file.pdf", "rb") as f:
    content = f.read()

doc_id = adapter.save_document(
    content=content,
    metadata={
        "title": "Climate Policy",
        "jurisdiction": "state",
        "category": "policy",
        "topic": "climate",
        "filename": "climate-policy.pdf"
    }
)
```

#### Load Document

```python
# Load document content and metadata
metadata = adapter.load_metadata(doc_id)
content = adapter.load_document(doc_id, metadata)

# Save locally if needed
with open("downloaded.pdf", "wb") as f:
    f.write(content)
```

### Chunk Operations

#### Save Chunks

```python
# Process and save chunks
from green_gov_rag.etl.chunker import TextChunker

chunker = TextChunker(chunk_size=1000, chunk_overlap=100)
text = content.decode('utf-8')  # Assuming text content
chunks = chunker.chunk_text(text)

# Format chunks
chunk_dicts = [
    {
        "content": chunk,
        "metadata": {
            "chunk_id": i,
            "document_id": doc_id,
            "page_number": None,
        }
    }
    for i, chunk in enumerate(chunks)
]

# Save to storage
adapter.save_chunks(chunk_dicts, doc_id)
```

#### Load Chunks

```python
# Load all chunks for a document
chunks = adapter.load_chunks(doc_id)

print(f"Loaded {len(chunks)} chunks")
for chunk in chunks[:3]:
    print(chunk['content'][:100])
```

### List and Filter Documents

```python
# List all documents
all_docs = adapter.list_documents()

# Filter by jurisdiction
federal_docs = adapter.list_documents(jurisdiction="federal")

# Filter by category and topic
env_docs = adapter.list_documents(
    jurisdiction="federal",
    category="environment",
    topic="emissions_reporting"
)

for doc in env_docs:
    print(f"{doc['title']} - {doc['document_id']}")
```

## Usage Examples

### Example 1: Ingest Documents to Cloud

```python
from green_gov_rag.etl.ingest import ingest_documents

# Ingest documents (auto-detects cloud from settings)
document_ids = ingest_documents(
    config_path="configs/documents_config.yml"
)

# Or explicitly use cloud storage
document_ids = ingest_documents(
    use_cloud=True,
    config_path="configs/documents_config.yml"
)

print(f"Ingested {len(document_ids)} documents to cloud storage")
```

### Example 2: Process Documents from Cloud

```python
from green_gov_rag.etl.pipeline import EnhancedETLPipeline

# Initialize cloud-aware pipeline
pipeline = EnhancedETLPipeline(
    use_cloud=True,
    enable_auto_tagging=True,
    chunk_size=1000,
    chunk_overlap=100
)

# Process documents
chunks = pipeline.run(
    config_path="configs/documents_config.yml",
    document_ids=document_ids  # From ingestion step
)

print(f"Processed {len(chunks)} chunks")
```

### Example 3: Load Documents from Storage

```python
from green_gov_rag.etl.loader import (
    load_documents_from_storage,
    get_document_content_from_storage,
    get_document_chunks_from_storage
)

# List documents
docs = load_documents_from_storage(jurisdiction="federal")

# Load specific document
doc_id = docs[0]['document_id']
content, metadata = get_document_content_from_storage(doc_id)

# Load chunks
chunks = get_document_chunks_from_storage(doc_id)
```

### Example 4: Sync to Database

```python
from green_gov_rag.etl.db_writer import (
    save_document_from_storage_metadata,
    save_chunks_from_storage
)
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

adapter = ETLStorageAdapter()

# Load and sync document metadata
metadata = adapter.load_metadata(doc_id)
db_doc = save_document_from_storage_metadata(metadata)

# Load and sync chunks
chunks = adapter.load_chunks(doc_id)
db_chunks = save_chunks_from_storage(doc_id, chunks)

print(f"Synced document and {len(db_chunks)} chunks to database")
```

## Airflow Integration

### Using the Cloud-Aware DAG

1. **Set Airflow Variables** (optional, overrides .env):

```python
# Via Airflow UI or CLI
airflow variables set STORAGE_PROVIDER aws
airflow variables set STORAGE_CONTAINER greengovrag-docs
airflow variables set ENABLE_AUTO_TAGGING true
airflow variables set CHUNK_SIZE 1000
```

2. **Trigger the DAG**:

```bash
# Trigger manually
airflow dags trigger greengovrag_cloud_pipeline

# Or with custom params
airflow dags trigger greengovrag_cloud_pipeline \
  --conf '{"storage_provider": "azure", "chunk_size": 1500}'
```

3. **Monitor Progress**:

```bash
# View DAG runs
airflow dags list-runs -d greengovrag_cloud_pipeline

# View task logs
airflow tasks logs greengovrag_cloud_pipeline process_documents <execution_date>
```

### Task Flow

The cloud-aware DAG executes these tasks in sequence:

1. **ingest_documents** - Downloads documents to cloud storage
2. **sync_metadata_to_db** - Syncs metadata to PostgreSQL
3. **process_documents** - Parses, chunks, and tags documents
4. **sync_chunks_to_db** - Syncs chunks to database
5. **build_vector_store** - Creates embeddings and vector store
6. **validate_pipeline** - Runs test query for validation

### Cloud Storage Sensors

For automatic processing when new documents arrive, the DAG includes sensor support for both AWS S3 and Azure Blob Storage.

**How Sensors Work:**
1. Sensor DAG polls cloud storage every 60 seconds (configurable)
2. Looks for `trigger.json` files matching pattern `documents/*/trigger.json`
3. When detected, automatically triggers the main ETL pipeline via `TriggerDagRunOperator`
4. Pipeline processes all new documents in the container
5. Sensor continues monitoring for future triggers

**Sensor DAGs:**
- `greengovrag_s3_sensor` - AWS S3 monitoring (active when STORAGE_PROVIDER=aws)
- `greengovrag_azure_sensor` - Azure Blob monitoring (active when STORAGE_PROVIDER=azure)

## Database Integration

### Storage Metadata in Database

Documents and chunks now track their storage location:

```python
from green_gov_rag.etl.db_writer import get_document_by_id

# Get document from database
doc = get_document_by_id(doc_id)

# Check storage info
print(doc.metadata_)
# {
#   'storage_provider': 'aws',
#   'storage_mode': 'cloud',
#   'storage_path': 'documents/federal/environment/emissions/nger.pdf',
#   'sha256': 'abc123...',
#   ...
# }
```

### Query Documents by Storage

```python
from sqlmodel import Session, select
from green_gov_rag.models import Document

with Session(engine) as session:
    # Find all cloud-stored documents
    statement = select(Document).where(
        Document.metadata_['storage_mode'].astext == 'cloud'
    )
    cloud_docs = session.exec(statement).all()

    # Find AWS-specific documents
    statement = select(Document).where(
        Document.metadata_['storage_provider'].astext == 'aws'
    )
    aws_docs = session.exec(statement).all()
```

## Migration Guide

### Migrating from Local to Cloud

1. **Set up cloud credentials** in `.env`

2. **Upload existing documents**:

```python
from pathlib import Path
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

adapter = ETLStorageAdapter(provider='aws')

# Upload local files
for doc_file in Path('data/raw').rglob('*.pdf'):
    with open(doc_file, 'rb') as f:
        adapter.save_document(
            content=f.read(),
            metadata={
                'title': doc_file.stem,
                'jurisdiction': 'federal',  # Update as needed
                'category': 'misc',
                'topic': 'general',
                'filename': doc_file.name
            }
        )
```

3. **Update configuration**:

```bash
# Change from local to cloud
CLOUD_PROVIDER=aws  # Was: local
```

4. **Verify migration**:

```python
# List cloud documents
docs = adapter.list_documents()
print(f"Migrated {len(docs)} documents")
```

### Migrating from Cloud to Cloud (AWS → Azure)

```python
# 1. Initialize both adapters
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

aws_adapter = ETLStorageAdapter(provider='aws')
azure_adapter = ETLStorageAdapter(provider='azure')

# 2. List documents in AWS
docs = aws_adapter.list_documents()

# 3. Copy each document
for doc_meta in docs:
    doc_id = doc_meta['document_id']

    # Load from AWS
    content = aws_adapter.load_document(doc_id, doc_meta)

    # Save to Azure
    azure_adapter.save_document(content, doc_meta)

    # Copy chunks
    chunks = aws_adapter.load_chunks(doc_id)
    azure_adapter.save_chunks(chunks, doc_id)

# 4. Update configuration
# CLOUD_PROVIDER=azure
```

### Migration Checklist

- [ ] Update `CLOUD_PROVIDER` environment variable
- [ ] Update provider credentials (AWS keys or Azure connection string)
- [ ] Update `STORAGE_CONTAINER` name
- [ ] Migrate documents using migration script
- [ ] Migrate chunks
- [ ] Update vector store location
- [ ] Update database connection string (if changing cloud provider)
- [ ] Test application with sample queries
- [ ] Update monitoring/logging config
- [ ] Update IaC scripts (CDK, Bicep, etc.)
- [ ] Update CI/CD pipelines
- [ ] Document in runbook

## AWS Deep Dive

### AWS S3 Setup

#### 1. Create S3 Bucket

```bash
# Create bucket
aws s3 mb s3://greengovrag-documents --region us-east-1

# Enable versioning (optional, for document history)
aws s3api put-bucket-versioning \
  --bucket greengovrag-documents \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket greengovrag-documents \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

#### 2. Configure IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::greengovrag-documents/*",
        "arn:aws:s3:::greengovrag-documents"
      ]
    }
  ]
}
```

#### 3. S3 Sensor Configuration

```bash
# Set up AWS connection in Airflow
airflow connections add aws_default \
  --conn-type aws \
  --conn-login YOUR_ACCESS_KEY \
  --conn-password YOUR_SECRET_KEY \
  --conn-extra '{"region_name": "us-east-1"}'
```

#### 4. Trigger Processing

```bash
# Create trigger file
echo '{"trigger": true, "source": "manual"}' > trigger.json

# Upload to S3 to trigger processing
aws s3 cp trigger.json s3://greengovrag-documents/documents/federal/trigger.json

# Monitor sensor
airflow tasks logs greengovrag_s3_sensor wait_for_new_documents <date>
```

### AWS Best Practices

1. **Lifecycle Policies**: Archive old documents to Glacier
   ```bash
   aws s3api put-bucket-lifecycle-configuration \
     --bucket greengovrag-documents \
     --lifecycle-configuration file://lifecycle.json
   ```

2. **Transfer Acceleration**: Enable for faster uploads
   ```bash
   aws s3api put-bucket-accelerate-configuration \
     --bucket greengovrag-documents \
     --accelerate-configuration Status=Enabled
   ```

3. **VPC Endpoints**: Use for private access from ECS/EC2
4. **CloudWatch Metrics**: Monitor bucket operations
5. **Cost Optimization**: Use Intelligent-Tiering for variable access patterns

## Azure Deep Dive

### Azure Blob Storage Setup

#### 1. Create Storage Account

```bash
# Create resource group
az group create \
  --name greengovrag-rg \
  --location eastus

# Create storage account
az storage account create \
  --name greengovragstorage \
  --resource-group greengovrag-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Get connection string
az storage account show-connection-string \
  --name greengovragstorage \
  --resource-group greengovrag-rg \
  --output tsv
```

#### 2. Create Blob Container

```bash
# Set connection string
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# Create container
az storage container create \
  --name greengovrag-documents \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Enable soft delete for recovery
az storage blob service-properties delete-policy update \
  --enable true \
  --days-retained 7 \
  --account-name greengovragstorage
```

#### 3. Airflow Connection Setup

**Option 1: Connection String (Recommended)**

```bash
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
  }'
```

**Option 2: SAS Token**

```bash
# Generate SAS token (valid for 1 year)
az storage container generate-sas \
  --name greengovrag-documents \
  --permissions racwdl \
  --expiry 2025-12-31T23:59:59Z \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Add to Airflow
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "sas_token": "sv=2021-06-08&ss=bfqt&srt=sco&sp=rwdlacupiytfx&..."
  }'
```

**Option 3: Managed Identity (Azure VMs)**

```bash
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "use_managed_identity": true,
    "storage_account_name": "greengovragstorage"
  }'
```

#### 4. Azure Sensor Configuration

```bash
# Trigger processing by uploading trigger file
echo '{"trigger": true, "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > trigger.json

az storage blob upload \
  -f trigger.json \
  -c greengovrag-documents \
  -n documents/federal/trigger.json \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Monitor sensor
airflow tasks logs greengovrag_azure_sensor wait_for_new_documents <date>
```

### Azure Best Practices

1. **Access Tiers**: Use appropriate storage tier
   - **Hot**: Frequently accessed data
   - **Cool**: Infrequently accessed (30+ days)
   - **Archive**: Rarely accessed (180+ days)

2. **Azure CDN**: Enable for global document delivery
   ```bash
   az cdn endpoint create \
     --resource-group greengovrag-rg \
     --name greengovrag-cdn \
     --profile-name greengovrag-profile \
     --origin greengovragstorage.blob.core.windows.net
   ```

3. **Private Endpoints**: Use for production security
4. **Azure Monitor**: Enable logging and metrics
5. **Data Residency**: Use australiaeast region for Australian data

### Azure CLI Operations

```bash
# Upload document
az storage blob upload \
  -f local-document.pdf \
  -c greengovrag-documents \
  -n documents/federal/environment/climate/policy-2024.pdf \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# List blobs
az storage blob list \
  -c greengovrag-documents \
  --prefix documents/federal/ \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Download document
az storage blob download \
  -c greengovrag-documents \
  -n documents/federal/environment/climate/policy-2024.pdf \
  -f downloaded-policy.pdf \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

## Troubleshooting

### Common Issues

#### 1. Credentials Not Found

**AWS Error**: `ValueError: AWS_ACCESS_KEY_ID is required when CLOUD_PROVIDER is 'aws'`

**Solution**: Add credentials to `.env`:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

Or skip validation during development:
```bash
DEBUG=true
```

**Azure Error**: `ValueError: AZURE_STORAGE_CONNECTION_STRING is required when CLOUD_PROVIDER is 'azure'`

**Solution**: Add connection string to `.env`:
```bash
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."
```

#### 2. Container/Bucket Not Found

**AWS Error**: `botocore.exceptions.NoSuchBucket: The specified bucket does not exist`

**Solution**: Create the bucket first:
```bash
aws s3 mb s3://greengovrag-documents
```

**Azure Error**: `ResourceNotFoundError: The specified container does not exist`

**Solution**: Create the container:
```bash
az storage container create -n greengovrag-documents \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

#### 3. Permission Denied

**AWS Error**: `botocore.exceptions.ClientError: Access Denied`

**Solution**: Ensure IAM policy includes required permissions (see AWS Deep Dive)

**Azure Error**: `AuthorizationPermissionMismatch`

**Solution**: Check SAS token permissions or connection string validity:
```bash
# Verify connection string
echo $AZURE_STORAGE_CONNECTION_STRING

# Test connection
az storage container list --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

#### 4. Documents Not Found After Migration

**Issue**: Documents uploaded to cloud but not appearing in queries

**Solution**: Check the storage path structure:
```python
# Verify document path
metadata = adapter.load_metadata(doc_id)
print(metadata.get('storage_path'))

# Should be: documents/{jurisdiction}/{category}/{topic}/{filename}
```

#### 5. Sensor Not Triggering

**Issue**: Airflow sensor not detecting trigger files

**Solution**:
```bash
# Check sensor logs
airflow tasks logs greengovrag_s3_sensor wait_for_new_documents <date>

# Verify trigger file exists (AWS)
aws s3 ls s3://greengovrag-documents/documents/federal/trigger.json

# Verify trigger file exists (Azure)
az storage blob exists \
  -c greengovrag-documents \
  -n documents/federal/trigger.json \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

### Debug Mode

Enable detailed logging:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Run operations with debug output
adapter = ETLStorageAdapter()
docs = adapter.list_documents()  # Will show detailed logs
```

### Testing Cloud Storage

Test connectivity without processing documents:

```python
from green_gov_rag.cloud.storage import StorageClient

# Test AWS
client = StorageClient(provider='aws')
print(client.backend.file_exists('greengovrag-documents', 'test.txt'))

# Test Azure
client = StorageClient(provider='azure')
files = client.backend.list_files('greengovrag-documents', prefix='documents/')
print(f"Found {len(files)} files")
```

## Performance Considerations

### Best Practices

1. **Batch Operations**: Upload/download multiple files in parallel
   ```python
   from concurrent.futures import ThreadPoolExecutor

   def upload_doc(doc_path):
       adapter.save_document(...)

   with ThreadPoolExecutor(max_workers=10) as executor:
       executor.map(upload_doc, doc_paths)
   ```

2. **Chunk Size**: Optimize based on provider
   - **AWS S3**: 5 MB multipart threshold
   - **Azure Blob**: 4 MB block size

3. **Caching**: Use local cache for frequently accessed documents
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def get_cached_document(doc_id):
       return adapter.load_document(doc_id, metadata)
   ```

4. **Region Selection**: Choose cloud regions close to your compute
   ```bash
   # AWS
   AWS_REGION=us-east-1  # Match your ECS region

   # Azure
   CLOUD_REGION=eastus  # Match your Container Apps region
   ```

### Provider-Specific Optimizations

**AWS S3:**
- Use Transfer Acceleration for large files (>100MB)
- Enable multipart upload for files >100MB
- Use VPC endpoints for private access from ECS/EC2
- Consider S3 Intelligent-Tiering for variable access patterns

**Azure Blob:**
- Use block size of 4MB for optimal throughput
- Enable Azure CDN for frequent access
- Use private endpoints for production
- Consider lifecycle management for archival

**Local:**
- Use SSD storage for better performance
- Implement file watching for real-time sync
- Consider NFS/SMB for shared access across services

## Security Best Practices

1. **Never hardcode credentials** - Use environment variables or secret managers
2. **Encrypt at rest** - S3 SSE-KMS, Azure default encryption enabled
3. **Encrypt in transit** - Always use HTTPS/TLS
4. **Access controls** - IAM policies (AWS), RBAC (Azure), file permissions (Local)
5. **Rotate credentials** - Regular rotation of access keys and SAS tokens
6. **Audit logging** - Enable CloudTrail (AWS) or Azure Monitor logs

### AWS Security

```bash
# Enable bucket logging
aws s3api put-bucket-logging \
  --bucket greengovrag-documents \
  --bucket-logging-status file://logging.json

# Block public access
aws s3api put-public-access-block \
  --bucket greengovrag-documents \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

### Azure Security

```bash
# Enable logging
az storage logging update \
  --log rwd \
  --retention 90 \
  --services b \
  --account-name greengovragstorage

# Disable public access
az storage account update \
  --name greengovragstorage \
  --resource-group greengovrag-rg \
  --allow-blob-public-access false
```

## Dependencies

### Required Python Packages

```bash
# Base
pip install requests

# AWS support
pip install boto3>=1.28.0

# Azure support
pip install azure-storage-blob>=12.19.0

# All providers
pip install boto3 azure-storage-blob
```

### Airflow Providers

```bash
# AWS
pip install apache-airflow-providers-amazon>=8.0.0

# Azure
pip install apache-airflow-providers-microsoft-azure>=8.4.0
```

## See Also

- [Cloud Provider Comparison](../.local/cloud-comparison.md) - Choose your provider
- [Data Sources Reference](../reference/data-sources.md) - Data sovereignty considerations
- [AWS Deployment Guide](../deployment/aws.md) - Deploy on AWS
- [Azure Deployment Guide](../deployment/azure.md) - Deploy on Azure
- [Local Docker Setup](../deployment/local-docker.md) - Development environment

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/sdp5/green-gov-rag/issues
- **Documentation**: https://green-gov-rag.github.io
- **Contact**: contact@sundeep.id.au

# Cloud Storage Integration Guide

## Overview

GreenGovRAG now supports cloud storage (AWS S3, Azure Blob Storage) in addition to local filesystem storage. This guide explains how to configure and use cloud storage across the ETL pipeline.

## Table of Contents

1. [Architecture](#architecture)
2. [Configuration](#configuration)
3. [ETL Storage Adapter](#etl-storage-adapter)
4. [Usage Examples](#usage-examples)
5. [Airflow Integration](#airflow-integration)
6. [Database Integration](#database-integration)
7. [Migration Guide](#migration-guide)
8. [Troubleshooting](#troubleshooting)

## Architecture

### Storage Path Structure

All storage backends use a consistent path structure:

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

### Components

1. **Storage Adapter** (`green_gov_rag/etl/storage_adapter.py`)
   - Cloud-agnostic interface for ETL operations
   - Handles downloads, uploads, metadata management

2. **Cloud Storage Backend** (`green_gov_rag/cloud/storage.py`)
   - Low-level storage operations
   - Provider-specific implementations (AWS, Azure, Local)

3. **ETL Modules** (Updated)
   - `ingest.py` - Downloads documents to cloud/local storage
   - `pipeline.py` - Processes documents from storage
   - `loader.py` - Loads documents and chunks from storage
   - `db_writer.py` - Tracks storage paths in database

4. **Airflow DAG** (`greengovrag_pipeline_cloud.py`)
   - Cloud-aware workflow orchestration
   - Distributed processing support
   - Cloud storage sensors

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Storage Provider Selection
CLOUD_PROVIDER=aws              # Options: local, aws, azure
STORAGE_CONTAINER=greengovrag-documents
LOCAL_STORAGE_PATH=./data/storage

# AWS S3 Configuration (if CLOUD_PROVIDER=aws)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Azure Blob Storage Configuration (if CLOUD_PROVIDER=azure)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Optional: Cloud Region Override
CLOUD_REGION=us-east-1
```

### Validation

The configuration is automatically validated on startup. To skip validation during development:

```bash
DEBUG=true  # Skips credential validation
```

## ETL Storage Adapter

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

#### AWS S3 Sensor

The S3 sensor monitors for trigger files:

```bash
# Create trigger file
echo '{"trigger": true, "source": "manual"}' > trigger.json

# Upload to S3 to trigger processing
aws s3 cp trigger.json s3://greengovrag-documents/documents/federal/trigger.json

# Monitor sensor
airflow tasks logs greengovrag_s3_sensor wait_for_new_documents <date>
```

**Configuration:**
```bash
# Set up AWS connection in Airflow
airflow connections add aws_default \
  --conn-type aws \
  --conn-login YOUR_ACCESS_KEY \
  --conn-password YOUR_SECRET_KEY \
  --conn-extra '{"region_name": "us-east-1"}'
```

#### Azure Blob Storage Sensor

The Azure sensor monitors Blob Storage for trigger files:

```bash
# Create trigger file
echo '{"trigger": true, "source": "manual"}' > trigger.json

# Upload to Azure Blob to trigger processing
az storage blob upload \
  -f trigger.json \
  -c greengovrag-documents \
  -n documents/federal/trigger.json \
  --connection-string "YOUR_CONNECTION_STRING"

# Monitor sensor
airflow tasks logs greengovrag_azure_sensor wait_for_new_documents <date>
```

**Configuration:**
```bash
# Set up Azure connection in Airflow
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{"connection_string": "DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"}'

# OR using SAS token:
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{"sas_token": "YOUR_SAS_TOKEN"}'
```

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

## Troubleshooting

### Common Issues

#### 1. Credentials Not Found

**Error**: `ValueError: AWS_ACCESS_KEY_ID is required when CLOUD_PROVIDER is 'aws'`

**Solution**: Add credentials to `.env`:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

Or skip validation during development:
```bash
DEBUG=true
```

#### 2. Container/Bucket Not Found

**Error**: `botocore.exceptions.NoSuchBucket: The specified bucket does not exist`

**Solution**: Create the bucket first:
```bash
# AWS
aws s3 mb s3://greengovrag-documents

# Azure
az storage container create -n greengovrag-documents
```

#### 3. Permission Denied

**Error**: `botocore.exceptions.ClientError: Access Denied`

**Solution**: Ensure IAM policy includes:
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

#### 4. Documents Not Found After Migration

**Issue**: Documents uploaded to cloud but not appearing in queries

**Solution**: Check the storage path structure:
```python
# Verify document path
metadata = adapter.load_metadata(doc_id)
print(metadata.get('storage_path'))

# Should be: documents/{jurisdiction}/{category}/{topic}/{filename}
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

# List files
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
- AWS S3: 5 MB multipart threshold
- Azure Blob: 4 MB block size

3. **Caching**: Use local cache for frequently accessed documents
```python
# Enable caching in your application
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_document(doc_id):
    return adapter.load_document(doc_id, metadata)
```

4. **Region Selection**: Choose cloud regions close to your compute
```bash
CLOUD_REGION=us-east-1  # Match your app region
AWS_REGION=us-east-1
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/yourusername/green-gov-rag/issues
- Documentation: https://docs.greengovrag.com
- Email: support@greengovrag.com

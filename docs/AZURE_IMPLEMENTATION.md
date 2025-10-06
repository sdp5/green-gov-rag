# Azure Blob Storage Implementation

## Overview

The GreenGovRAG ETL pipeline now includes full Azure Blob Storage support, matching the existing AWS S3 capabilities. This document covers Azure-specific setup and configuration.

## Features Implemented

### 1. Azure Blob Storage Backend ✅
- **Location**: `green_gov_rag/cloud/storage.py` - `AzureBackend` class
- Full CRUD operations on Azure Blob Storage
- Connection string and SAS token support
- Automatic blob container creation

### 2. ETL Storage Adapter ✅
- **Location**: `green_gov_rag/etl/storage_adapter.py`
- Cloud-agnostic interface works seamlessly with Azure
- Automatic provider detection from `CLOUD_PROVIDER=azure`

### 3. Airflow Azure Sensor ✅
- **Location**: `green_gov_rag/airflow/dags/etl_pipeline_cloud.py`
- `greengovrag_azure_sensor` DAG for automatic triggers
- Uses `WasbBlobSensor` to monitor for new documents
- Auto-triggers main ETL pipeline when trigger file detected

## Configuration

### Environment Variables

```bash
# .env file
CLOUD_PROVIDER=azure
STORAGE_CONTAINER=greengovrag-documents
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net

# Optional: Cloud region
CLOUD_REGION=eastus
```

### Airflow Connection Setup

#### Option 1: Connection String (Recommended)

```bash
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net"
  }'
```

#### Option 2: SAS Token

```bash
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "sas_token": "sv=2021-06-08&ss=bfqt&srt=sco&sp=rwdlacupiytfx&se=2025-12-31T23:59:59Z&st=2025-01-01T00:00:00Z&spr=https&sig=..."
  }'
```

#### Option 3: Managed Identity (Azure VMs)

```bash
airflow connections add azure_blob_default \
  --conn-type wasb \
  --conn-extra '{
    "use_managed_identity": true,
    "storage_account_name": "myaccount"
  }'
```

### Airflow Variables

```bash
airflow variables set STORAGE_PROVIDER azure
airflow variables set STORAGE_CONTAINER greengovrag-documents
airflow variables set ENABLE_AUTO_TAGGING true
airflow variables set CHUNK_SIZE 1000
```

## Azure Resources Setup

### 1. Create Storage Account

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

### 2. Create Blob Container

```bash
# Set connection string
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# Create container
az storage container create \
  --name greengovrag-documents \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"

# Set public access (optional, for testing)
az storage container set-permission \
  --name greengovrag-documents \
  --public-access blob \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

### 3. Generate SAS Token (Optional)

```bash
# Generate SAS token valid for 1 year
az storage container generate-sas \
  --name greengovrag-documents \
  --permissions racwdl \
  --expiry 2025-12-31T23:59:59Z \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

## Usage Examples

### Python API

```python
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

# Initialize for Azure (auto-detected from settings)
adapter = ETLStorageAdapter()

# Or explicitly
adapter = ETLStorageAdapter(provider='azure', container='greengovrag-documents')

# Upload document
doc_id = adapter.download_from_url(
    "https://example.com/document.pdf",
    metadata={
        "title": "Climate Policy 2024",
        "jurisdiction": "federal",
        "category": "environment",
        "topic": "climate"
    }
)

# List documents
docs = adapter.list_documents(jurisdiction="federal")

# Load document
metadata = adapter.load_metadata(doc_id)
content = adapter.load_document(doc_id, metadata)
```

### Azure CLI Operations

```bash
# Upload document directly to blob
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

## Airflow DAG Usage

### Trigger Processing Manually

```bash
# Trigger the main pipeline
airflow dags trigger greengovrag_cloud_pipeline \
  --conf '{"storage_provider": "azure", "enable_auto_tagging": true}'

# Monitor execution
airflow dags list-runs -d greengovrag_cloud_pipeline

# View logs
airflow tasks logs greengovrag_cloud_pipeline ingest_documents 2025-01-01
```

### Automatic Triggering via Sensor

1. **Upload trigger file to Azure Blob:**

```bash
# Create trigger file
echo '{"trigger": true, "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > trigger.json

# Upload to container
az storage blob upload \
  -f trigger.json \
  -c greengovrag-documents \
  -n documents/federal/trigger.json \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
```

2. **Sensor detects file and triggers pipeline:**
   - `greengovrag_azure_sensor` DAG polls every 60 seconds
   - Detects `trigger.json` file
   - Triggers `greengovrag_cloud_pipeline` DAG automatically

3. **Monitor sensor:**

```bash
# Check sensor status
airflow dags list-runs -d greengovrag_azure_sensor

# View sensor logs
airflow tasks logs greengovrag_azure_sensor wait_for_new_documents 2025-01-01
```

## Azure Sensor DAG Details

### DAG Configuration

```python
# From etl_pipeline_cloud.py
azure_sensor = WasbBlobSensor(
    task_id="wait_for_new_documents",
    container_name=STORAGE_CONTAINER,
    blob_name="documents/*/trigger.json",  # Pattern matching
    wasb_conn_id="azure_blob_default",
    timeout=60 * 60,  # 1 hour
    poke_interval=60,  # Check every minute
    check_options={"prefix": "documents/"},
)

trigger_pipeline = TriggerDagRunOperator(
    task_id="trigger_etl_pipeline",
    trigger_dag_id="greengovrag_cloud_pipeline",
    wait_for_completion=False,
    conf={
        "triggered_by": "azure_sensor",
        "storage_provider": "azure",
    },
)

azure_sensor >> trigger_pipeline
```

### Customizing Sensor Behavior

Edit `etl_pipeline_cloud.py` to change:

```python
# Check every 5 minutes instead of 1 minute
poke_interval=300

# Timeout after 2 hours instead of 1 hour
timeout=2 * 60 * 60

# Different trigger pattern
blob_name="documents/ready/*.json"
```

## Storage Path Structure

Azure Blob Storage uses the same structure as S3:

```
greengovrag-documents/
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

Example:
```
greengovrag-documents/
├── documents/federal/environment/emissions/nger-guidelines.pdf
├── metadata/federal/environment/emissions/nger-guidelines.pdf.json
└── chunks/abc123def456/000001.json
```

## Testing

### Test Azure Connection

```python
from green_gov_rag.cloud.storage import StorageClient

# Test connection
client = StorageClient(provider='azure')

# List files
files = client.list_files('greengovrag-documents', prefix='documents/')
print(f"Found {len(files)} files in Azure Blob Storage")

# Test upload
with open('test.txt', 'w') as f:
    f.write('Hello Azure!')

client.upload_file('test.txt', 'greengovrag-documents', 'test/test.txt')
print("Upload successful!")

# Test download
client.download_file('greengovrag-documents', 'test/test.txt', 'downloaded.txt')
print("Download successful!")
```

### Test ETL Adapter

```python
from green_gov_rag.etl.storage_adapter import ETLStorageAdapter

adapter = ETLStorageAdapter(provider='azure')

# Get storage info
info = adapter.get_storage_info()
print(info)
# {'provider': 'azure', 'container': 'greengovrag-documents', 'backend_type': 'AzureBackend'}

# Test document save
doc_id = adapter.save_document(
    content=b"Test document content",
    metadata={
        "title": "Test Document",
        "jurisdiction": "federal",
        "category": "test",
        "topic": "testing",
        "filename": "test.txt"
    }
)
print(f"Saved document: {doc_id}")

# List documents
docs = adapter.list_documents()
print(f"Total documents: {len(docs)}")
```

### Test Airflow DAG

```bash
# Test individual tasks
airflow tasks test greengovrag_cloud_pipeline ingest_documents 2025-01-01
airflow tasks test greengovrag_cloud_pipeline sync_metadata_to_db 2025-01-01

# Test sensor
airflow tasks test greengovrag_azure_sensor wait_for_new_documents 2025-01-01
```

## Performance Considerations

### Azure-Specific Optimizations

1. **Block Size**: Azure uses 4MB blocks by default
   ```python
   # For large files, consider increasing
   blob_client.upload_blob(data, max_concurrency=4, block_size=8*1024*1024)
   ```

2. **Region Selection**: Choose region close to compute
   ```bash
   CLOUD_REGION=eastus  # Match your VM/AKS region
   ```

3. **Access Tiers**: Use appropriate storage tier
   - Hot: Frequently accessed data
   - Cool: Infrequently accessed (30+ days)
   - Archive: Rarely accessed (180+ days)

4. **CDN Integration**: For document delivery
   ```bash
   # Enable Azure CDN for blob storage
   az cdn endpoint create \
     --resource-group greengovrag-rg \
     --name greengovrag-cdn \
     --profile-name greengovrag-profile \
     --origin greengovragstorage.blob.core.windows.net
   ```

## Security Best Practices

1. **Use Managed Identity** (for Azure VMs/AKS)
2. **Rotate SAS Tokens** regularly (max 1 year)
3. **Enable Soft Delete** for blob recovery
4. **Use Private Endpoints** for production
5. **Enable Azure Monitor** for logging

```bash
# Enable soft delete
az storage blob service-properties delete-policy update \
  --enable true \
  --days-retained 7 \
  --account-name greengovragstorage

# Enable logging
az storage logging update \
  --log rwd \
  --retention 90 \
  --services b \
  --account-name greengovragstorage
```

## Monitoring

### Azure Portal
- Navigate to Storage Account → Monitoring
- View metrics: Requests, Latency, Availability
- Set up alerts for failures

### Azure CLI
```bash
# View storage metrics
az monitor metrics list \
  --resource /subscriptions/{sub-id}/resourceGroups/greengovrag-rg/providers/Microsoft.Storage/storageAccounts/greengovragstorage \
  --metric-names Transactions \
  --aggregation Total
```

### Airflow Monitoring
```bash
# Monitor DAG runs
airflow dags list-runs -d greengovrag_azure_sensor

# View task logs
airflow tasks logs greengovrag_azure_sensor wait_for_new_documents <date>
```

## Troubleshooting

### Common Issues

1. **Connection String Invalid**
   ```bash
   # Verify connection string format
   echo $AZURE_STORAGE_CONNECTION_STRING
   # Should start with: DefaultEndpointsProtocol=https;AccountName=...
   ```

2. **Container Not Found**
   ```bash
   # List containers
   az storage container list --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
   ```

3. **Permission Denied**
   ```bash
   # Check SAS token permissions
   # Ensure: racwdl (read, add, create, write, delete, list)
   ```

4. **Sensor Not Triggering**
   ```bash
   # Check sensor logs
   airflow tasks logs greengovrag_azure_sensor wait_for_new_documents <date>

   # Verify blob exists
   az storage blob exists \
     -c greengovrag-documents \
     -n documents/federal/trigger.json \
     --connection-string "$AZURE_STORAGE_CONNECTION_STRING"
   ```

## Dependencies

### Required Python Packages
```bash
pip install azure-storage-blob==12.19.0
pip install apache-airflow-providers-microsoft-azure==8.4.0
```

### Airflow Provider
```bash
# Ensure Azure provider is installed
airflow providers list | grep azure
# Should show: apache-airflow-providers-microsoft-azure
```

## Migration from AWS to Azure

See `CLOUD_STORAGE_GUIDE.md` section "Migrating from Cloud to Cloud (AWS → Azure)" for detailed migration steps.

Quick summary:
1. Initialize both AWS and Azure adapters
2. Copy documents and metadata
3. Copy chunks
4. Update configuration to CLOUD_PROVIDER=azure
5. Test and verify

## Next Steps

- Set up Azure Monitor alerts for storage failures
- Implement lifecycle policies for data archiving
- Configure Azure CDN for global document delivery
- Set up geo-redundant replication (GRS)
- Integrate with Azure Key Vault for credential management

## Resources

- [Azure Blob Storage Documentation](https://docs.microsoft.com/azure/storage/blobs/)
- [Airflow Azure Provider](https://airflow.apache.org/docs/apache-airflow-providers-microsoft-azure/)
- [Azure Python SDK](https://docs.microsoft.com/python/api/overview/azure/storage-blob)
- [GreenGovRAG Cloud Storage Guide](./CLOUD_STORAGE_GUIDE.md)

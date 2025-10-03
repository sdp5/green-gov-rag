# Quick Start: Cloud-Agnostic GreenGovRAG

Get started with GreenGovRAG on your preferred cloud platform in minutes.

## 🚀 Choose Your Platform

<details>
<summary><b>Option 1: Local (Recommended for Development)</b></summary>

### Prerequisites
- Docker & Docker Compose
- 5 minutes

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag

# 2. Configure environment
cp .env.example .env
# Edit .env and set:
# CLOUD_PROVIDER=local
# LOCAL_STORAGE_PATH=./data/storage

# 3. Start services
cd deploy/docker
docker-compose up -d

# 4. Access the application
# UI: http://localhost:8501
# API: http://localhost:8000
```

**Estimated Time:** 5 minutes
**Cost:** $0
</details>

<details>
<summary><b>Option 2: Azure (Recommended for Production)</b></summary>

### Prerequisites
- Azure CLI installed
- Active Azure subscription
- 30 minutes

### Steps

```bash
# 1. Install Azure CLI (if not installed)
# macOS: brew install azure-cli
# Ubuntu: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# 2. Login to Azure
az login

# 3. Clone and configure
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/deploy/azure

# 4. Run deployment script
chmod +x deploy.sh
./deploy.sh

# 5. Get application URL
az containerapp show \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv

# 6. Build and push Docker images
# Follow instructions in deploy/azure/README.md
```

**Estimated Time:** 30 minutes
**Cost:** ~$30-50/month (dev), ~$230-260/month (prod)
</details>

<details>
<summary><b>Option 3: AWS</b></summary>

### Prerequisites
- AWS CLI installed and configured
- AWS CDK installed (`npm install -g aws-cdk`)
- Valid AWS credentials
- 45 minutes

### Steps

```bash
# 1. Install AWS CDK
npm install -g aws-cdk

# 2. Clone and configure
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/deploy/aws

# 3. Install dependencies
pip install -r requirements.txt

# 4. Bootstrap CDK (first time only)
cdk bootstrap

# 5. Deploy
cdk deploy

# 6. Get application URL
cdk outputs | grep LoadBalancerUrl
```

**Estimated Time:** 45 minutes
**Cost:** ~$60-80/month (dev), ~$250-300/month (prod)
</details>

---

## 📝 Quick Test

Test the cloud storage abstraction:

```bash
# Set your cloud provider
export CLOUD_PROVIDER=local  # or aws, azure

# Run the example
python examples/cloud_storage_example.py
```

Expected output:
```
=== Cloud Storage Abstraction Layer Example ===
Using provider: local

=== Uploading test_document.txt to greengovrag-documents/examples/test_document.txt ===
✅ Upload successful

=== Checking if examples/test_document.txt exists ===
File exists: True

=== Example completed successfully! ===
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Cloud Provider (choose one: aws, azure, local)
CLOUD_PROVIDER=local

# For AWS
AWS_DEFAULT_REGION=ap-southeast-2
STORAGE_CONTAINER=greengovrag-documents

# For Azure
CLOUD_REGION=australiaeast
AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

# For Local
LOCAL_STORAGE_PATH=./data/storage

# Common
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql://user:pass@host:5432/greengovrag
```

---

## 📚 Next Steps

### 1. Ingest Documents

```bash
# Install CLI
pip install -e .

# Download documents
greengovrag-cli ingest-docs --config configs/documents_config.yml

# Process documents
greengovrag-cli parse-docs
greengovrag-cli chunk-docs
greengovrag-cli embed-docs
greengovrag-cli build-vector-store
```

### 2. Query the System

```bash
# Via CLI
greengovrag-cli evaluate-query "What are the native vegetation clearance rules in SA?"

# Via UI
# Open http://localhost:8501 (local)
# Or your cloud URL
```

### 3. Migrate Between Clouds

```python
from green_gov_rag.cloud import StorageClient

# Source
source = StorageClient(provider="local")
files = source.list_files("greengovrag-documents")

# Destination
dest = StorageClient(provider="aws")

# Migrate
for file in files:
    source.download_file("greengovrag-documents", file, f"/tmp/{file}")
    dest.upload_file(f"/tmp/{file}", "greengovrag-documents", file)
```

---

## 📖 Documentation

- **Full Documentation**: See `/docs` directory
- **Deployment Guide**: `deploy/README.md`
- **Azure Guide**: `deploy/azure/README.md`
- **Migration Guide**: `docs/CLOUD_MIGRATION.md`
- **Cloud Comparison**: `docs/CLOUD_PROVIDER_COMPARISON.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`

---

## 🐛 Troubleshooting

### Local Issues

**Problem:** Port 8501 already in use
```bash
# Solution: Change port in docker-compose.yml
ports:
  - "8502:8501"  # Use 8502 instead
```

**Problem:** Permission denied on ./data/storage
```bash
# Solution: Fix permissions
chmod 755 ./data/storage
```

### AWS Issues

**Problem:** No credentials found
```bash
# Solution: Configure AWS CLI
aws configure
```

### Azure Issues

**Problem:** AZURE_STORAGE_CONNECTION_STRING required
```bash
# Solution: Get from Azure Portal
az storage account show-connection-string \
  --name <storage-account> \
  --resource-group greengovrag-rg
```

---

## 💡 Tips

1. **Start Local**: Always test locally first
2. **Use Azure for Production**: More cost-effective than AWS
3. **Set Up Monitoring**: Enable Application Insights (Azure) or CloudWatch (AWS)
4. **Backup Regularly**: Implement backup procedures
5. **Use Secrets Managers**: Never hardcode credentials

---

## 🎯 Success Checklist

- [ ] Environment configured (`.env` file created)
- [ ] Cloud provider chosen and configured
- [ ] Infrastructure deployed (if using cloud)
- [ ] Application accessible
- [ ] Test query successful
- [ ] Documents ingested
- [ ] Vector store built
- [ ] Monitoring enabled (cloud only)

---

## 📞 Get Help

- **Documentation**: Check `/docs` directory
- **Examples**: See `/examples` directory
- **Issues**: [GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)
- **AWS Support**: https://console.aws.amazon.com/support/
- **Azure Support**: https://azure.microsoft.com/support/

---

## 🎉 You're Ready!

Your GreenGovRAG instance is now running. Start asking questions about Australian environmental and planning regulations!

**Example Queries:**
- "Do I need an environmental impact assessment to build a solar farm in regional NSW?"
- "Can I clear native vegetation on my property near Murray Bridge, SA?"
- "What are the zoning restrictions for coastal land in Mornington Peninsula, VIC?"
- "Which emissions standards apply to industrial zones in Greater Sydney?"

---

**Happy querying! 🌿🏛️**

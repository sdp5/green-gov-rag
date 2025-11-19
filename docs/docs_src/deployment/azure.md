# Azure Deployment

> Enterprise deployment using Azure Container Apps, PostgreSQL Flexible Server, and Container Instances

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Front Door                       │
│                   (CDN + WAF + HTTPS)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
     ┌─────────────┴────────────┐
     │                          │
     ▼                          ▼
┌─────────────┐          ┌──────────────────┐
│ Blob Storage│          │  Container Apps  │
│  (Frontend) │          │    (Backend)     │
└─────────────┘          └────────┬─────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
                ▼                 ▼                 ▼
         ┌─────────────┐   ┌──────────┐    ┌──────────────┐
         │ PostgreSQL  │   │  Qdrant  │    │   Cosmos DB  │
         │   Flexible  │   │(Container│    │ (Cache/NoSQL)│
         │   Server    │   │Instance) │    │              │
         └─────────────┘   └──────────┘    └──────────────┘
```

## Prerequisites

### 1. Azure Account Setup

- Azure subscription (free tier available)
- Azure CLI installed:

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Set subscription
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### 2. Resource Group Creation

```bash
az group create \
  --name greengovrag-rg \
  --location australiaeast
```

### 3. Required Permissions

Your Azure account needs:

- Contributor role on subscription
- Permissions to create:
    - Container Apps, Container Instances
    - PostgreSQL Flexible Server
    - Storage Account, Front Door, Cosmos DB
    - Virtual Network, Log Analytics

### 4. LLM API Key

You need an API key for:
  
- Azure OpenAI (recommended for enterprise)
- OpenAI API
- Other supported providers

## Deployment Steps

### 1. Clone Repository

```bash
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/deploy/azure
```

### 2. Configure Variables

Edit `main.bicep` parameters:

```bicep
param location string = 'australiaeast'
param projectName string = 'greengovrag'
param environment string = 'prod'
param containerImage string = 'ghcr.io/sdp5/green-gov-rag:latest'
```

### 3. Set Secrets in Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name greengovrag-kv \
  --resource-group greengovrag-rg \
  --location australiaeast

# Store OpenAI API key
az keyvault secret set \
  --vault-name greengovrag-kv \
  --name openai-api-key \
  --value "sk-your-key-here"

# Store database password
DB_PASSWORD=$(openssl rand -base64 32)
az keyvault secret set \
  --vault-name greengovrag-kv \
  --name db-password \
  --value "$DB_PASSWORD"

# Optional: Azure OpenAI
az keyvault secret set \
  --vault-name greengovrag-kv \
  --name azure-openai-key \
  --value "your-azure-openai-key"
```

### 4. Deploy Infrastructure

```bash
# Validate template
az deployment group validate \
  --resource-group greengovrag-rg \
  --template-file main.bicep \
  --parameters main.parameters.json

# Deploy
az deployment group create \
  --resource-group greengovrag-rg \
  --template-file main.bicep \
  --parameters main.parameters.json
```

Deployment takes ~15-20 minutes.

### 5. Configure Container Apps Environment

```bash
# Get Container Apps environment name
ENVIRONMENT_NAME=$(az containerapp env list \
  --resource-group greengovrag-rg \
  --query '[0].name' -o tsv)

# Update backend container
az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --set-env-vars \
    LLM_PROVIDER=azure \
    LLM_MODEL=gpt-5-mini \
    VECTOR_STORE_TYPE=qdrant \
    DATABASE_URL=secretref:db-connection-string \
    AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com \
    AZURE_OPENAI_API_KEY=secretref:azure-openai-key
```

### 6. Get Deployment Outputs

```bash
# Get backend URL
az containerapp show \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv

# Get frontend URL
az storage account show \
  --name greengovragfrontend \
  --resource-group greengovrag-rg \
  --query primaryEndpoints.web -o tsv
```

### 7. Verify Deployment

```bash
# Health check
BACKEND_URL=$(az containerapp show \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv)

curl https://$BACKEND_URL/api/health
```

### 8. Configure Front Door

```bash
# Create Front Door profile
az afd profile create \
  --profile-name greengovrag-fd \
  --resource-group greengovrag-rg \
  --sku Standard_AzureFrontDoor

# Add origin for backend
az afd origin create \
  --resource-group greengovrag-rg \
  --host-name $BACKEND_URL \
  --profile-name greengovrag-fd \
  --origin-group-name backend-origins \
  --origin-name backend \
  --priority 1 \
  --weight 1000 \
  --enabled-state Enabled \
  --http-port 80 \
  --https-port 443
```

### 9. Run ETL Pipeline

**Using Azure Container Instances**:

```bash
az container create \
  --resource-group greengovrag-rg \
  --name greengovrag-etl \
  --image ghcr.io/sdp5/green-gov-rag:latest \
  --command-line "greengovrag-cli etl run-pipeline" \
  --environment-variables \
    LLM_PROVIDER=azure \
    DATABASE_URL=<connection-string> \
  --secure-environment-variables \
    OPENAI_API_KEY=<key> \
  --restart-policy Never
```

**Check logs**:
```bash
az container logs \
  --resource-group greengovrag-rg \
  --name greengovrag-etl \
  --follow
```

## Configuration

### Environment Variables

Set in Container App:

```bash
az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --set-env-vars \
    LLM_PROVIDER=azure \
    LLM_MODEL=gpt-5-mini \
    VECTOR_STORE_TYPE=qdrant \
    CLOUD_PROVIDER=azure \
    LOG_LEVEL=INFO \
  --secrets \
    db-password=<value> \
    openai-api-key=<value>
```

### Azure OpenAI Configuration

**Create Azure OpenAI resource**:

```bash
az cognitiveservices account create \
  --name greengovrag-openai \
  --resource-group greengovrag-rg \
  --kind OpenAI \
  --sku S0 \
  --location australiaeast

# Deploy model
az cognitiveservices account deployment create \
  --name greengovrag-openai \
  --resource-group greengovrag-rg \
  --deployment-name gpt-5-mini \
  --model-name gpt-5-mini \
  --model-version "0301" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

**Configure backend**:

```bash
OPENAI_ENDPOINT=$(az cognitiveservices account show \
  --name greengovrag-openai \
  --resource-group greengovrag-rg \
  --query properties.endpoint -o tsv)

OPENAI_KEY=$(az cognitiveservices account keys list \
  --name greengovrag-openai \
  --resource-group greengovrag-rg \
  --query key1 -o tsv)

az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --set-env-vars \
    LLM_PROVIDER=azure \
    AZURE_OPENAI_ENDPOINT=$OPENAI_ENDPOINT \
  --replace-secrets \
    azure-openai-key=$OPENAI_KEY
```

### Scaling Configuration

**Container Apps auto-scaling**:

```bash
az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --min-replicas 1 \
  --max-replicas 10 \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100
```

**Or edit `main.bicep`**:

```bicep
resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  properties: {
    configuration: {
      scaling: {
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}
```

### Database Scaling

**Upgrade PostgreSQL tier**:

```bash
az postgres flexible-server update \
  --name greengovrag-db \
  --resource-group greengovrag-rg \
  --sku-name Standard_B2s  # Upgrade from B1ms
```

## CI/CD Pipeline

### GitHub Actions Setup

#### 1. Create Service Principal

```bash
az ad sp create-for-rbac \
  --name greengovrag-github-actions \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/greengovrag-rg \
  --sdk-auth
```

Copy the output JSON to GitHub Secrets as `AZURE_CREDENTIALS`.

#### 2. Configure GitHub Secrets

In repository Settings → Secrets and variables → Actions:

```
AZURE_CREDENTIALS=<json-from-above>
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
AZURE_RESOURCE_GROUP=greengovrag-rg
CONTAINER_REGISTRY=greengovrag.azurecr.io
OPENAI_API_KEY=sk-...
```

#### 3. Workflow Files

**.github/workflows/deploy-azure.yml**:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push Docker image
        run: |
          az acr build \
            --registry ${{ secrets.CONTAINER_REGISTRY }} \
            --image greengovrag:${{ github.sha }} \
            --file backend/Dockerfile .

      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name greengovrag-backend \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }} \
            --image ${{ secrets.CONTAINER_REGISTRY }}/greengovrag:${{ github.sha }}
```

## Monitoring

### Application Insights

**Create Application Insights**:

```bash
az monitor app-insights component create \
  --app greengovrag-insights \
  --location australiaeast \
  --resource-group greengovrag-rg \
  --application-type web

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app greengovrag-insights \
  --resource-group greengovrag-rg \
  --query instrumentationKey -o tsv)

# Configure backend
az containerapp update \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --set-env-vars \
    APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=$INSTRUMENTATION_KEY
```

### View Logs

```bash
# Container Apps logs
az containerapp logs show \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --follow

# Query Log Analytics
az monitor log-analytics query \
  --workspace greengovrag-logs \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'greengovrag-backend' | order by TimeGenerated desc | take 100"
```

### Metrics

**View in Azure Portal**: Monitor → Metrics → Select resource

**Key metrics**:

- Container Apps: CPU/Memory usage, HTTP requests, Response time
- PostgreSQL: CPU/Memory, Connections, Storage
- Cosmos DB: Request units, Storage, Latency

### Alerts

**Create CPU alert**:

```bash
az monitor metrics alert create \
  --name HighCPUAlert \
  --resource-group greengovrag-rg \
  --scopes /subscriptions/.../resourceGroups/greengovrag-rg/providers/Microsoft.App/containerApps/greengovrag-backend \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email=contact@sundeep.id.au
```

## Backup and Recovery

### PostgreSQL Automated Backups

```bash
# Backups are automatic (7-day retention)
# List backups
az postgres flexible-server backup list \
  --resource-group greengovrag-rg \
  --server-name greengovrag-db

# Restore from backup
az postgres flexible-server restore \
  --resource-group greengovrag-rg \
  --name greengovrag-db-restored \
  --source-server greengovrag-db \
  --restore-time "2025-11-15T02:00:00Z"
```

### Qdrant Backups

**Manual snapshot**:

```bash
# Connect to container instance
az container exec \
  --resource-group greengovrag-rg \
  --name greengovrag-qdrant \
  --exec-command "/bin/sh"

# Inside container
curl -X POST 'http://localhost:6333/collections/greengovrag/snapshots'
```

### Blob Storage Backups

Enable soft delete:

```bash
az storage account blob-service-properties update \
  --account-name greengovragfrontend \
  --resource-group greengovrag-rg \
  --enable-delete-retention true \
  --delete-retention-days 7
```

## Troubleshooting

### Issue: Container App Not Starting

**Check logs**:

```bash
az containerapp logs show \
  --name greengovrag-backend \
  --resource-group greengovrag-rg \
  --tail 100
```

Common causes:

- Missing environment variables
- Database connection string incorrect
- Container image not found

### Issue: Database Connection Timeout

**Check firewall rules**:

```bash
# Allow Azure services
az postgres flexible-server firewall-rule create \
  --resource-group greengovrag-rg \
  --name greengovrag-db \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### Issue: High Costs

**Optimization steps**:

1. Use Burstable tier for PostgreSQL (B1ms instead of GP_Standard_D2s_v3)
2. Set Container Apps min replicas to 0 (scale to zero)
3. Use Serverless Cosmos DB instead of provisioned throughput
4. Enable blob storage lifecycle policies
5. Use Azure Front Door Standard instead of Premium

## Teardown

### Delete Resource Group

```bash
# This deletes all resources in the group
az group delete \
  --name greengovrag-rg \
  --yes --no-wait
```

**Note**: Some resources may have soft-delete:

- Key Vault (can be purged after 90 days or immediately with `--purge`)
- Blob Storage (soft-deleted blobs retained for 7 days)

**Force delete Key Vault**:

```bash
az keyvault purge \
  --name greengovrag-kv \
  --location australiaeast
```

## Next Steps

- [Production Checklist](production-checklist.md) - Pre-launch verification
- [Monitoring Guide](monitoring.md) - Detailed monitoring setup
- [Cloud Comparison](cloud-comparison.md) - AWS vs Azure comparison

---

**Last Updated**: 2025-11-22

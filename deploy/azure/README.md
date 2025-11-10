# Azure Deployment for GreenGovRAG

This directory contains Azure Bicep templates for deploying GreenGovRAG to Azure using Container Apps.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │             FastAPI Backend (Port 8000)                    │  │
│  │              Container App + ETL Jobs                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
   ┌────▼─────┐      ┌─────────▼───────┐    ┌─────────▼──────┐
   │  Blob    │      │  PostgreSQL     │    │  Spot VM       │
   │  Storage │      │  Flex Server    │    │  (Qdrant)      │
   │+ Tables  │      │  (pgvector)     │    │                │
   └──────────┘      └─────────────────┘    └────────────────┘

   ┌─────────────────────────────────────────┐
   │        Static Web App (Frontend)        │
   │              React + TypeScript         │
   └─────────────────────────────────────────┘
```

## Resources Deployed

- **Azure Container Apps** - FastAPI backend (1 vCPU, 3GB)
- **Container App Jobs** - ETL pipeline + monitoring jobs
- **Storage Account** - Blob storage (documents) + Table Storage (cache)
- **PostgreSQL Flexible Server** - B1s with pgvector extension
- **Spot VM (Ubuntu)** - Qdrant vector database (60-90% cost savings)
- **Static Web App** - React frontend (Free tier)
- **Log Analytics Workspace** - Centralized logging

## Prerequisites

- Azure CLI (`az`) installed
- Active Azure subscription
- Python 3.12+
- Docker (for building images)

## Quick Start

### 1. Install Azure CLI

```bash
# macOS
brew install azure-cli

# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Windows
# Download from: https://aka.ms/installazurecliwindows
```

### 2. Login to Azure

```bash
az login

# List subscriptions
az account list --output table

# Set subscription (if you have multiple)
az account set --subscription "Your-Subscription-Name"
```

### 3. Deploy Infrastructure

```bash
cd deploy/azure

# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
1. Create a resource group
2. Deploy all infrastructure via Bicep
3. Configure managed identity and RBAC
4. Output deployment information

## Manual Deployment

If you prefer to deploy manually:

### 1. Create Resource Group

```bash
RESOURCE_GROUP="greengovrag-rg"
LOCATION="australiaeast"

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 2. Set Secrets

Create a Key Vault to store secrets first (or use existing):

```bash
KV_NAME="greengovrag-init-kv"

az keyvault create \
  --name $KV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Store PostgreSQL password
az keyvault secret set \
  --vault-name $KV_NAME \
  --name "postgres-admin-password" \
  --value "your-secure-password"

# Store OpenAI API key
az keyvault secret set \
  --vault-name $KV_NAME \
  --name "openai-api-key" \
  --value "sk-..."
```

### 3. Update Parameters File

Edit `parameters.dev.json` and update the Key Vault references:

```json
{
  "postgresPassword": {
    "reference": {
      "keyVault": {
        "id": "/subscriptions/{sub-id}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{kv-name}"
      },
      "secretName": "postgres-admin-password"
    }
  }
}
```

### 4. Deploy with Bicep

```bash
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters @parameters.dev.json
```

### 5. Build and Push Docker Images

```bash
# Get ACR login server
ACR_NAME=$(az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs.containerRegistryLoginServer.value -o tsv)

# Login to ACR
az acr login --name ${ACR_NAME%%.*}

# Build and push API image
docker build -t $ACR_NAME/greengovrag-api:latest \
  -f ../../deploy/docker/api/Dockerfile \
  ../..

docker push $ACR_NAME/greengovrag-api:latest

# Build and push UI image
docker build -t $ACR_NAME/greengovrag-ui:latest \
  -f ../../deploy/docker/streamlit/Dockerfile \
  ../..

docker push $ACR_NAME/greengovrag-ui:latest
```

### 6. Update Container Apps

The container apps will automatically pull the new images, or you can force an update:

```bash
az containerapp update \
  --name greengovrag-dev-api \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME/greengovrag-api:latest

az containerapp update \
  --name greengovrag-dev-ui \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME/greengovrag-ui:latest
```

## Post-Deployment

### Get Application URLs

```bash
# API URL
az containerapp show \
  --name greengovrag-dev-api \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv

# UI URL
az containerapp show \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --query properties.configuration.ingress.fqdn -o tsv
```

### Get Storage Connection String

```bash
STORAGE_ACCOUNT=$(az deployment group show \
  --resource-group greengovrag-rg \
  --name main \
  --query properties.outputs.storageAccountName.value -o tsv)

az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group greengovrag-rg
```

### View Logs

```bash
# View UI logs
az containerapp logs show \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --follow

# View API logs
az containerapp logs show \
  --name greengovrag-dev-api \
  --resource-group greengovrag-rg \
  --follow

# View logs in Log Analytics
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where ContainerAppName_s == 'greengovrag-dev-ui' | order by TimeGenerated desc | limit 100"
```

## Configuration

### Environment Variables

The following environment variables are configured in the Container Apps:

```bash
CLOUD_PROVIDER=azure
CLOUD_REGION=australiaeast
STORAGE_CONTAINER=documents
AZURE_STORAGE_CONNECTION_STRING=<from-keyvault>
OPENAI_API_KEY=<from-keyvault>
DATABASE_URL=<from-keyvault>
```

### Scaling

Configure auto-scaling rules:

```bash
az containerapp update \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --min-replicas 1 \
  --max-replicas 10 \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50
```

### Custom Domain

Add a custom domain:

```bash
# Add custom domain
az containerapp hostname add \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --hostname app.yourdomain.com

# Bind certificate
az containerapp hostname bind \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --hostname app.yourdomain.com \
  --certificate <certificate-name>
```

## Cost Optimization

### Development Environment

For development, use minimal resources:

```bicep
// In main.bicep, adjust:
sku: {
  name: 'Standard_B1ms'  // Burstable tier for PostgreSQL
}

resources: {
  cpu: json('0.25')      // Minimal CPU
  memory: '0.5Gi'        // Minimal memory
}

scale: {
  minReplicas: 0         // Scale to zero when idle
  maxReplicas: 1
}
```

### Production Environment

For production, use appropriate resources:

```bicep
sku: {
  name: 'Standard_D2s_v3'  // General purpose
}

resources: {
  cpu: json('1.0')
  memory: '2Gi'
}

scale: {
  minReplicas: 2           // High availability
  maxReplicas: 10
}
```

## Monitoring

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app greengovrag-insights \
  --location australiaeast \
  --resource-group greengovrag-rg \
  --workspace <log-analytics-workspace-id>

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app greengovrag-insights \
  --resource-group greengovrag-rg \
  --query instrumentationKey -o tsv)

# Add to container app
az containerapp update \
  --name greengovrag-dev-ui \
  --resource-group greengovrag-rg \
  --set-env-vars "APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY"
```

### Set Up Alerts

```bash
# CPU alert
az monitor metrics alert create \
  --name cpu-alert \
  --resource-group greengovrag-rg \
  --scopes <container-app-id> \
  --condition "avg Percentage CPU > 80" \
  --description "Alert when CPU exceeds 80%"

# Memory alert
az monitor metrics alert create \
  --name memory-alert \
  --resource-group greengovrag-rg \
  --scopes <container-app-id> \
  --condition "avg MemoryPercentage > 80" \
  --description "Alert when memory exceeds 80%"
```

## Security

### Network Security

Enable VNet integration:

```bash
# Create VNet
az network vnet create \
  --name greengovrag-vnet \
  --resource-group greengovrag-rg \
  --address-prefix 10.0.0.0/16 \
  --subnet-name container-subnet \
  --subnet-prefix 10.0.0.0/24

# Update Container Apps Environment
az containerapp env update \
  --name greengovrag-dev-env \
  --resource-group greengovrag-rg \
  --internal-only true
```

### Private Endpoints

Enable private endpoints for storage and database:

```bash
# Storage private endpoint
az network private-endpoint create \
  --name storage-endpoint \
  --resource-group greengovrag-rg \
  --vnet-name greengovrag-vnet \
  --subnet container-subnet \
  --private-connection-resource-id <storage-id> \
  --connection-name storage-connection \
  --group-id blob
```

## Troubleshooting

### Container App Won't Start

1. Check logs:
   ```bash
   az containerapp logs show \
     --name greengovrag-dev-ui \
     --resource-group greengovrag-rg \
     --tail 100
   ```

2. Verify environment variables are set correctly
3. Check managed identity has correct permissions
4. Ensure container image is accessible

### Storage Access Issues

1. Verify managed identity has "Storage Blob Data Contributor" role
2. Check storage firewall allows Container Apps
3. Verify connection string is correct

### Database Connection Issues

1. Check firewall rules allow Container Apps
2. Verify credentials in Key Vault
3. Test connection from Container App console

## Cleanup

### Delete Everything

```bash
az group delete --name greengovrag-rg --yes --no-wait
```

### Delete Specific Resources

```bash
# Delete container apps
az containerapp delete --name greengovrag-dev-ui --resource-group greengovrag-rg --yes
az containerapp delete --name greengovrag-dev-api --resource-group greengovrag-rg --yes

# Delete database
az postgres flexible-server delete --name greengovrag-dev-postgres --resource-group greengovrag-rg --yes

# Delete storage
az storage account delete --name <storage-account> --resource-group greengovrag-rg --yes
```

## Support

For issues or questions:
- [Azure Container Apps Documentation](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Bicep Documentation](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)
- [Project GitHub Issues](https://github.com/sdp5/green-gov-rag/issues)

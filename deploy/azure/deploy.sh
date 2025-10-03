#!/bin/bash
# Deployment script for Azure infrastructure

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-greengovrag-rg}"
LOCATION="${LOCATION:-australiaeast}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== GreenGovRAG Azure Deployment ===${NC}"

# Check prerequisites
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}Not logged in to Azure. Logging in...${NC}"
    az login
fi

# Set subscription if provided
if [ -n "$SUBSCRIPTION_ID" ]; then
    echo -e "${YELLOW}Setting subscription to: $SUBSCRIPTION_ID${NC}"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# Show current subscription
CURRENT_SUB=$(az account show --query name -o tsv)
echo -e "${GREEN}Using subscription: $CURRENT_SUB${NC}"

# Create resource group if it doesn't exist
echo -e "${YELLOW}Creating resource group: $RESOURCE_GROUP in $LOCATION${NC}"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Prompt for secrets if not set
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${YELLOW}Enter PostgreSQL admin password:${NC}"
    read -s POSTGRES_PASSWORD
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${YELLOW}Enter OpenAI API Key:${NC}"
    read -s OPENAI_API_KEY
fi

# Deploy infrastructure
echo -e "${GREEN}Deploying infrastructure...${NC}"
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file main.bicep \
  --parameters \
    projectName=greengovrag \
    environment="$ENVIRONMENT" \
    location="$LOCATION" \
    postgresPassword="$POSTGRES_PASSWORD" \
    openaiApiKey="$OPENAI_API_KEY"

# Get outputs
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Retrieving deployment outputs...${NC}"

STORAGE_ACCOUNT=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.storageAccountName.value -o tsv)

API_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.apiUrl.value -o tsv)

UI_URL=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.uiUrl.value -o tsv)

ACR_LOGIN_SERVER=$(az deployment group show \
  --resource-group "$RESOURCE_GROUP" \
  --name main \
  --query properties.outputs.containerRegistryLoginServer.value -o tsv)

echo -e "${GREEN}=== Deployment Summary ===${NC}"
echo "Resource Group: $RESOURCE_GROUP"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Container Registry: $ACR_LOGIN_SERVER"
echo "API URL: $API_URL"
echo "UI URL: $UI_URL"

echo -e "${YELLOW}Next steps:${NC}"
echo "1. Build and push Docker images:"
echo "   az acr login --name ${ACR_LOGIN_SERVER%%.*}"
echo "   docker build -t $ACR_LOGIN_SERVER/greengovrag-api:latest -f deploy/docker/api/Dockerfile ."
echo "   docker build -t $ACR_LOGIN_SERVER/greengovrag-ui:latest -f deploy/docker/streamlit/Dockerfile ."
echo "   docker push $ACR_LOGIN_SERVER/greengovrag-api:latest"
echo "   docker push $ACR_LOGIN_SERVER/greengovrag-ui:latest"
echo ""
echo "2. Update container apps to use the new images"
echo "3. Access the UI at: $UI_URL"

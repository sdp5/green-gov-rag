#!/bin/bash
set -e

# Azure deployment script for GreenGovRAG Hybrid Architecture
# Deploys: Container Apps, PostgreSQL, Static Web App, Spot VM for Qdrant

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== GreenGovRAG Azure Deployment ===${NC}"

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-greengovrag-production-rg}"
LOCATION="${LOCATION:-eastus}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not installed${NC}"
    exit 1
fi

# Check login
echo -e "${BLUE}Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    az login
fi

SUBSCRIPTION=$(az account show --query id -o tsv)
echo -e "${GREEN}Subscription: $SUBSCRIPTION${NC}"

# Get parameters
read -sp "PostgreSQL password: " POSTGRES_PASSWORD
echo
read -sp "OpenAI API key: " OPENAI_API_KEY
echo
read -p "MapBox token (optional): " MAPBOX_TOKEN

# Create resource group
echo -e "${BLUE}Creating resource group...${NC}"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

# Deploy infrastructure
echo -e "${BLUE}Deploying infrastructure (this may take 10-15 minutes)...${NC}"
OUTPUTS=$(az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "$SCRIPT_DIR/main.bicep" \
    --parameters \
        environment="$ENVIRONMENT" \
        postgresPassword="$POSTGRES_PASSWORD" \
        openaiApiKey="$OPENAI_API_KEY" \
        mapboxToken="$MAPBOX_TOKEN" \
    --query properties.outputs \
    --output json)

echo -e "${GREEN}✓ Infrastructure deployed${NC}"

# Parse outputs
API_URL=$(echo "$OUTPUTS" | jq -r '.apiUrl.value')
FRONTEND_URL=$(echo "$OUTPUTS" | jq -r '.frontendUrl.value')
STORAGE_ACCOUNT=$(echo "$OUTPUTS" | jq -r '.storageAccountName.value')
STATIC_WEB_APP=$(echo "$OUTPUTS" | jq -r '.staticWebAppName.value')
POSTGRES_HOST=$(echo "$OUTPUTS" | jq -r '.postgresHost.value')

# Display results
echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo -e "${BLUE}API URL:${NC} $API_URL"
echo -e "${BLUE}Frontend URL:${NC} $FRONTEND_URL"
echo -e "${BLUE}Storage:${NC} $STORAGE_ACCOUNT"
echo -e "${BLUE}Database:${NC} $POSTGRES_HOST"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Build and push backend container"
echo "2. Deploy frontend to Static Web App"
echo "3. Run ETL pipeline via GitHub Actions"
echo ""
echo -e "${BLUE}Monthly cost: ~\$45${NC}"

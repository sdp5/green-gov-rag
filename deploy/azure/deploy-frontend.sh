#!/bin/bash
set -e

# Script to build and deploy frontend to Azure Static Web App
# This script should be run after Bicep deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GreenGovRAG Frontend Build for Azure Static Web App ===${NC}"

# Parse arguments
RESOURCE_GROUP="${1:-greengovrag-dev-rg}"
STATIC_WEB_APP_NAME="${2:-greengovrag-dev-frontend}"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${RED}Error: Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed${NC}"
    exit 1
fi

# Get API URL from Azure deployment outputs
echo -e "${BLUE}Fetching API URL from Azure deployment...${NC}"
API_URL=$(az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "greengovrag-deployment" \
    --query "properties.outputs.apiUrl.value" \
    --output tsv 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}Warning: Could not fetch API URL from deployment. Using placeholder.${NC}"
    API_URL="https://REPLACE_WITH_API_URL/api"
fi

# Get MapBox token from environment or use empty string
VITE_MAPBOX_TOKEN="${VITE_MAPBOX_TOKEN:-}"

echo -e "${GREEN}Building frontend...${NC}"
cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing npm dependencies...${NC}"
    npm install
fi

# Build the frontend
echo -e "${BLUE}Running production build...${NC}"
npm run build

# Generate config.js with actual values
echo -e "${GREEN}Generating runtime configuration...${NC}"
TEMPLATE_FILE="$FRONTEND_DIR/public/config.template.js"
OUTPUT_FILE="$FRONTEND_DIR/dist/config.js"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${YELLOW}Warning: config.template.js not found. Creating default config.js${NC}"
    cat > "$OUTPUT_FILE" << EOF
// Runtime configuration for GreenGovRAG frontend
window.__RUNTIME_CONFIG__ = {
  API_URL: '$API_URL',
  MAPBOX_TOKEN: '$VITE_MAPBOX_TOKEN'
};
EOF
else
    # Use envsubst to replace variables in template
    export VITE_API_URL="$API_URL"
    export VITE_MAPBOX_TOKEN
    envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"
fi

echo -e "${GREEN}✓ Frontend build complete${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  API_URL: $API_URL"
echo -e "  MAPBOX_TOKEN: ${VITE_MAPBOX_TOKEN:0:10}..."
echo ""

# Deploy to Azure Static Web App
echo -e "${BLUE}Deploying to Azure Static Web App...${NC}"

# Get deployment token
DEPLOYMENT_TOKEN=$(az staticwebapp secrets list \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.apiKey" \
    --output tsv)

if [ -z "$DEPLOYMENT_TOKEN" ]; then
    echo -e "${RED}Error: Could not retrieve deployment token for Static Web App${NC}"
    exit 1
fi

# Check if SWA CLI is installed
if ! command -v swa &> /dev/null; then
    echo -e "${YELLOW}Installing Azure Static Web Apps CLI...${NC}"
    npm install -g @azure/static-web-apps-cli
fi

# Deploy using SWA CLI
echo -e "${BLUE}Uploading build to Azure...${NC}"
swa deploy \
    --app-location "$FRONTEND_DIR/dist" \
    --deployment-token "$DEPLOYMENT_TOKEN" \
    --env production

echo -e "${GREEN}✓ Deployment complete${NC}"
echo ""

# Get the Static Web App URL
FRONTEND_URL=$(az staticwebapp show \
    --name "$STATIC_WEB_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "defaultHostname" \
    --output tsv)

echo -e "${GREEN}Frontend URL: https://$FRONTEND_URL${NC}"
echo ""
echo -e "${YELLOW}Note: Static Web App settings are managed in Azure Bicep template${NC}"
echo -e "${YELLOW}If you need to update runtime config, modify the staticWebAppSettings resource${NC}"

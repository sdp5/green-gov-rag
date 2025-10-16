#!/bin/bash
set -e

# Script to build and deploy frontend to AWS CloudFront
# This script should be run before CDK deployment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== GreenGovRAG Frontend Build for AWS CloudFront ===${NC}"

# Check if frontend directory exists
if [ ! -d "$FRONTEND_DIR" ]; then
    echo -e "${YELLOW}Error: Frontend directory not found at $FRONTEND_DIR${NC}"
    exit 1
fi

# Get environment variables (with defaults)
VITE_API_URL="${VITE_API_URL:-}"
VITE_MAPBOX_TOKEN="${VITE_MAPBOX_TOKEN:-}"

# If API URL not provided, try to get it from CDK outputs
if [ -z "$VITE_API_URL" ]; then
    echo -e "${YELLOW}VITE_API_URL not set. You'll need to update config.js manually after getting the ALB URL from CDK outputs.${NC}"
    VITE_API_URL="https://REPLACE_WITH_ALB_URL/api"
fi

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

# Generate config.js from template
echo -e "${GREEN}Generating runtime configuration...${NC}"
TEMPLATE_FILE="$FRONTEND_DIR/public/config.template.js"
OUTPUT_FILE="$FRONTEND_DIR/dist/config.js"

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${YELLOW}Warning: config.template.js not found. Creating default config.js${NC}"
    cat > "$OUTPUT_FILE" << EOF
// Runtime configuration for GreenGovRAG frontend
window.__RUNTIME_CONFIG__ = {
  API_URL: '$VITE_API_URL',
  MAPBOX_TOKEN: '$VITE_MAPBOX_TOKEN'
};
EOF
else
    # Use envsubst to replace variables in template
    export VITE_API_URL
    export VITE_MAPBOX_TOKEN
    envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"
fi

echo -e "${GREEN}✓ Frontend build complete${NC}"
echo -e "${BLUE}Build output: $FRONTEND_DIR/dist${NC}"
echo -e "${BLUE}Config file: $OUTPUT_FILE${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo -e "  API_URL: $VITE_API_URL"
echo -e "  MAPBOX_TOKEN: ${VITE_MAPBOX_TOKEN:0:10}..."
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review the generated config.js"
echo -e "  2. If VITE_API_URL is placeholder, update it after CDK deployment"
echo -e "  3. Run CDK deployment: cd deploy/aws && cdk deploy"
echo -e "  4. If needed, manually upload dist/ to S3 or re-run this script with correct API_URL"

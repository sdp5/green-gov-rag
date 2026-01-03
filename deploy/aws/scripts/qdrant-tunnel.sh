#!/bin/bash
# Qdrant Vector Database Tunnel via SSM
# Forwards Qdrant port to localhost
#
# Usage: ./scripts/qdrant-tunnel.sh
#
# Access Qdrant:
#   Web UI:  http://localhost:6333/dashboard
#   API:     http://localhost:6333
#   Metrics: http://localhost:6333/metrics

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Qdrant Vector Database Tunnel via SSM${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Fetching stack outputs...${NC}"
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`QdrantInstanceId`].OutputValue' \
  --output text 2>/dev/null)

QDRANT_API_KEY=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`QdrantApiKey`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$INSTANCE_ID" ]; then
  echo -e "${YELLOW}Error: Could not retrieve stack outputs${NC}"
  echo "Make sure the GreenGovRAGStack is deployed and you have AWS credentials configured"
  exit 1
fi

echo -e "${GREEN}✓ Instance ID: $INSTANCE_ID${NC}"
echo ""

echo -e "${BLUE}Access Qdrant:${NC}"
echo "  Web UI:      http://localhost:6333/dashboard"
echo "  API:         http://localhost:6333"
echo "  Collections: http://localhost:6333/collections"
echo "  Metrics:     http://localhost:6333/metrics"
echo ""

if [ -n "$QDRANT_API_KEY" ]; then
  echo -e "${BLUE}API Key (add to requests as header):${NC}"
  echo "  X-API-Key: $QDRANT_API_KEY"
  echo ""
fi

echo -e "${BLUE}Example API calls:${NC}"
echo "  # List collections"
echo "  curl http://localhost:6333/collections"
echo ""
echo "  # Search vectors (with API key if configured)"
if [ -n "$QDRANT_API_KEY" ]; then
  echo "  curl -H 'api-key: $QDRANT_API_KEY' http://localhost:6333/collections"
else
  echo "  curl http://localhost:6333/collections"
fi
echo ""

echo -e "${YELLOW}Starting SSM port forwarding session...${NC}"
echo -e "${YELLOW}Press Ctrl+C to close tunnel${NC}"
echo ""

# Forward Qdrant port
aws ssm start-session \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "{\"portNumber\":[\"6333\"],\"localPortNumber\":[\"6333\"]}"
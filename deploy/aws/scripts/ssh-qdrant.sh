#!/bin/bash
# SSH to Qdrant EC2 Instance via SSM
# Interactive shell access to manage Qdrant container
#
# Usage: ./scripts/ssh-qdrant.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  SSH to Qdrant EC2 Instance via SSM${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Fetching instance ID...${NC}"
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`QdrantInstanceId`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$INSTANCE_ID" ]; then
  echo -e "${YELLOW}Error: Could not retrieve instance ID${NC}"
  echo "Make sure the GreenGovRAGStack is deployed and you have AWS credentials configured"
  exit 1
fi

echo -e "${GREEN}✓ Instance ID: $INSTANCE_ID${NC}"
echo ""

echo -e "${BLUE}Useful commands once connected:${NC}"
echo "  docker ps              # Check Qdrant container status"
echo "  docker logs qdrant     # View Qdrant logs"
echo "  docker logs -f qdrant  # Follow Qdrant logs"
echo "  docker restart qdrant  # Restart Qdrant"
echo "  docker exec -it qdrant sh  # Access Qdrant container shell"
echo ""
echo "  ls -la /qdrant/storage     # Check vector data"
echo "  df -h | grep qdrant        # Check disk usage"
echo "  curl http://localhost:6333/collections  # Query Qdrant API"
echo ""

echo -e "${YELLOW}Starting SSM session...${NC}"
echo -e "${YELLOW}Type 'exit' to disconnect${NC}"
echo ""

# Start interactive session
aws ssm start-session --target "$INSTANCE_ID"
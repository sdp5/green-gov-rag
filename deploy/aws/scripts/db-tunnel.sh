#!/bin/bash
# PostgreSQL Database Tunnel via SSM
# Forwards RDS PostgreSQL port to localhost via Qdrant EC2 instance
#
# Usage: ./scripts/db-tunnel.sh
#
# Connect with pgAdmin or psql:
#   Host: localhost
#   Port: 5432
#   Database: greengovrag
#   Username: postgres
#   Password: <from your secrets>

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  PostgreSQL Database Tunnel via SSM${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Fetching stack outputs...${NC}"
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`QdrantInstanceId`].OutputValue' \
  --output text 2>/dev/null)

DB_HOST=$(aws cloudformation describe-stacks \
  --stack-name GreenGovRAGStack \
  --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$INSTANCE_ID" ] || [ -z "$DB_HOST" ]; then
  echo -e "${YELLOW}Error: Could not retrieve stack outputs${NC}"
  echo "Make sure the GreenGovRAGStack is deployed and you have AWS credentials configured"
  exit 1
fi

echo -e "${GREEN}✓ Instance ID: $INSTANCE_ID${NC}"
echo -e "${GREEN}✓ RDS Endpoint: $DB_HOST${NC}"
echo ""

echo -e "${BLUE}Connection Details:${NC}"
echo "  Host:     localhost"
echo "  Port:     5432"
echo "  Database: greengovrag"
echo "  Username: postgres"
echo "  Password: <from your AWS secrets>"
echo ""

echo -e "${BLUE}Example psql connection:${NC}"
echo "  psql -h localhost -p 5432 -U postgres -d greengovrag"
echo ""

echo -e "${YELLOW}Starting SSM port forwarding session...${NC}"
echo -e "${YELLOW}Press Ctrl+C to close tunnel${NC}"
echo ""

# Forward RDS port through Qdrant EC2 instance
aws ssm start-session \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$DB_HOST\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"5432\"]}"
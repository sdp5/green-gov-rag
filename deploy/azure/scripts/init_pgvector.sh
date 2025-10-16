#!/usr/bin/env bash
#
# Azure PostgreSQL pgvector Extension Initialization Script
#
# This script automatically installs the pgvector extension in Azure PostgreSQL
# Flexible Server after deployment.
#
# Usage:
#   ./init_pgvector.sh <resource-group> <server-name> <database-name> <admin-password>
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ "$#" -lt 3 ]; then
    log_error "Usage: $0 <resource-group> <server-name> <database-name> [admin-password]"
    log_info "Example: $0 greengovrag-rg greengovrag-dev-postgres greengovrag"
    exit 1
fi

RESOURCE_GROUP=$1
SERVER_NAME=$2
DATABASE_NAME=$3
ADMIN_PASSWORD=${4:-""}

log_info "Initializing pgvector extension for Azure PostgreSQL..."
log_info "Resource Group: $RESOURCE_GROUP"
log_info "Server: $SERVER_NAME"
log_info "Database: $DATABASE_NAME"

# Get server details
log_info "Retrieving server details..."
SERVER_FQDN=$(az postgres flexible-server show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SERVER_NAME" \
    --query "fullyQualifiedDomainName" \
    --output tsv)

if [ -z "$SERVER_FQDN" ]; then
    log_error "Failed to retrieve server FQDN"
    exit 1
fi

log_info "Server FQDN: $SERVER_FQDN"

# Check if pgvector is already enabled in server parameters
log_info "Checking if vector extension is enabled in server configuration..."
EXTENSIONS=$(az postgres flexible-server parameter show \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$SERVER_NAME" \
    --name "azure.extensions" \
    --query "value" \
    --output tsv)

if [[ ! "$EXTENSIONS" =~ "VECTOR" ]]; then
    log_warn "Vector extension not enabled in server configuration"
    log_info "Enabling vector extension..."

    # Enable vector extension in server configuration
    az postgres flexible-server parameter set \
        --resource-group "$RESOURCE_GROUP" \
        --server-name "$SERVER_NAME" \
        --name "azure.extensions" \
        --value "VECTOR,POSTGIS" \
        --output none

    log_info "Vector extension enabled in server configuration ✓"
    log_warn "Server may need to restart for changes to take effect"
    log_info "Waiting 30 seconds for server to apply changes..."
    sleep 30
else
    log_info "Vector extension already enabled in server configuration ✓"
fi

# Get admin password if not provided
if [ -z "$ADMIN_PASSWORD" ]; then
    log_warn "Admin password not provided"
    read -sp "Enter PostgreSQL admin password: " ADMIN_PASSWORD
    echo
fi

# Check if psql is available
if ! command -v psql &> /dev/null; then
    log_error "psql command not found"
    log_info "Install PostgreSQL client:"
    log_info "  Ubuntu/Debian: sudo apt-get install postgresql-client"
    log_info "  macOS: brew install postgresql"
    log_info "  Or use Azure Cloud Shell which has psql pre-installed"
    exit 1
fi

# Create pgvector extension in database
log_info "Creating pgvector extension in database..."

PGPASSWORD="$ADMIN_PASSWORD" psql \
    -h "$SERVER_FQDN" \
    -U "dbadmin" \
    -d "$DATABASE_NAME" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" \
    2>&1 | tee /tmp/pgvector_init.log

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_info "pgvector extension created successfully ✓"

    # Verify installation
    VERSION=$(PGPASSWORD="$ADMIN_PASSWORD" psql \
        -h "$SERVER_FQDN" \
        -U "dbadmin" \
        -d "$DATABASE_NAME" \
        -t \
        -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';" \
        2>/dev/null | xargs)

    if [ -n "$VERSION" ]; then
        log_info "pgvector version: $VERSION"
    fi

    echo ""
    log_info "========================================="
    log_info "  pgvector Extension Setup Complete"
    log_info "========================================="
    log_info "Database: $DATABASE_NAME"
    log_info "Host: $SERVER_FQDN"
    log_info "Status: Ready for vector operations"
    log_info "========================================="
else
    log_error "Failed to create pgvector extension"
    log_error "Check log: /tmp/pgvector_init.log"
    exit 1
fi

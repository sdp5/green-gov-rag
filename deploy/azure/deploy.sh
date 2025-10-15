#!/usr/bin/env bash
set -euo pipefail

# Green Gov RAG - Azure Deployment Script
# This script deploys the application to Azure using Bicep

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-greengovrag-rg}"
LOCATION="${LOCATION:-australiaeast}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed"
        echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    log_info "All prerequisites met ✓"
}

# Login and set subscription
setup_azure_account() {
    log_info "Setting up Azure account..."

    # Check if logged in
    if ! az account show &> /dev/null; then
        log_warn "Not logged in to Azure. Logging in..."
        az login
    fi

    # Set subscription if provided
    if [ -n "${AZURE_SUBSCRIPTION_ID:-}" ]; then
        log_info "Setting subscription to: $AZURE_SUBSCRIPTION_ID"
        az account set --subscription "$AZURE_SUBSCRIPTION_ID"
    fi

    CURRENT_SUB=$(az account show --query name -o tsv)
    log_info "Using subscription: $CURRENT_SUB"
}

# Create resource group
create_resource_group() {
    log_info "Creating resource group: $RESOURCE_GROUP in $LOCATION..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
    log_info "Resource group created ✓"
}

# Collect secrets
collect_secrets() {
    log_info "Collecting required secrets..."

    # PostgreSQL password
    if [ -z "${POSTGRES_PASSWORD:-}" ]; then
        log_warn "PostgreSQL password not set"
        read -p "Enter PostgreSQL admin password: " -s POSTGRES_PASSWORD
        echo
        export POSTGRES_PASSWORD
    fi

    # OpenAI API Key
    if [ -z "${OPENAI_API_KEY:-}" ]; then
        log_warn "OpenAI API key not set"
        read -p "Enter OpenAI API key: " -s OPENAI_API_KEY
        echo
        export OPENAI_API_KEY
    fi

    # MapBox Token
    if [ -z "${MAPBOX_TOKEN:-}" ]; then
        log_warn "MapBox token not set"
        read -p "Enter MapBox access token: " -s MAPBOX_TOKEN
        echo
        export MAPBOX_TOKEN
    fi

    log_info "Secrets collected ✓"
}

# Deploy infrastructure with Bicep
deploy_infrastructure() {
    log_info "Deploying infrastructure with Bicep (this may take 10-15 minutes)..."

    cd "$SCRIPT_DIR"

    az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file main.bicep \
        --parameters \
            projectName=greengovrag \
            environment="$ENVIRONMENT" \
            location="$LOCATION" \
            postgresPassword="$POSTGRES_PASSWORD" \
            openaiApiKey="$OPENAI_API_KEY" \
            mapboxToken="$MAPBOX_TOKEN" \
        --output table

    log_info "Infrastructure deployed ✓"
}

# Get deployment outputs
get_deployment_outputs() {
    log_info "Retrieving deployment outputs..."

    DEPLOYMENT_NAME=$(az deployment group list \
        --resource-group "$RESOURCE_GROUP" \
        --query "[0].name" \
        --output tsv)

    ACR_LOGIN_SERVER=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs.containerRegistryLoginServer.value \
        --output tsv)

    POSTGRES_HOST=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs.postgresHost.value \
        --output tsv)

    API_URL=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs.apiUrl.value \
        --output tsv)

    FRONTEND_URL=$(az deployment group show \
        --resource-group "$RESOURCE_GROUP" \
        --name "$DEPLOYMENT_NAME" \
        --query properties.outputs.frontendUrl.value \
        --output tsv)

    export ACR_LOGIN_SERVER POSTGRES_HOST API_URL FRONTEND_URL
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."

    # Login to ACR
    log_info "Logging in to Azure Container Registry..."
    ACR_NAME=$(echo "$ACR_LOGIN_SERVER" | cut -d'.' -f1)
    az acr login --name "$ACR_NAME"

    cd "$PROJECT_ROOT"

    # Build and push backend
    log_info "Building backend image..."
    docker build -t "$ACR_LOGIN_SERVER/greengovrag-api:latest" \
        -f deploy/docker/backend.Dockerfile \
        .

    log_info "Pushing backend image..."
    docker push "$ACR_LOGIN_SERVER/greengovrag-api:latest"

    # Build and push frontend
    log_info "Building frontend image..."
    docker build -t "$ACR_LOGIN_SERVER/greengovrag-frontend:latest" \
        -f deploy/docker/frontend.Dockerfile \
        .

    log_info "Pushing frontend image..."
    docker push "$ACR_LOGIN_SERVER/greengovrag-frontend:latest"

    log_info "Docker images pushed ✓"
}

# Update container apps with new images
update_container_apps() {
    log_info "Updating container apps..."

    # Update API container
    az containerapp update \
        --name "greengovrag-${ENVIRONMENT}-api" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_LOGIN_SERVER/greengovrag-api:latest" \
        --output none

    # Update Frontend container
    az containerapp update \
        --name "greengovrag-${ENVIRONMENT}-frontend" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_LOGIN_SERVER/greengovrag-frontend:latest" \
        --output none

    log_info "Container apps updated ✓"
}

# Initialize database with extensions
initialize_database() {
    log_info "Initializing database extensions..."

    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        log_warn "psql not found. Please install PostgreSQL client to initialize database."
        log_warn "Extensions will be created automatically by the Azure configuration."
        return
    fi

    # Create extensions using psql
    log_info "Creating vector and postgis extensions..."
    PGPASSWORD="$POSTGRES_PASSWORD" psql \
        -h "$POSTGRES_HOST" \
        -U dbadmin \
        -d greengovrag \
        <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'postgis');
EOF

    log_info "Database extensions verified ✓"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    export DATABASE_URL="postgresql://dbadmin:$POSTGRES_PASSWORD@$POSTGRES_HOST:5432/greengovrag"

    cd "$PROJECT_ROOT/backend"

    # Check if alembic is installed
    if ! python3 -c "import alembic" &>/dev/null; then
        log_info "Installing alembic..."
        pip install -q alembic psycopg2-binary
    fi

    log_info "Running alembic upgrade..."
    python3 -m alembic upgrade head

    log_info "Migrations completed ✓"
}

# Display deployment information
show_deployment_info() {
    log_info "Deployment complete! 🎉"
    echo
    echo "========================================="
    echo "  GreenGovRAG Deployment Information"
    echo "========================================="
    echo
    echo "Frontend URL:    $FRONTEND_URL"
    echo "API URL:         $API_URL"
    echo "Database Host:   $POSTGRES_HOST"
    echo
    echo "To view logs:"
    echo "  az containerapp logs show --name greengovrag-${ENVIRONMENT}-frontend --resource-group $RESOURCE_GROUP --follow"
    echo "  az containerapp logs show --name greengovrag-${ENVIRONMENT}-api --resource-group $RESOURCE_GROUP --follow"
    echo
    echo "To update images:"
    echo "  ./deploy.sh"
    echo
    echo "To destroy deployment:"
    echo "  az group delete --name $RESOURCE_GROUP --yes"
    echo
    echo "========================================="
}

# Main execution
main() {
    log_info "Starting GreenGovRAG Azure deployment..."
    echo

    check_prerequisites
    setup_azure_account
    create_resource_group
    collect_secrets

    # First deployment: create infrastructure
    if [ "${SKIP_INFRA:-false}" != "true" ]; then
        deploy_infrastructure
    fi

    get_deployment_outputs
    build_and_push_images

    # Update container apps only on subsequent deployments
    if [ "${SKIP_INFRA:-false}" == "true" ]; then
        update_container_apps
    fi

    log_info "Waiting for services to stabilize..."
    sleep 30

    initialize_database
    run_migrations

    show_deployment_info
}

# Run main function
main "$@"

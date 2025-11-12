#!/usr/bin/env bash
set -euo pipefail

# GreenGovRAG - AWS Backend Deployment Script
# This script performs initial deployment of the backend to AWS using CDK
# For subsequent deployments, use GitHub Actions workflow (aws-deploy-backend.yml)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

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

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check CDK
    if ! command -v cdk &> /dev/null; then
        log_error "AWS CDK is not installed. Run: npm install -g aws-cdk"
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        exit 1
    fi

    log_info "All prerequisites met ✓"
}

# Set AWS environment variables
setup_aws_env() {
    log_info "Setting up AWS environment..."

    # Get AWS account ID
    export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    export CDK_DEFAULT_REGION=${AWS_REGION:-ap-southeast-2}

    log_info "AWS Account: $CDK_DEFAULT_ACCOUNT"
    log_info "AWS Region: $CDK_DEFAULT_REGION"
}

# Bootstrap CDK (first time only)
bootstrap_cdk() {
    log_info "Bootstrapping CDK (if not already done)..."
    cdk bootstrap aws://$CDK_DEFAULT_ACCOUNT/$CDK_DEFAULT_REGION
}

# Deploy CDK stack
deploy_stack() {
    log_info "Deploying CDK stack..."
    cd "$SCRIPT_DIR"

    # Install Python dependencies for CDK
    pip install -q -r requirements.txt 2>/dev/null || true

    # Get API access key from environment or prompt
    if [ -z "$API_ACCESS_KEY" ]; then
        log_warn "API_ACCESS_KEY not set in environment"
        read -p "Enter API access key for production (or press Enter to use default): " -s API_ACCESS_KEY
        echo
        if [ -z "$API_ACCESS_KEY" ]; then
            API_ACCESS_KEY="REPLACE_ME"
            log_warn "Using placeholder API key. Update via GitHub Secrets before production use."
        fi
    fi

    # Get database password from environment or prompt
    if [ -z "${SQL_DB_PASSWORD:-}" ]; then
        log_warn "SQL_DB_PASSWORD not set in environment"
        read -p "Enter database password (or press Enter to auto-generate): " -s SQL_DB_PASSWORD
        echo
        if [ -z "$SQL_DB_PASSWORD" ]; then
            SQL_DB_PASSWORD=$(openssl rand -base64 32)
            log_info "Generated random database password"
        fi
    fi

    # Export for use by initialize_database and run_migrations
    export SQL_DB_PASSWORD

    # Synthesize stack
    log_info "Synthesizing CloudFormation template..."
    cdk synth --context api_access_key="$API_ACCESS_KEY" \
              --context sql_db_password="$SQL_DB_PASSWORD"

    # Deploy
    log_info "Deploying to AWS (this may take 15-20 minutes)..."
    cdk deploy --require-approval never \
        --context api_access_key="$API_ACCESS_KEY" \
        --context sql_db_password="$SQL_DB_PASSWORD"

    log_info "Stack deployed successfully ✓"
}

# Initialize database with PostGIS and pgvector extensions
initialize_database() {
    log_info "Initializing database extensions..."

    # Get database endpoint from CDK outputs
    DB_HOST=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    if [ -z "$DB_HOST" ]; then
        log_warn "Could not retrieve database endpoint. Skipping database initialization."
        log_warn "You may need to manually run database migrations."
        return
    fi

    log_info "Database host: $DB_HOST"

    # Use credentials from deploy_stack
    DB_USER="postgres"
    DB_PASSWORD="$SQL_DB_PASSWORD"
    DB_NAME="greengovrag"

    # Install psql if not available
    if ! command -v psql &> /dev/null; then
        log_warn "psql not found. Please install PostgreSQL client to initialize database."
        log_warn "Run manually: PGPASSWORD='***' psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c 'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS postgis;'"
        return
    fi

    # Create extensions
    log_info "Creating vector and postgis extensions..."
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS postgis;
\dx
EOF

    log_info "Database extensions created ✓"
}

# Run Alembic migrations
run_migrations() {
    log_info "Running database migrations..."

    # Get database endpoint from CDK outputs
    DB_HOST=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='DatabaseEndpoint'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    if [ -z "$DB_HOST" ]; then
        log_warn "Could not retrieve database endpoint. Skipping migrations."
        return
    fi

    # Use credentials from deploy_stack
    DB_USER="postgres"
    DB_PASSWORD="$SQL_DB_PASSWORD"

    export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:5432/greengovrag"

    # Run migrations from backend directory
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

# Display deployment info
show_deployment_info() {
    log_info "Deployment complete! 🎉"
    echo
    log_info "Retrieving deployment information..."

    APP_URL=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='ApplicationURL'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    API_URL=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='ApiURL'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    echo
    echo "========================================="
    echo "  GreenGovRAG Deployment Information"
    echo "========================================="
    echo
    echo "Application URL: $APP_URL"
    echo "API URL:         $API_URL"
    echo
    echo "To view logs:"
    echo "  aws logs tail /aws/ecs/greengovrag --follow --region $CDK_DEFAULT_REGION"
    echo
    echo "To update the deployment:"
    echo "  cd deploy/aws && cdk deploy"
    echo
    echo "To destroy the deployment:"
    echo "  cd deploy/aws && cdk destroy"
    echo
    echo "========================================="
}

# Main execution
main() {
    log_info "Starting GreenGovRAG AWS deployment..."
    echo

    check_prerequisites
    setup_aws_env
    bootstrap_cdk
    deploy_stack

    log_info "Waiting for stack to stabilize..."
    sleep 30

    initialize_database
    run_migrations

    show_deployment_info
}

# Run main function
main "$@"

#!/usr/bin/env bash
set -euo pipefail

# Green Gov RAG - AWS Deployment Script
# This script deploys the application to AWS using CDK

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

# Create required secrets in AWS Secrets Manager
create_secrets() {
    log_info "Checking required secrets..."

    # Check OpenAI API Key
    if ! aws secretsmanager describe-secret --secret-id greengovrag/openai-api-key --region $CDK_DEFAULT_REGION &>/dev/null; then
        log_warn "Secret 'greengovrag/openai-api-key' not found"
        read -p "Enter your OpenAI API key: " -s OPENAI_KEY
        echo
        aws secretsmanager create-secret \
            --name greengovrag/openai-api-key \
            --secret-string "$OPENAI_KEY" \
            --region $CDK_DEFAULT_REGION
        log_info "Created OpenAI API key secret ✓"
    else
        log_info "OpenAI API key secret exists ✓"
    fi

    # Check MapBox Token
    if ! aws secretsmanager describe-secret --secret-id greengovrag/mapbox-token --region $CDK_DEFAULT_REGION &>/dev/null; then
        log_warn "Secret 'greengovrag/mapbox-token' not found"
        read -p "Enter your MapBox access token: " -s MAPBOX_TOKEN
        echo
        aws secretsmanager create-secret \
            --name greengovrag/mapbox-token \
            --secret-string "$MAPBOX_TOKEN" \
            --region $CDK_DEFAULT_REGION
        log_info "Created MapBox token secret ✓"
    else
        log_info "MapBox token secret exists ✓"
    fi
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

    # Synthesize stack
    log_info "Synthesizing CloudFormation template..."
    cdk synth

    # Deploy
    log_info "Deploying to AWS (this may take 15-20 minutes)..."
    cdk deploy --require-approval never

    log_info "Stack deployed successfully ✓"
}

# Initialize database with PostGIS and pgvector extensions
initialize_database() {
    log_info "Initializing database extensions..."

    # Get database details from CDK outputs
    DB_SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    DB_HOST=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='DatabaseHost'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    if [ -z "$DB_SECRET_ARN" ] || [ -z "$DB_HOST" ]; then
        log_warn "Could not retrieve database details. Skipping database initialization."
        log_warn "You may need to manually run database migrations."
        return
    fi

    log_info "Database host: $DB_HOST"

    # Get database credentials
    DB_CREDENTIALS=$(aws secretsmanager get-secret-value \
        --secret-id "$DB_SECRET_ARN" \
        --region $CDK_DEFAULT_REGION \
        --query SecretString \
        --output text)

    DB_PASSWORD=$(echo $DB_CREDENTIALS | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")
    DB_USER=$(echo $DB_CREDENTIALS | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])")
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

    # Get database connection string from secrets
    DB_SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name GreenGovRAGStack \
        --query "Stacks[0].Outputs[?OutputKey=='DatabaseSecretArn'].OutputValue" \
        --output text \
        --region $CDK_DEFAULT_REGION)

    if [ -z "$DB_SECRET_ARN" ]; then
        log_warn "Could not retrieve database secret. Skipping migrations."
        return
    fi

    DB_CREDENTIALS=$(aws secretsmanager get-secret-value \
        --secret-id "$DB_SECRET_ARN" \
        --region $CDK_DEFAULT_REGION \
        --query SecretString \
        --output text)

    DB_HOST=$(echo $DB_CREDENTIALS | python3 -c "import sys, json; print(json.load(sys.stdin)['host'])")
    DB_PASSWORD=$(echo $DB_CREDENTIALS | python3 -c "import sys, json; print(json.load(sys.stdin)['password'])")
    DB_USER=$(echo $DB_CREDENTIALS | python3 -c "import sys, json; print(json.load(sys.stdin)['username'])")

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
    create_secrets
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

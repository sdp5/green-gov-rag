#!/usr/bin/env bash
set -euo pipefail

# GreenGovRAG Backend Startup Script
# This script performs health checks and runs migrations before starting the API server

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

# Check if DATABASE_URL is set
if [ -z "${DATABASE_URL:-}" ]; then
    log_error "DATABASE_URL environment variable is not set"
    exit 1
fi
log_info "DATABASE_URL configured ✓"

# Wait for PostgreSQL to be ready
log_info "Checking PostgreSQL connection..."
MAX_RETRIES=30
RETRY_COUNT=0

# Extract host and port from DATABASE_URL
# Format: postgresql://user:password@host:port/database
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

if [ -z "$DB_HOST" ] || [ -z "$DB_PORT" ]; then
    log_warn "Could not parse DATABASE_URL. Attempting direct connection..."
else
    log_info "Database host: $DB_HOST:$DB_PORT"

    # Install pg_isready if not available (lightweight PostgreSQL client)
    if ! command -v pg_isready &> /dev/null; then
        log_info "Installing postgresql-client..."
        apt-get update -qq && apt-get install -y -qq postgresql-client > /dev/null 2>&1
    fi

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            log_info "PostgreSQL is ready ✓"
            break
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        log_warn "PostgreSQL not ready (attempt $RETRY_COUNT/$MAX_RETRIES), waiting..."
        sleep 2
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_error "PostgreSQL did not become ready in time"
        exit 1
    fi
fi

# Check Qdrant connection (if using Qdrant vector store)
if [ "${VECTOR_STORE_TYPE:-faiss}" = "qdrant" ]; then
    log_info "Checking Qdrant connection..."

    if [ -z "${QDRANT_URL:-}" ]; then
        log_warn "QDRANT_URL not set but VECTOR_STORE_TYPE=qdrant. Skipping Qdrant check."
    else
        QDRANT_HOST=$(echo "$QDRANT_URL" | sed 's|http://||' | sed 's|https://||' | cut -d: -f1)
        QDRANT_PORT=$(echo "$QDRANT_URL" | sed 's|http://||' | sed 's|https://||' | cut -d: -f2 | cut -d/ -f1)

        log_info "Qdrant host: $QDRANT_HOST:$QDRANT_PORT"

        # Extended timeout for EC2 instance boot + Docker pull + Qdrant start
        QDRANT_MAX_RETRIES=120  # 120 attempts * 3s = 360 seconds (6 minutes)
        RETRY_COUNT=0
        while [ $RETRY_COUNT -lt $QDRANT_MAX_RETRIES ]; do
            if curl -sf "${QDRANT_URL}/health" > /dev/null 2>&1; then
                log_info "Qdrant is ready ✓"
                break
            fi

            RETRY_COUNT=$((RETRY_COUNT + 1))
            log_warn "Qdrant not ready (attempt $RETRY_COUNT/$QDRANT_MAX_RETRIES), waiting..."
            sleep 3
        done

        if [ $RETRY_COUNT -eq $QDRANT_MAX_RETRIES ]; then
            log_error "Qdrant did not become ready in time (waited 360 seconds / 6 minutes)"
            log_error "Continuing anyway - application will fail if Qdrant is required"
        fi
    fi
else
    log_info "Using ${VECTOR_STORE_TYPE:-faiss} vector store, skipping Qdrant check"
fi

# Run database migrations
log_info "Running database migrations..."
if [ -f "alembic.ini" ]; then
    # Use alembic directly
    alembic upgrade head || {
        log_error "Database migrations failed"
        exit 1
    }
    log_info "Database migrations completed ✓"
else
    log_warn "alembic.ini not found, skipping migrations"
fi

# Start FastAPI server
log_info "Starting FastAPI server..."
exec uvicorn green_gov_rag.api.main:app --host 0.0.0.0 --port 8000

# Installation

> Get GreenGovRAG installed on your system

## Prerequisites

- Python 3.12 or later
- pip or uv package manager
- Docker (optional, for containerized deployment)
- PostgreSQL 15+ with pgvector extension (for production)

## Installation Options

### Option 1: Docker (Recommended for Quick Start)

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag

# Copy environment file
cp backend/.env.example backend/.env
# Edit .env with your API keys and configuration

# Start all services
cd deploy/docker
docker-compose up
```

Access the API at `http://localhost:8000/docs`

### Option 2: pip Install (Development)

For local development:

```bash
# Clone the repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/backend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install package in editable mode
pip install -e .[dev]

# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
alembic upgrade head

# Start the API server
uvicorn green_gov_rag.api.main:app --reload
```

### Option 3: From Source (Advanced)

For advanced users who want full control:

```bash
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/backend

# Install with all dependencies
pip install -e .[dev,cloud,azure]
```

## Verify Installation

```bash
# Check version
python -c "import green_gov_rag; print(green_gov_rag.__version__)"

# Run health check
curl http://localhost:8000/api/health
```

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started in 5 minutes
- [Configuration](configuration.md) - Configure environment variables
- [First Query](first-query.md) - Submit your first RAG query
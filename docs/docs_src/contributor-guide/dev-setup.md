# Development Setup Guide

> Get your local development environment ready for contributing to GreenGovRAG

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [IDE Setup](#ide-setup)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## Prerequisites

### Required Software

**Python 3.12+**
```bash
# Check Python version
python3 --version
# Should output: Python 3.12.x or later

# If not installed, install via:
# Ubuntu/Debian
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip

# macOS (using Homebrew)
brew install python@3.12

# Windows (using official installer)
# Download from https://www.python.org/downloads/
```

**Git**
```bash
# Check Git version
git --version
# Should output: git version 2.x.x or later

# If not installed:
# Ubuntu/Debian
sudo apt install git

# macOS
brew install git

# Windows
# Download from https://git-scm.com/download/win
```

**Docker (Recommended)**
```bash
# Check Docker version
docker --version
docker-compose --version

# If not installed:
# Ubuntu/Debian
sudo apt install docker.io docker-compose

# macOS/Windows
# Download Docker Desktop from https://www.docker.com/products/docker-desktop
```

**PostgreSQL 15+ (Optional - for non-Docker setup)**
```bash
# Ubuntu/Debian
sudo apt install postgresql-15 postgresql-contrib-15

# macOS
brew install postgresql@15

# Windows
# Download from https://www.postgresql.org/download/windows/
```

### Optional Software

**VS Code** (Recommended IDE)
- Download from: https://code.visualstudio.com/

**PyCharm** (Alternative IDE)
- Download from: https://www.jetbrains.com/pycharm/

**Make** (for convenience commands)
```bash
# Ubuntu/Debian
sudo apt install build-essential

# macOS (included with Xcode Command Line Tools)
xcode-select --install

# Windows (via Chocolatey)
choco install make
```

### System Requirements

- **RAM**: Minimum 8GB, recommended 16GB
- **Disk Space**: At least 10GB free
- **CPU**: Modern multi-core processor
- **Network**: Stable internet connection for API calls and downloads

## Installation Methods

### Method 1: Docker Setup (Recommended)

The fastest and most reliable way to get started:

```bash
# 1. Clone the repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag

# 2. Add upstream remote (for syncing with main repo)
git remote add upstream https://github.com/sdp5/green-gov-rag.git

# 3. Copy environment file
cp backend/.env.example backend/.env

# 4. Edit environment variables (see Environment Configuration section)
nano backend/.env  # or use your preferred editor

# 5. Start all services
cd deploy/docker
docker-compose up -d

# 6. Check services are running
docker-compose ps
```

**Services started:**
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
- Qdrant (optional): `http://localhost:6333`

**Development with Airflow:**
```bash
# Start with Airflow UI for ETL development
docker-compose --profile dev up -d

# Access Airflow at http://localhost:8080
# Default credentials: airflow/airflow
```

### Method 2: Local Development Setup

For development with hot-reloading and easier debugging:

```bash
# 1. Clone the repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag

# 2. Add upstream remote
git remote add upstream https://github.com/sdp5/green-gov-rag.git

# 3. Navigate to backend
cd backend

# 4. Create virtual environment
python3.12 -m venv .venv

# 5. Activate virtual environment
# Linux/macOS
source .venv/bin/activate
# Windows
.venv\Scripts\activate

# 6. Upgrade pip
pip install --upgrade pip

# 7. Install package in editable mode with dev dependencies
pip install -e .[dev]

# 8. Copy environment file
cp .env.example .env

# 9. Edit environment variables
nano .env  # or use your preferred editor
```

**Additional cloud dependencies (optional):**
```bash
# AWS support
pip install -e .[aws]

# Azure support
pip install -e .[azure]

# All cloud providers
pip install -e .[cloud]
```

### Method 3: Advanced Setup with UV

For faster dependency resolution using the `uv` package manager:

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone repository
git clone https://github.com/sdp5/green-gov-rag.git
cd green-gov-rag/backend

# 3. Create virtual environment with uv
uv venv

# 4. Activate environment
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 5. Install dependencies with uv (much faster than pip)
uv pip install -e .[dev]
```

## Environment Configuration

### Required Environment Variables

Edit `backend/.env` with the following required variables:

```bash
# ============================================
# LLM Configuration (REQUIRED)
# ============================================

# Choose your LLM provider: openai, azure, bedrock, anthropic
LLM_PROVIDER=openai

# For OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
LLM_MODEL=gpt-4o-mini  # or gpt-4o, gpt-4-turbo

# For Azure OpenAI (if using LLM_PROVIDER=azure)
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# For Anthropic (if using LLM_PROVIDER=anthropic)
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-3-5-sonnet-20241022

# For AWS Bedrock (if using LLM_PROVIDER=bedrock)
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_DEFAULT_REGION=us-east-1
LLM_MODEL=anthropic.claude-3-sonnet-20240229-v1:0

# ============================================
# Database Configuration
# ============================================

# For Docker setup
DATABASE_URL=postgresql://greengovrag:greengovrag@localhost:5432/greengovrag

# For local PostgreSQL (if not using Docker)
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/greengovrag

# ============================================
# Vector Store Configuration
# ============================================

# Choose vector store: faiss (local dev) or qdrant (production)
VECTOR_STORE_TYPE=faiss

# For Qdrant (optional)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional, leave empty for local development

# ============================================
# Cloud Storage (Optional)
# ============================================

# Choose provider: local, aws, azure
CLOUD_PROVIDER=local

# For AWS S3
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# For Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER_NAME=your-container-name

# ============================================
# Development Settings
# ============================================

# Environment: development, staging, production
ENVIRONMENT=development

# Enable debug logging
LOG_LEVEL=DEBUG

# API settings
API_RATE_LIMIT=100/minute
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Disable authentication for local development
AUTH_ENABLED=false
```

### Optional Environment Variables

```bash
# Redis cache (optional, for faster development)
REDIS_URL=redis://localhost:6379/0

# Airflow (optional, for ETL development)
AIRFLOW_HOME=/path/to/green-gov-rag/backend/green_gov_rag/airflow
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://greengovrag:greengovrag@localhost:5432/greengovrag

# Embedding model override
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Chunk size for documents
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

### Getting API Keys

**OpenAI:**
1. Visit https://platform.openai.com/
2. Sign up or log in
3. Navigate to API keys
4. Create a new secret key
5. Copy to `OPENAI_API_KEY` in `.env`

**Anthropic:**
1. Visit https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API keys
4. Create a new key
5. Copy to `ANTHROPIC_API_KEY` in `.env`

**Azure OpenAI:**
1. Requires Azure subscription
2. Create Azure OpenAI resource in Azure Portal
3. Deploy a model (e.g., gpt-4o-mini)
4. Get endpoint and key from resource
5. Configure in `.env`

## Database Setup

### Docker Database Setup

If using Docker Compose, the database is automatically configured:

```bash
cd deploy/docker
docker-compose up -d postgres

# Verify database is running
docker-compose ps postgres

# Connect to database
docker-compose exec postgres psql -U greengovrag -d greengovrag
```

### Local PostgreSQL Setup

If running PostgreSQL locally:

```bash
# 1. Start PostgreSQL service
# Ubuntu/Debian
sudo systemctl start postgresql

# macOS
brew services start postgresql@15

# Windows
# Start from Services or PostgreSQL application

# 2. Create database user
sudo -u postgres psql
postgres=# CREATE USER greengovrag WITH PASSWORD 'greengovrag';
postgres=# CREATE DATABASE greengovrag OWNER greengovrag;
postgres=# \q

# 3. Install pgvector extension
sudo -u postgres psql -d greengovrag
greengovrag=# CREATE EXTENSION vector;
greengovrag=# \q

# 4. Verify connection
psql -U greengovrag -d greengovrag -h localhost
```

### Running Database Migrations

Once the database is set up:

```bash
cd backend

# Activate virtual environment if not already active
source .venv/bin/activate

# Run migrations
alembic upgrade head

# Verify migrations
alembic current

# Check database schema
psql -U greengovrag -d greengovrag -h localhost -c "\dt"
```

### Creating a New Migration

When you modify database models:

```bash
# Generate migration automatically
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file in backend/alembic/versions/

# Apply migration
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Running the Application

### Running with Docker

```bash
cd deploy/docker

# Start all services
docker-compose up

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Running Backend Locally

```bash
cd backend

# Activate virtual environment
source .venv/bin/activate

# Start development server with hot-reload
uvicorn green_gov_rag.api.main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience command if Make is installed
make run
```

**Alternative: Using Gunicorn (production-like)**
```bash
gunicorn green_gov_rag.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=green_gov_rag --cov-report=html

# Run specific test file
pytest tests/test_rag.py

# Run specific test function
pytest tests/test_rag.py::test_query_endpoint

# Run tests matching pattern
pytest -k "test_vector"

# Run only unit tests (skip integration)
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Running Linters and Formatters

```bash
cd backend

# Format code with Ruff
ruff format .

# Check linting issues
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Run type checking with MyPy
mypy green_gov_rag tests

# Run all checks (if Make is installed)
make lint
make mypy
make format
```

## IDE Setup

### VS Code Setup

**Recommended Extensions:**
1. Python (Microsoft)
2. Pylance (Microsoft)
3. Ruff (Astral Software)
4. Docker (Microsoft)
5. GitLens (GitKraken)
6. YAML (Red Hat)
7. Markdown All in One (Yu Zhang)

**Install extensions:**
```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
code --install-extension ms-azuretools.vscode-docker
code --install-extension eamodio.gitlens
code --install-extension redhat.vscode-yaml
code --install-extension yzhang.markdown-all-in-one
```

**Configure VS Code settings** (`.vscode/settings.json`):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ],
  "python.linting.enabled": false,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.lint.args": [
    "--config=${workspaceFolder}/backend/pyproject.toml"
  ],
  "ruff.format.args": [
    "--config=${workspaceFolder}/backend/pyproject.toml"
  ],
  "mypy.configFile": "${workspaceFolder}/backend/pyproject.toml",
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/.ruff_cache": true
  },
  "editor.rulers": [100],
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true
}
```

**Create launch configuration** (`.vscode/launch.json`):
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "green_gov_rag.api.main:app",
        "--reload",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
      ],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    },
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    },
    {
      "name": "Python: Pytest",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v"
      ],
      "cwd": "${workspaceFolder}/backend",
      "envFile": "${workspaceFolder}/backend/.env"
    }
  ]
}
```

### PyCharm Setup

**Configure Python Interpreter:**
1. Open Settings (Ctrl+Alt+S / Cmd+,)
2. Navigate to Project > Python Interpreter
3. Click gear icon > Add
4. Select "Existing environment"
5. Browse to `backend/.venv/bin/python`
6. Click OK

**Configure Ruff:**
1. Install Ruff plugin from Marketplace
2. Go to Settings > Tools > Ruff
3. Enable Ruff
4. Set configuration file to `backend/pyproject.toml`

**Configure Testing:**
1. Go to Settings > Tools > Python Integrated Tools
2. Set "Default test runner" to pytest
3. Set "Test configuration" to use `backend/pyproject.toml`

**Configure Run Configuration:**
1. Edit Configurations > Add New > Python
2. Script path: Select `uvicorn` module
3. Parameters: `green_gov_rag.api.main:app --reload`
4. Working directory: `backend/`
5. Environment variables: Load from `.env`

## Pre-commit Hooks

Pre-commit hooks run checks before every commit to ensure code quality.

### Installing Pre-commit

```bash
# Install pre-commit package
pip install pre-commit

# Or if already in dev dependencies
pip install -e .[dev]
```

### Setting Up Hooks

```bash
cd /home/sundeep/github/green-gov-rag

# Install pre-commit hooks
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

### Create Pre-commit Configuration

Create `.pre-commit-config.yaml` in the repository root:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: check-toml
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.15
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML, types-requests]
        args: [--config-file=backend/pyproject.toml]
```

### Using Pre-commit Hooks

```bash
# Hooks run automatically on git commit
git commit -m "feat: Add new feature"

# Skip hooks if needed (not recommended)
git commit -m "feat: Add new feature" --no-verify

# Run specific hook manually
pre-commit run ruff --all-files

# Bypass hook for specific file
git commit -m "docs: Update README" README.md --no-verify
```

## Verification

### Verify Installation

```bash
# Check Python package installation
cd backend
python -c "import green_gov_rag; print(green_gov_rag.__version__)"

# Check CLI is available
greengovrag-cli --help

# Verify dependencies
pip list | grep -E "fastapi|langchain|sqlmodel"
```

### Verify Services

```bash
# Check backend API
curl http://localhost:8000/api/health
# Expected output: {"status": "healthy", ...}

# Check API documentation
# Open browser to http://localhost:8000/docs

# Check database connection
cd backend
python -c "from green_gov_rag.models.database import engine; engine.connect()"

# Check vector store
python -c "from green_gov_rag.rag.vector_store import VectorStoreFactory; VectorStoreFactory.create()"
```

### Verify Development Tools

```bash
# Check Ruff
ruff --version

# Check MyPy
mypy --version

# Check Pytest
pytest --version

# Check Alembic
alembic --version

# Check pre-commit
pre-commit --version
```

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError: No module named 'green_gov_rag'`**

Solution:
```bash
# Ensure you installed in editable mode
cd backend
pip install -e .[dev]

# Verify installation
pip list | grep green-gov-rag
```

**Issue: PostgreSQL connection refused**

Solution:
```bash
# Check PostgreSQL is running
# Ubuntu/Debian
sudo systemctl status postgresql

# macOS
brew services list

# Docker
docker-compose ps postgres

# Check connection parameters in .env
# Ensure DATABASE_URL matches your PostgreSQL setup
```

**Issue: `pgvector extension not found`**

Solution:
```bash
# Install pgvector extension
# Docker (restart with volume recreation)
cd deploy/docker
docker-compose down -v
docker-compose up -d

# Local PostgreSQL
sudo -u postgres psql -d greengovrag
CREATE EXTENSION vector;
\q
```

**Issue: Alembic migration errors**

Solution:
```bash
# Check current migration state
alembic current

# Downgrade and reapply
alembic downgrade -1
alembic upgrade head

# If stuck, reset migrations (CAUTION: destroys data)
alembic downgrade base
alembic upgrade head
```

**Issue: Tests fail with import errors**

Solution:
```bash
# Ensure test environment is properly set up
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or reinstall in editable mode
pip install -e .[dev]
```

**Issue: Embedding model download fails**

Solution:
```bash
# Pre-download embedding model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Or use different model in .env
EMBEDDING_MODEL=sentence-transformers/paraphrase-MiniLM-L6-v2
```

**Issue: Docker build fails**

Solution:
```bash
# Clean Docker cache
docker system prune -a

# Rebuild without cache
cd deploy/docker
docker-compose build --no-cache

# Check Docker resources (increase if needed)
# Docker Desktop > Settings > Resources
```

**Issue: Port already in use**

Solution:
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or change port in uvicorn command
uvicorn green_gov_rag.api.main:app --reload --port 8001
```

**Issue: Ruff/MyPy not found**

Solution:
```bash
# Ensure dev dependencies are installed
cd backend
pip install -e .[dev]

# Or install individually
pip install ruff mypy
```

### Getting Help

If you encounter issues not listed here:

1. Check the [Troubleshooting Guide](../user-guide/troubleshooting.md)
2. Search [existing issues](https://github.com/sdp5/green-gov-rag/issues)
3. Ask in GitHub Discussions
4. Create a new issue with:
   - Error message and stack trace
   - Environment details (OS, Python version, etc.)
   - Steps to reproduce
   - What you've already tried

## Next Steps

Now that your development environment is set up:

1. **Learn the code style**: Review the [Code Style Guide](code-style.md)
2. **Understand testing**: Read the [Testing Guide](testing.md)
3. **Make your first contribution**: Check the [Pull Request Guide](pull-requests.md)
4. **Explore the codebase**: Review the [Architecture Documentation](../developer-guide/)
5. **Find an issue**: Look for [good first issues](https://github.com/sdp5/green-gov-rag/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)

## Quick Reference

### Essential Commands

```bash
# Start development server
uvicorn green_gov_rag.api.main:app --reload

# Run tests
pytest

# Format code
ruff format .

# Check linting
ruff check .

# Type check
mypy green_gov_rag tests

# Run migrations
alembic upgrade head

# Start Docker services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Directory Structure

```
green-gov-rag/
├── backend/              # Python backend
│   ├── green_gov_rag/   # Main package
│   ├── tests/           # Test suite
│   ├── .env             # Environment variables (create from .env.example)
│   └── pyproject.toml   # Dependencies and tool configuration
├── deploy/docker/       # Docker Compose setup
├── docs/                # Documentation
└── .venv/              # Virtual environment (created locally)
```

---

**Ready to contribute?** Head to the [Code Style Guide](code-style.md) to learn about our coding standards!

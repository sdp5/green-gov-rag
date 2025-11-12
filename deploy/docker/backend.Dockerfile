FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/pyproject.toml backend/ruff.toml ./
COPY backend/green_gov_rag ./green_gov_rag
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./

# Copy data and configs
COPY data ./data
COPY backend/configs ./configs

# Copy startup script
COPY deploy/docker/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose FastAPI port
EXPOSE 8000

# Run startup script (handles health checks, migrations, then uvicorn)
CMD ["/app/start.sh"]

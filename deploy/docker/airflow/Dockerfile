# Stage 1: Builder - Install dependencies
# Use Airflow 2.10.4 which has better SQLAlchemy 2.0 support
FROM apache/airflow:2.10.4-python3.12 AS builder

USER root

# Install system deps
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY pyproject.toml README.md /app/
COPY green_gov_rag /app/green_gov_rag/
COPY alembic /app/alembic/
COPY alembic.ini /app/
COPY configs /app/configs/

RUN chown -R airflow:root /app
USER airflow

# Ensure setuptools_scm works even without .git folder
# Normalized project name (replace '-' with '_') → green_gov_rag
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GREEN_GOV_RAG=0.1.0

# Install your local package with constraints
RUN pip install --no-cache-dir -e .

# Stage 2: Runtime
FROM apache/airflow:2.10.4-python3.12

USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy code and installed packages from builder
COPY --from=builder /app /app
COPY --from=builder /home/airflow/.local /home/airflow/.local

# Create Airflow data directories
RUN mkdir -p /app/data/raw /app/data/processed /app/data/chunks /app/data/vector_store && \
    chown -R airflow:root /app && chmod -R 775 /app

USER airflow
ENV PYTHONPATH=/app:$PYTHONPATH

WORKDIR /opt/airflow

FROM apache/airflow:2.8.1-python3.12

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

USER airflow

WORKDIR /opt/airflow

# Copy backend code
COPY --chown=airflow:root backend/pyproject.toml backend/ruff.toml ./
COPY --chown=airflow:root backend/green_gov_rag ./green_gov_rag

# Install Python package
RUN pip install --no-cache-dir -e .

# DAGs are mounted via volume in docker-compose

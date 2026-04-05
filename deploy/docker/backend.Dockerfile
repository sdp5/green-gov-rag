FROM python:3.12-slim

WORKDIR /app
ARG VERSION="0.1.0"
# Set to "true" to install AWS CLI + local embedding deps (sentence-transformers, torch, faiss)
ARG INSTALL_AWS_CLI="false"
ARG INSTALL_LOCAL_EMBEDDINGS="false"

# Install system dependencies
# - gcc, g++, cmake: C/C++ compilers for Python packages with native extensions
# - curl: Health checks and debugging
# - postgresql-client: Database operations
# - libgl1, libglib2.0-0, libsm6, libxext6, libxrender1: OpenCV headless support
# - libgomp1: OpenMP for parallel processing
# - libmagic1: File type detection (unstructured library)
# - poppler-utils: PDF utilities (pdftotext, pdfinfo for unstructured)
# - tesseract-ocr: OCR engine for text extraction from images/PDFs
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    cmake \
    curl \
    unzip \
    pkg-config \
    postgresql-client \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Optionally install AWS CLI v2 (only needed if ETL runs inside the container)
RUN if [ "$INSTALL_AWS_CLI" = "true" ]; then \
        ARCH=$(uname -m) \
        && if [ "$ARCH" = "aarch64" ]; then \
             curl --retry 3 --retry-delay 5 "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"; \
           else \
             curl --retry 3 --retry-delay 5 "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
           fi \
        && unzip -q awscliv2.zip \
        && ./aws/install \
        && rm -rf aws awscliv2.zip \
        && aws --version; \
    else echo "Skipping AWS CLI install (use --build-arg INSTALL_AWS_CLI=true to include)"; fi

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

# Set pretend version for setuptools-scm
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

# Upgrade pip to avoid dependency resolution issues with older resolver
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
# Default: production (Azure OpenAI embeddings + Qdrant, no torch/faiss ~1.5GB smaller)
# With --build-arg INSTALL_LOCAL_EMBEDDINGS=true: includes sentence-transformers, torch, faiss
RUN if [ "$INSTALL_LOCAL_EMBEDDINGS" = "true" ]; then \
        pip install --no-cache-dir -e ".[local]"; \
    else \
        pip install --no-cache-dir -e .; \
    fi

# Expose FastAPI port
EXPOSE 8000

# Run startup script (handles health checks, migrations, then uvicorn)
CMD ["/app/start.sh"]

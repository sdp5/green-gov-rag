FROM python:3.12-slim

WORKDIR /app
ARG VERSION="0.1.0"

# Install system dependencies for ETL pipeline
# - gcc, g++: C/C++ compilers for Python packages with native extensions
# - curl: Health checks and debugging
# - postgresql-client: Database operations
# - libgl1, libglib2.0-0, libsm6, libxext6, libxrender1: OpenCV headless support
# - libgomp1: OpenMP for parallel processing (PyTorch, NumPy)
# - libmagic1: File type detection (unstructured library)
# - poppler-utils: PDF utilities (pdftotext, pdfinfo for unstructured)
# - tesseract-ocr: OCR engine for text extraction from images/PDFs
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
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

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose FastAPI port
EXPOSE 8000

# Run startup script (handles health checks, migrations, then uvicorn)
CMD ["/app/start.sh"]

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code
COPY backend/pyproject.toml backend/ruff.toml ./
COPY backend/green_gov_rag ./green_gov_rag

# Copy data and configs
COPY data ./data
COPY configs ./configs

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose Streamlit port
EXPOSE 8501

# Configure Streamlit
RUN mkdir -p ~/.streamlit && \
    echo "\
[server]\n\
headless = true\n\
port = 8501\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
" > ~/.streamlit/config.toml

# Run Streamlit
CMD ["streamlit", "run", "green_gov_rag/app/ui.py"]

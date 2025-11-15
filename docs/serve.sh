#!/bin/bash
# Serve MkDocs documentation locally

# Change to docs directory
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

# Serve documentation
echo "Starting MkDocs server..."
echo "Documentation will be available at: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop"

mkdocs serve

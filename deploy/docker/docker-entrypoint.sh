#!/bin/sh
set -e

# Runtime environment variable injection for Vite/React apps
# This script replaces placeholder values in built JavaScript files with actual environment variables

echo "Injecting runtime environment variables..."

# Find all JavaScript files in the build output
find /usr/share/nginx/html -type f -name '*.js' -exec sed -i \
  -e "s|VITE_API_URL_PLACEHOLDER|${VITE_API_URL:-http://localhost:8000/api}|g" \
  -e "s|VITE_MAPBOX_TOKEN_PLACEHOLDER|${VITE_MAPBOX_TOKEN:-}|g" \
  {} \;

echo "Environment variables injected successfully"
echo "VITE_API_URL: ${VITE_API_URL:-http://localhost:8000/api}"
echo "VITE_MAPBOX_TOKEN: ${VITE_MAPBOX_TOKEN:+***configured***}"

# Execute the CMD
exec "$@"

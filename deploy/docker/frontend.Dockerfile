# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY frontend/ ./

# Build application (env vars will be injected at runtime)
RUN npm run build

# Production stage
FROM nginx:alpine

# Install envsubst (part of gettext package)
RUN apk add --no-cache gettext

# Copy build output
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config
COPY deploy/docker/nginx.conf /etc/nginx/conf.d/default.conf

# Create entrypoint script for runtime env injection
COPY deploy/docker/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Expose port
EXPOSE 80

# Use custom entrypoint to inject env vars at runtime
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]

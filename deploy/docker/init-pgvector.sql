-- Initialize pgvector extension for PostgreSQL
-- This script runs automatically when the postgres container first starts

-- Create pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

"""Centralized configuration management using pydantic-settings.

All environment variables are defined here and can be accessed via the settings object.
"""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # =========================================================================
    # Cloud Storage Settings
    # =========================================================================
    cloud_provider: Literal["local", "aws", "azure"] = Field(
        default="local",
        description="Cloud storage provider (local, aws, azure)",
    )
    cloud_region: str | None = Field(
        default=None,
        description="Cloud region for storage",
    )
    storage_container: str = Field(
        default="greengovrag-documents",
        description="Storage container/bucket name",
    )
    local_storage_path: str = Field(
        default="./data/storage",
        description="Local storage path when using local provider",
    )

    # AWS Settings
    aws_access_key_id: str | None = Field(
        default=None,
        description="AWS access key ID",
    )
    aws_secret_access_key: str | None = Field(
        default=None,
        description="AWS secret access key",
    )
    aws_region: str | None = Field(
        default=None,
        description="AWS region",
    )

    # Azure Settings
    azure_storage_connection_string: str | None = Field(
        default=None,
        description="Azure Storage connection string",
    )

    # =========================================================================
    # LLM & Embedding Settings
    # =========================================================================
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )
    llm_model: str = Field(
        default="openai/text-davinci-003",
        description="LLM model to use for generation",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for vector generation",
    )
    bedrock_model_id: str | None = Field(
        default=None,
        description="AWS Bedrock model ID",
    )

    # =========================================================================
    # Application Settings
    # =========================================================================
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment",
    )
    debug: bool = Field(
        default=False,
        description="Debug mode",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # =========================================================================
    # Database Settings
    # =========================================================================
    database_url: str | None = Field(
        default=None,
        description="Database connection URL",
    )

    # =========================================================================
    # Vector Store Settings
    # =========================================================================
    vector_store_type: Literal["faiss", "qdrant", "chromadb"] = Field(
        default="faiss",
        description="Vector store type",
    )
    vector_store_path: str = Field(
        default="./data/vector_store",
        description="Path to vector store files",
    )
    qdrant_url: str | None = Field(
        default=None,
        description="Qdrant server URL",
    )
    qdrant_api_key: str | None = Field(
        default=None,
        description="Qdrant API key",
    )

    # =========================================================================
    # RAG Settings
    # =========================================================================
    chunk_size: int = Field(
        default=1000,
        description="Text chunk size for splitting documents",
    )
    chunk_overlap: int = Field(
        default=100,
        description="Overlap between text chunks",
    )
    top_k_results: int = Field(
        default=4,
        description="Number of top results to retrieve from vector store",
    )

    # =========================================================================
    # API Settings
    # =========================================================================
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host",
    )
    api_port: int = Field(
        default=8000,
        description="API server port",
    )
    api_reload: bool = Field(
        default=False,
        description="Enable API auto-reload",
    )


# Global settings instance
settings = Settings()


# Convenience function for testing/overriding settings
def get_settings() -> Settings:
    """Get the global settings instance.

    This function is useful for dependency injection and testing.
    """
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables.

    Useful for testing or when environment variables change.
    """
    global settings
    settings = Settings()
    return settings

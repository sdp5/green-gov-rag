"""Centralized configuration management using pydantic-settings.

All environment variables are defined here and can be accessed via the settings object.
"""

from __future__ import annotations

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
    llm_provider: Literal["openai", "azure", "bedrock", "anthropic"] = Field(
        default="openai",
        description="LLM provider (openai, azure, bedrock, anthropic)",
    )

    # OpenAI Settings
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
    )

    # Azure OpenAI Settings
    azure_openai_api_key: str | None = Field(
        default=None,
        description="Azure OpenAI API key",
    )
    azure_openai_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL",
    )
    azure_openai_api_version: str = Field(
        default="2024-02-15-preview",
        description="Azure OpenAI API version",
    )
    azure_openai_deployment: str | None = Field(
        default=None,
        description="Azure OpenAI deployment name",
    )

    # AWS Bedrock Settings
    bedrock_model_id: str | None = Field(
        default=None,
        description="AWS Bedrock model ID",
    )

    # Anthropic Settings
    anthropic_api_key: str | None = Field(
        default=None,
        description="Anthropic API key",
    )

    # Model Settings
    llm_model: str = Field(
        default="gpt-4",
        description="LLM model to use for generation",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model for vector generation",
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
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="CORS allowed origins (comma-separated)",
    )

    def model_post_init(self, __context):
        """Validate settings after initialization."""
        self._validate_llm_credentials()

    def _validate_llm_credentials(self):
        """Validate that required API keys are present for the selected provider."""
        if self.llm_provider == "openai" and not self.openai_api_key:
            msg = "OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'"
            raise ValueError(msg)

        if self.llm_provider == "azure":
            if not self.azure_openai_api_key:
                msg = "AZURE_OPENAI_API_KEY is required when LLM_PROVIDER is 'azure'"
                raise ValueError(msg)
            if not self.azure_openai_endpoint:
                msg = "AZURE_OPENAI_ENDPOINT is required when LLM_PROVIDER is 'azure'"
                raise ValueError(msg)

        if self.llm_provider == "bedrock":
            if not self.aws_access_key_id or not self.aws_secret_access_key:
                msg = "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required when LLM_PROVIDER is 'bedrock'"
                raise ValueError(msg)

        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            msg = "ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'"
            raise ValueError(msg)


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

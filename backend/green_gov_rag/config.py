"""Centralized configuration management using pydantic-settings.

All environment variables are defined here and can be accessed via the settings object.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from green_gov_rag.types import CloudProvider, LLMProvider, VectorStoreType

# Determine the .env file path (look in backend/ directory)
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Validation control
    skip_validation: bool = Field(
        default=False,
        description="Skip credential validation (for testing)",
    )

    # =========================================================================
    # Cloud Storage Settings
    # =========================================================================
    cloud_provider: CloudProvider = Field(
        default=CloudProvider.LOCAL,
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
    raw_data_dir: str = Field(
        default="./data/raw",
        description="Directory for raw downloaded documents (local development only)",
    )
    processed_data_dir: str = Field(
        default="./data/processed",
        description="Directory for processed/parsed documents",
    )
    chunks_data_dir: str = Field(
        default="./data/chunks",
        description="Directory for chunked documents",
    )
    documents_config_path: str = Field(
        default="configs/documents_config.yml",
        description="Path to documents configuration file",
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
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
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
        default="2024-12-01-preview",
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
        default="gpt-5-mini",
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
    vector_store_type: VectorStoreType = Field(
        default=VectorStoreType.QDRANT,
        description="Vector store type (faiss for local dev, qdrant for production)",
    )
    vector_store_path: str = Field(
        default="./data/vector_store",
        description="Path to vector store files",
    )
    qdrant_url: str | None = Field(
        default="http://localhost:6333",
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
        default="https://greengovrag.sundeep.id.au,https://greengovrag.au",
        description="CORS allowed origins (comma-separated)",
    )
    api_access_key: str = Field(
        default="dev-insecure-key-change-in-prod",
        description="API access key required for all API endpoints (set via environment variable in production)",
    )
    admin_api_key: str | None = Field(
        default=None,
        description="Admin API access key for /api/admin/* endpoints (must be different from API_ACCESS_KEY)",
    )

    # =========================================================================
    # Cache Settings
    # =========================================================================
    enable_cache: bool = Field(
        default=True,
        description="Enable LLM response caching",
    )
    enable_redis_cache: bool = Field(
        default=False,
        description="Enable Redis for distributed caching (requires Redis server)",
    )
    redis_host: str = Field(
        default="localhost",
        description="Redis server host",
    )
    redis_port: int = Field(
        default=6379,
        description="Redis server port",
    )
    cache_ttl: int = Field(
        default=3600,
        description="Cache time-to-live in seconds (default: 1 hour)",
    )
    enable_semantic_cache: bool = Field(
        default=True,
        description="Enable semantic similarity caching for similar queries (production-ready, threshold: 0.95)",
    )

    # =========================================================================
    # Notification Settings
    # =========================================================================
    enable_notifications: bool = Field(
        default=False,
        description="Enable email notifications for monitoring alerts",
    )
    smtp_host: str = Field(
        default="localhost",
        description="SMTP server host",
    )
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
    )
    smtp_username: str | None = Field(
        default=None,
        description="SMTP username for authentication",
    )
    smtp_password: str | None = Field(
        default=None,
        description="SMTP password for authentication",
    )
    smtp_use_tls: bool = Field(
        default=True,
        description="Use TLS for SMTP connection",
    )
    notification_from_email: str = Field(
        default="noreply@green-gov-rag.local",
        description="From email address for notifications",
    )
    notification_from_name: str = Field(
        default="Green Gov RAG Monitoring",
        description="From name for notifications",
    )
    notification_recipients: list[str] = Field(
        default_factory=list,
        description="List of email addresses to receive notifications",
    )
    notify_on_update: bool = Field(
        default=True,
        description="Send notification when documents are updated",
    )
    notify_on_discovery: bool = Field(
        default=True,
        description="Send notification when new documents are discovered",
    )
    notify_on_failure: bool = Field(
        default=True,
        description="Send notification when monitoring fails",
    )
    notify_on_citation_warning: bool = Field(
        default=False,
        description="Send notification for citation verification warnings",
    )
    notification_throttle_seconds: int = Field(
        default=3600,
        description="Minimum seconds between notifications for same event (throttling)",
    )

    # =========================================================================
    # Citation Verification Settings
    # =========================================================================
    enable_citation_verification: bool = Field(
        default=True,
        description="Enable citation verification in query responses",
    )
    citation_staleness_threshold_days: int = Field(
        default=30,
        description="Days after which citations are considered potentially stale",
    )

    def model_post_init(self, __context):
        """Validate settings after initialization."""
        # Skip validation in development if skip_validation is true or DEBUG is true
        if not self.skip_validation and not self.debug:
            self._validate_llm_credentials()

    def _validate_llm_credentials(self):
        """Validate that required API keys are present for the selected provider."""
        if self.llm_provider == "openai":
            if not self.openai_api_key or self.openai_api_key == "sk-your-key-here":
                msg = (
                    "OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'. "
                    "Set DEBUG=true in .env to skip validation during development."
                )
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

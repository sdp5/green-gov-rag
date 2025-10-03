"""Cloud configuration management for GreenGovRAG.

Provides environment-driven configuration for cloud resources.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class CloudConfig:
    """Cloud provider configuration."""

    provider: str
    region: Optional[str] = None
    storage_container: Optional[str] = None
    storage_connection_string: Optional[str] = None

    @classmethod
    def from_env(cls) -> "CloudConfig":
        """Load cloud configuration from environment variables.

        Environment variables:
            CLOUD_PROVIDER: Cloud provider ('aws', 'azure', 'local')
            CLOUD_REGION: Cloud region/location
            STORAGE_CONTAINER: Default storage container/bucket name
            AZURE_STORAGE_CONNECTION_STRING: Azure storage connection string (Azure only)
            LOCAL_STORAGE_PATH: Local storage base path (local only)

        Returns:
            CloudConfig instance
        """
        provider = os.getenv("CLOUD_PROVIDER", "local")
        region = os.getenv("CLOUD_REGION")
        storage_container = os.getenv("STORAGE_CONTAINER", "greengovrag-documents")
        storage_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        return cls(
            provider=provider,
            region=region,
            storage_container=storage_container,
            storage_connection_string=storage_connection_string,
        )

    def validate(self) -> None:
        """Validate cloud configuration.

        Raises:
            ValueError: If required configuration is missing
        """
        if self.provider not in ("aws", "azure", "local"):
            msg = f"Invalid CLOUD_PROVIDER: {self.provider}. Must be 'aws', 'azure', or 'local'"
            raise ValueError(msg)

        if self.provider == "azure" and not self.storage_connection_string:
            msg = "AZURE_STORAGE_CONNECTION_STRING is required for Azure provider"
            raise ValueError(msg)


def get_storage_client():
    """Get a configured storage client based on environment.

    Returns:
        StorageClient instance configured for the current environment
    """
    from green_gov_rag.cloud.storage import StorageClient

    config = CloudConfig.from_env()
    config.validate()

    return StorageClient(provider=config.provider)

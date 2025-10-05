"""Cloud configuration management for GreenGovRAG.

Provides environment-driven configuration for cloud resources.
Now uses centralized settings from green_gov_rag.config
"""

from __future__ import annotations

from dataclasses import dataclass

from green_gov_rag.cloud.storage import StorageClient
from green_gov_rag.config import settings


@dataclass
class CloudConfig:
    """Cloud provider configuration."""

    provider: str
    region: str | None = None
    storage_container: str | None = None
    storage_connection_string: str | None = None

    @classmethod
    def from_env(cls) -> "CloudConfig":
        """Load cloud configuration from centralized settings.

        Returns
        -------
            CloudConfig instance

        """
        return cls(
            provider=settings.cloud_provider,
            region=settings.cloud_region or settings.aws_region,
            storage_container=settings.storage_container,
            storage_connection_string=settings.azure_storage_connection_string,
        )

    def validate(self) -> None:
        """Validate cloud configuration.

        Raises
        ------
            ValueError: If required configuration is missing

        """
        if self.provider not in {"aws", "azure", "local"}:
            msg = f"Invalid CLOUD_PROVIDER: {self.provider}. Must be 'aws', 'azure', or 'local'"
            raise ValueError(msg)

        if self.provider == "azure" and not self.storage_connection_string:
            msg = "AZURE_STORAGE_CONNECTION_STRING is required for Azure provider"
            raise ValueError(msg)


def get_storage_client() -> StorageClient:
    """Get a configured storage client based on environment.

    Returns
    -------
        StorageClient instance configured for the current environment.

    """
    config = CloudConfig.from_env()
    config.validate()

    return StorageClient(provider=config.provider)

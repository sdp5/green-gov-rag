"""Cloud abstraction layer for GreenGovRAG.

Provides cloud-agnostic interfaces for storage, secrets, and other cloud services.
"""

from green_gov_rag.cloud.storage import StorageClient

__all__ = ["StorageClient"]

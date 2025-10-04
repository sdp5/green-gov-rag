"""Document source plugins for ETL pipeline.

This module provides a plugin architecture for document sources,
making it easy to add new document types as contributions.
"""

from green_gov_rag.etl.sources.base import DocumentSource, ValidationResult
from green_gov_rag.etl.sources.emissions import EmissionsReportingSource
from green_gov_rag.etl.sources.factory import (
    DocumentSourceFactory,
    GenericDocumentSource,
)
from green_gov_rag.etl.sources.federal import FederalLegislationSource
from green_gov_rag.etl.sources.local_government import LocalGovernmentSource
from green_gov_rag.etl.sources.registry import DocumentSourceRegistry
from green_gov_rag.etl.sources.state import StateLegislationSource

__all__ = [
    "DocumentSource",
    "ValidationResult",
    "DocumentSourceRegistry",
    "DocumentSourceFactory",
    "GenericDocumentSource",
    "FederalLegislationSource",
    "EmissionsReportingSource",
    "StateLegislationSource",
    "LocalGovernmentSource",
]

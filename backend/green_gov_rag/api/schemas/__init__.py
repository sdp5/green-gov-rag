"""API request/response schemas."""

from green_gov_rag.api.schemas.admin import (
    AdminActionResponse,
    AdminDocumentDetailResponse,
    AdminDocumentItem,
    AdminDocumentListResponse,
    DashboardStats,
    QueryAnalyticsResponse,
    SystemHealthResponse,
)
from green_gov_rag.api.schemas.analytics import (
    AnalyticsStats,
    DistributionData,
    TopicDistribution,
)
from green_gov_rag.api.schemas.common import (
    GeoJSONFeature,
    GeoJSONGeometry,
    GeoJSONResponse,
    HealthResponse,
    RootResponse,
)
from green_gov_rag.api.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentsFilter,
)
from green_gov_rag.api.schemas.query import (
    FeedbackRequest,
    FeedbackResponse,
    QueryRequest,
    QueryResponse,
    SourceDocument,
)

__all__ = [
    "DocumentListResponse",
    "DocumentResponse",
    "DocumentsFilter",
    "QueryRequest",
    "QueryResponse",
    "SourceDocument",
    "FeedbackRequest",
    "FeedbackResponse",
    "AnalyticsStats",
    "DistributionData",
    "TopicDistribution",
    "HealthResponse",
    "RootResponse",
    "GeoJSONFeature",
    "GeoJSONGeometry",
    "GeoJSONResponse",
    "DashboardStats",
    "AdminDocumentListResponse",
    "AdminDocumentDetailResponse",
    "AdminDocumentItem",
    "AdminActionResponse",
    "QueryAnalyticsResponse",
    "SystemHealthResponse",
]

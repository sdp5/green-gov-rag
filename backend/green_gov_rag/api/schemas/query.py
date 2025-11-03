"""Query request/response schemas."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    """Source document reference with legal-grade citation metadata.

    Enhanced schema following legal RAG best practices (2025) for
    hierarchical document structure and deep linking.
    """

    # Core document identification
    title: str = Field(..., description="Document title")
    source_url: str = Field(..., description="Document source URL")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from document")
    relevance_score: Optional[float] = Field(None, description="Similarity score (0-1)")

    # Citation metadata (from hierarchical PDF parsing)
    page_number: Optional[int] = Field(
        None,
        description="Page number where this excerpt appears",
    )
    page_range: Optional[list[int]] = Field(
        None,
        description="Page range if excerpt spans multiple pages [start, end]",
    )
    section_title: Optional[str] = Field(
        None,
        description="Current section title (e.g., 'Market-Based Accounting Methods')",
    )
    section_hierarchy: Optional[list[str]] = Field(
        None,
        description="Full section hierarchy from top-level to current section",
        examples=[
            [
                "Part 3: Scope 2 Emissions",
                "Section 3.2: Calculation Methods",
                "3.2.1 Market-Based Accounting",
            ]
        ],
    )
    clause_reference: Optional[str] = Field(
        None,
        description="Clause or section reference (e.g., 's.3.2.1', 'cl.42')",
    )

    # Deep linking
    deep_link: Optional[str] = Field(
        None,
        description="Deep link to specific section/page in PDF",
        examples=["https://cer.gov.au/document/guideline.pdf#page=42"],
    )

    # Formatted citation
    citation: Optional[str] = Field(
        None,
        description="Formatted citation string for display",
        examples=[
            "Clean Energy Regulator (2024), Scope 2 Guideline, Page 42, Section 3.2.1"
        ],
    )

    # Document metadata for context
    jurisdiction: Optional[str] = Field(
        None,
        description="Jurisdiction level: federal, state, or local",
    )
    category: Optional[str] = Field(
        None,
        description="Document category: environment, planning, legislation, etc.",
    )
    topic: Optional[str] = Field(
        None,
        description="Specific topic: emissions_reporting, biodiversity, etc.",
    )
    region: Optional[str] = Field(
        None,
        description="Geographic region: Australia, New South Wales, City of Adelaide, etc.",
    )

    # ESG metadata (for ESG-specific queries)
    esg_metadata: Optional[dict[str, Any]] = Field(
        None,
        description="ESG-specific metadata (frameworks, scopes, gases, etc.)",
        examples=[
            {
                "frameworks": ["NGER", "ISSB"],
                "emission_scopes": ["scope_2"],
                "greenhouse_gases": ["CO2", "CH4", "N2O"],
                "consolidation_method": "operational_control",
                "regulator": "Clean Energy Regulator",
            }
        ],
    )

    # Spatial metadata (for location-based queries)
    spatial_metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Spatial metadata (LGA codes, state, spatial scope)",
        examples=[
            {
                "spatial_scope": "local",
                "state": "SA",
                "lga_codes": ["40070"],
                "lga_names": ["City of Adelaide"],
            }
        ],
    )


class QueryRequest(BaseModel):
    """Query request schema."""

    query: str = Field(..., min_length=1, description="User query")
    region: Optional[str] = Field(None, description="Region filter")
    jurisdiction: Optional[str] = Field(None, description="Jurisdiction filter")
    topics: Optional[list[str]] = Field(None, description="Topic filters")
    max_sources: int = Field(5, ge=1, le=20, description="Max source documents")
    session_id: Optional[str] = Field(
        None, description="Browser session ID for user-specific query history"
    )

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "query": "What are the emissions targets for NSW?",
                "region": "NSW",
                "jurisdiction": "State",
                "topics": ["Climate", "Emissions"],
                "max_sources": 5,
            }
        }


class FeedbackRequest(BaseModel):
    """Feedback submission for a query."""

    rating: int = Field(
        ..., ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)"
    )
    feedback_text: Optional[str] = Field(
        None, max_length=1000, description="Optional text feedback"
    )

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "rating": 5,
                "feedback_text": "Very helpful answer with accurate citations!",
            }
        }


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    success: bool
    message: str
    query_id: int

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Feedback submitted successfully",
                "query_id": 42,
            }
        }


class CoverageInfo(BaseModel):
    """LGA document coverage information."""

    selected_lga: Optional[str] = Field(
        None,
        description="Selected LGA name (e.g., 'City of Adelaide')",
    )
    lga_code: Optional[str] = Field(
        None,
        description="LGA code (e.g., '40070')",
    )
    has_local_coverage: bool = Field(
        ...,
        description="Whether local documents exist for this LGA",
    )
    local_doc_count: int = Field(
        0,
        description="Number of local documents available for this LGA",
    )
    coverage_level: str = Field(
        ...,
        description="Coverage level: 'high', 'medium', 'low', or 'none'",
    )
    contribution_url: str = Field(
        ...,
        description="GitHub URL to contribute new document sources",
    )

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "selected_lga": "City of Adelaide",
                "lga_code": "40070",
                "has_local_coverage": True,
                "local_doc_count": 15,
                "coverage_level": "high",
                "contribution_url": "https://github.com/sdp5/green-gov-rag/issues/new?template=add-document-source.md",
            }
        }


class QueryResponse(BaseModel):
    """Query response schema."""

    query: str
    answer: str
    sources: list[SourceDocument]
    filters_applied: dict
    response_time_ms: Optional[float] = None
    query_id: Optional[int] = Field(
        None, description="Query history ID for feedback submission"
    )

    # Document coverage information
    coverage_info: Optional[CoverageInfo] = Field(
        None,
        description="LGA document coverage information and contribution link",
    )

    # Phase 3: Trust & Compliance Features
    trust_score: Optional[float] = Field(
        None,
        description="Overall trust score (0-1) for this response",
        ge=0.0,
        le=1.0,
    )
    trust_confidence: Optional[str] = Field(
        None,
        description="Trust confidence level: high, medium, or low",
    )
    trust_breakdown: Optional[dict[str, Any]] = Field(
        None,
        description="Detailed trust score breakdown (citation, authority, conflict, accuracy)",
    )
    conflicts_detected: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Regulatory conflicts detected between sources",
    )
    hierarchy_explanation: Optional[str] = Field(
        None,
        description="Explanation of regulatory hierarchy (Federal > State > Local)",
    )
    citation_warnings: Optional[list[str]] = Field(
        None,
        description="Warnings about citation quality or currency",
    )

    class Config:
        """Schema config."""

        json_schema_extra = {
            "example": {
                "query": "What are the Scope 2 market-based accounting methods under NGER?",
                "answer": "Under NGER, Scope 2 emissions can be calculated using market-based accounting methods...",
                "sources": [
                    {
                        "title": "Clean Energy Regulator - Scope 2 Emissions Guideline",
                        "source_url": "https://cer.gov.au/document/voluntary-market-based-scope-2-emissions-guideline",
                        "excerpt": "Market-based accounting requires documentation of contractual instruments...",
                        "relevance_score": 0.92,
                        "page_number": 42,
                        "page_range": [42, 43],
                        "section_title": "Market-Based Accounting Methods",
                        "section_hierarchy": [
                            "Part 3: Scope 2 Emissions Accounting",
                            "Section 3.2: Calculation Methods",
                            "3.2.1 Market-Based Accounting",
                        ],
                        "clause_reference": "s.3.2.1",
                        "deep_link": "https://cer.gov.au/document/voluntary-market-based-scope-2-emissions-guideline#page=42",
                        "citation": "Clean Energy Regulator (2024), Scope 2 Emissions Guideline, Page 42, Section 3.2.1",
                        "jurisdiction": "federal",
                        "category": "environment",
                        "topic": "emissions_reporting",
                        "region": "Australia",
                        "esg_metadata": {
                            "frameworks": ["NGER", "ISSB", "GHG_Protocol"],
                            "emission_scopes": ["scope_2"],
                            "greenhouse_gases": [
                                "CO2",
                                "CH4",
                                "N2O",
                                "SF6",
                                "HFCs",
                                "PFCs",
                                "NF3",
                            ],
                            "consolidation_method": "operational_control",
                            "methodology_type": "calculation",
                            "regulator": "Clean Energy Regulator",
                            "reportable_under_nger": True,
                            "accounting_methods": ["location_based", "market_based"],
                        },
                        "spatial_metadata": {
                            "spatial_scope": "federal",
                            "state": None,
                            "lga_codes": [],
                            "applies_to_all_lgas": True,
                        },
                    }
                ],
                "filters_applied": {
                    "frameworks": ["NGER"],
                    "emission_scopes": ["scope_2"],
                },
                "response_time_ms": 1234.56,
            }
        }

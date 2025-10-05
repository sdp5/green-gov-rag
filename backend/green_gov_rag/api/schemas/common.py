"""Common response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., json_schema_extra={"examples": ["ok"]})
    service: str = Field(..., json_schema_extra={"examples": ["GreenGovRAG API"]})
    version: str = Field(..., json_schema_extra={"examples": ["0.1.0"]})


class RootResponse(BaseModel):
    """Root endpoint response."""

    service: str = Field(..., json_schema_extra={"examples": ["GreenGovRAG API"]})
    version: str = Field(..., json_schema_extra={"examples": ["0.1.0"]})
    docs: str = Field(..., json_schema_extra={"examples": ["/docs"]})
    admin: str = Field(..., json_schema_extra={"examples": ["/api/admin/dashboard"]})
    health: str = Field(..., json_schema_extra={"examples": ["/api/health"]})


class GeoJSONGeometry(BaseModel):
    """GeoJSON geometry."""

    type: str = Field(..., json_schema_extra={"examples": ["Polygon"]})
    coordinates: list[Any] = Field(
        ...,
        json_schema_extra={
            "examples": [
                [
                    [
                        [151.1, -33.8],
                        [151.3, -33.8],
                        [151.3, -34.0],
                        [151.1, -34.0],
                        [151.1, -33.8],
                    ]
                ]
            ]
        },
    )


class GeoJSONFeature(BaseModel):
    """GeoJSON feature."""

    type: str = Field(default="Feature", json_schema_extra={"examples": ["Feature"]})
    properties: dict[str, Any] = Field(
        ...,
        json_schema_extra={
            "examples": [{"name": "Sydney", "LGA_NAME": "Sydney", "state": "NSW"}]
        },
    )
    geometry: GeoJSONGeometry


class GeoJSONResponse(BaseModel):
    """GeoJSON FeatureCollection response."""

    type: str = Field(
        default="FeatureCollection",
        json_schema_extra={"examples": ["FeatureCollection"]},
    )
    features: list[GeoJSONFeature]

    model_config = {
        "json_schema_extra": {
            "examples": [{"type": "FeatureCollection", "features": []}]
        }
    }

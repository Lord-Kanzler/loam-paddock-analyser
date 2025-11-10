"""
Pydantic models for API responses.

These models provide:
- Type safety and validation
- Automatic JSON serialization
- Self-documenting API (shows up in /docs)
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PaddockDetail(BaseModel):
    """Individual paddock information."""

    name: str = Field(..., description="Paddock name")
    area_ha: Optional[float] = Field(None, description="Area in hectares")
    area_ac: Optional[float] = Field(None, description="Area in acres")
    note: Optional[str] = Field(None, description="Error message if invalid")


class ProjectSummary(BaseModel):
    """Summary statistics for a single project."""

    project_name: str = Field(..., description="Project name")
    paddock_count: int = Field(..., description="Total number of paddocks")
    valid_paddocks: int = Field(..., description="Number of valid paddocks")
    invalid_paddocks: int = Field(..., description="Number of invalid paddocks")
    area_m2: float = Field(..., description="Total area in square meters")
    area_ha: float = Field(..., description="Total area in hectares")
    area_ac: float = Field(..., description="Total area in acres")
    paddocks: List[PaddockDetail] = Field(..., description="Individual paddock details")


class UploadSummary(BaseModel):
    """Overall summary statistics."""

    total_projects: int = Field(..., description="Number of unique projects")
    total_paddocks: int = Field(..., description="Total number of paddocks")
    invalid_paddocks: int = Field(..., description="Number of invalid paddocks")


class UploadResponse(BaseModel):
    """Complete response from file upload."""

    summary: UploadSummary = Field(..., description="Overall statistics")
    projects: List[ProjectSummary] = Field(..., description="Per-project breakdown")
    normalized_geojson: Dict[str, Any] = Field(
        ..., 
        description="Normalized GeoJSON FeatureCollection with computed areas"
    )

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
    area_ha: Optional[float] = Field(None, description="Area in hectares (geodesic)")
    area_ac: Optional[float] = Field(None, description="Area in acres (geodesic)")
    area_planar_m2: Optional[float] = Field(None, description="Planar area in m²")
    area_geodesic_m2: Optional[float] = Field(None, description="Geodesic area in m²")
    difference_percent: Optional[float] = Field(None, description="Difference between planar and geodesic (%)")
    note: Optional[str] = Field(None, description="Error message if invalid")


class ProjectSummary(BaseModel):
    """Summary statistics for a single project."""

    project_name: str = Field(..., description="Project name")
    paddock_count: int = Field(..., description="Total number of paddocks")
    valid_paddocks: int = Field(..., description="Number of valid paddocks")
    invalid_paddocks: int = Field(..., description="Number of invalid paddocks")
    area_planar_m2: float = Field(..., description="Total planar area in square meters")
    area_geodesic_m2: float = Field(..., description="Total geodesic area in square meters")
    area_m2: float = Field(..., description="Total area in square meters (geodesic)")
    area_ha: float = Field(..., description="Total area in hectares (geodesic)")
    area_ac: float = Field(..., description="Total area in acres (geodesic)")
    difference_m2: float = Field(..., description="Difference between planar and geodesic (m²)")
    difference_percent: float = Field(..., description="Difference between planar and geodesic (%)")
    paddocks: List[PaddockDetail] = Field(..., description="Individual paddock details")


class UploadSummary(BaseModel):
    """Overall summary statistics."""

    total_projects: int = Field(..., description="Number of unique projects")
    total_paddocks: int = Field(..., description="Total number of paddocks")
    invalid_paddocks: int = Field(..., description="Number of invalid paddocks")
    total_area_planar_m2: float = Field(..., description="Total planar area")
    total_area_geodesic_m2: float = Field(..., description="Total geodesic area")
    total_difference_m2: float = Field(..., description="Total difference")
    total_difference_percent: float = Field(..., description="Average difference (%)")


class UploadResponse(BaseModel):
    """Complete response from file upload."""

    summary: UploadSummary = Field(..., description="Overall statistics")
    projects: List[ProjectSummary] = Field(..., description="Per-project breakdown")
    normalized_geojson: Dict[str, Any] = Field(
        ..., 
        description="Normalized GeoJSON FeatureCollection with computed areas"
    )

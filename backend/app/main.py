"""
Loam Paddock Analyser API

A simple FastAPI application for processing GeoJSON paddock data.
"""

import json
from collections import defaultdict
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import orjson

from .geometry import get_feature_area, create_normalized_feature
from .models import UploadResponse, ProjectSummary, UploadSummary, PaddockDetail

# Create FastAPI application instance
app = FastAPI(
    title="Loam Paddock Analyser",
    description="Upload GeoJSON paddock files and get analysis with planar vs geodesic comparison",
    version="0.2.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Root endpoint - health check."""
    return {"message": "Loam Paddock Analyser API", "status": "running"}


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


def extract_project_name(feature: Dict[str, Any]) -> str:
    """
    Extract project name from a GeoJSON feature's properties.
    
    Looks for these fields in order:
    1. Project__Name (from sample data)
    2. project_name
    3. project
    
    Args:
        feature: GeoJSON Feature dict
        
    Returns:
        Project name, or "Unknown" if not found or null
    """
    props = feature.get("properties") or {}
    
    # Try different possible field names
    project = (
        props.get("Project__Name") or 
        props.get("project_name") or 
        props.get("project")
    )
    
    # Return "Unknown" if null or empty string
    if not project:
        return "Unknown"
    
    return str(project).strip()


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    """
    Upload a GeoJSON file for processing.

    Args:
        file: Uploaded GeoJSON file

    Returns:
        Grouped paddocks by project with planar vs geodesic area comparison
    """
    # Check file extension
    if not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .geojson or .json file",
        )

    # Read file content
    raw_bytes = await file.read()

    # Parse JSON
    try:
        data = orjson.loads(raw_bytes)
    except Exception:
        try:
            data = json.loads(raw_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON: {str(e)}",
            )

    # Validate it's a FeatureCollection
    if data.get("type") != "FeatureCollection":
        raise HTTPException(
            status_code=400,
            detail="Expected a GeoJSON FeatureCollection",
        )

    # Get features
    features = data.get("features", [])
    
    # Group by project with area calculations
    projects = defaultdict(lambda: {
        "paddock_count": 0,
        "valid_paddocks": 0,
        "invalid_paddocks": 0,
        "area_planar_m2": 0.0,
        "area_geodesic_m2": 0.0,
        "paddocks": []
    })
    
    total_invalid = 0
    total_planar = 0.0
    total_geodesic = 0.0
    normalized_features = []
    
    for feature in features:
        project_name = extract_project_name(feature)
        projects[project_name]["paddock_count"] += 1
        
        # Get paddock name
        props = feature.get("properties", {})
        paddock_name = props.get("name", "Unnamed")
        
        # Calculate area
        area_info = get_feature_area(feature)
        
        # Create normalized feature
        normalized_feature = create_normalized_feature(feature, area_info)
        normalized_features.append(normalized_feature)
        
        if area_info:
            # Valid geometry
            projects[project_name]["valid_paddocks"] += 1
            projects[project_name]["area_planar_m2"] += area_info["area_planar_m2"]
            projects[project_name]["area_geodesic_m2"] += area_info["area_geodesic_m2"]
            
            total_planar += area_info["area_planar_m2"]
            total_geodesic += area_info["area_geodesic_m2"]
            
            # Create PaddockDetail object
            paddock = PaddockDetail(
                name=paddock_name,
                area_ha=round(area_info["area_ha"], 2),
                area_ac=round(area_info["area_ac"], 2),
                area_planar_m2=round(area_info["area_planar_m2"], 2),
                area_geodesic_m2=round(area_info["area_geodesic_m2"], 2),
                difference_percent=round(area_info["difference_percent"], 2),
            )
            projects[project_name]["paddocks"].append(paddock)
        else:
            # Invalid geometry
            projects[project_name]["invalid_paddocks"] += 1
            
            error_msg = normalized_feature["properties"].get("error", "Invalid geometry")
            paddock = PaddockDetail(
                name=paddock_name,
                area_ha=None,
                area_ac=None,
                area_planar_m2=None,
                area_geodesic_m2=None,
                difference_percent=None,
                note=error_msg
            )
            projects[project_name]["paddocks"].append(paddock)
            total_invalid += 1
    
    # Convert to list of ProjectSummary objects
    project_list = []
    for name, data in projects.items():
        planar = data["area_planar_m2"]
        geodesic = data["area_geodesic_m2"]
        diff = geodesic - planar
        diff_pct = (diff / planar * 100) if planar > 0 else 0
        
        project_summary = ProjectSummary(
            project_name=name,
            paddock_count=data["paddock_count"],
            valid_paddocks=data["valid_paddocks"],
            invalid_paddocks=data["invalid_paddocks"],
            area_planar_m2=round(planar, 2),
            area_geodesic_m2=round(geodesic, 2),
            area_m2=round(geodesic, 2),
            area_ha=round(geodesic / 10_000, 2),
            area_ac=round(geodesic * 0.000247105, 2),
            difference_m2=round(diff, 2),
            difference_percent=round(diff_pct, 2),
            paddocks=data["paddocks"]
        )
        project_list.append(project_summary)
    
    # Sort by project name
    project_list.sort(key=lambda p: p.project_name)

    # Create normalized GeoJSON FeatureCollection
    normalized_geojson = {
        "type": "FeatureCollection",
        "features": normalized_features
    }
    
    # Calculate total difference
    total_diff = total_geodesic - total_planar
    total_diff_pct = (total_diff / total_planar * 100) if total_planar > 0 else 0

    # Create response
    return UploadResponse(
        summary=UploadSummary(
            total_projects=len(project_list),
            total_paddocks=len(features),
            invalid_paddocks=total_invalid,
            total_area_planar_m2=round(total_planar, 2),
            total_area_geodesic_m2=round(total_geodesic, 2),
            total_difference_m2=round(total_diff, 2),
            total_difference_percent=round(total_diff_pct, 2),
        ),
        projects=project_list,
        normalized_geojson=normalized_geojson,
    )

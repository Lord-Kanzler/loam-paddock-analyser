"""
Loam Paddock Analyser API

A simple FastAPI application for processing GeoJSON paddock data.
"""

import json
from collections import defaultdict
from typing import Dict, List, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
import orjson  # Faster than built-in json

from .geometry import get_feature_area  # Import our geometry module

# Create FastAPI application instance
app = FastAPI(
    title="Loam Paddock Analyser",
    description="Upload GeoJSON paddock files and get analysis",
    version="0.1.0",
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


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """
    Upload a GeoJSON file for processing.

    Args:
        file: Uploaded GeoJSON file

    Returns:
        Grouped paddocks by project with area calculations
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
        # Try fast orjson first
        data = orjson.loads(raw_bytes)
    except Exception:
        # Fall back to standard json library
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
        "area_m2": 0.0,
        "paddock_names": []
    })
    
    total_invalid = 0
    
    for feature in features:
        project_name = extract_project_name(feature)
        projects[project_name]["paddock_count"] += 1
        
        # Get paddock name for debugging
        props = feature.get("properties", {})
        paddock_name = props.get("name", "Unnamed")
        
        # Calculate area
        area_info = get_feature_area(feature)
        
        if area_info:
            # Valid geometry
            projects[project_name]["valid_paddocks"] += 1
            projects[project_name]["area_m2"] += area_info["area_m2"]
            projects[project_name]["paddock_names"].append({
                "name": paddock_name,
                "area_ha": round(area_info["area_ha"], 2),
                "area_ac": round(area_info["area_ac"], 2),
            })
        else:
            # Invalid geometry
            projects[project_name]["invalid_paddocks"] += 1
            projects[project_name]["paddock_names"].append({
                "name": paddock_name,
                "area_ha": None,
                "area_ac": None,
                "note": "Invalid geometry"
            })
            total_invalid += 1
    
    # Convert to list of project summaries
    project_list = []
    for name, data in projects.items():
        project_list.append({
            "project_name": name,
            "paddock_count": data["paddock_count"],
            "valid_paddocks": data["valid_paddocks"],
            "invalid_paddocks": data["invalid_paddocks"],
            "area_m2": round(data["area_m2"], 2),
            "area_ha": round(data["area_m2"] / 10_000, 2),
            "area_ac": round(data["area_m2"] * 0.000247105, 2),
            "paddocks": data["paddock_names"]
        })
    
    # Sort by project name
    project_list.sort(key=lambda p: p["project_name"])

    return {
        "summary": {
            "total_projects": len(project_list),
            "total_paddocks": len(features),
            "invalid_paddocks": total_invalid,
        },
        "projects": project_list,
    }

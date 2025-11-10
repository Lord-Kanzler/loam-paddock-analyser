"""
Loam Paddock Analyser API

A simple FastAPI application for processing GeoJSON paddock data.
"""

import json
from fastapi import FastAPI, UploadFile, File, HTTPException
import orjson  # Faster than built-in json

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


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """
    Upload a GeoJSON file for processing.

    Args:
        file: Uploaded GeoJSON file

    Returns:
        Basic analysis of the GeoJSON structure
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

    # Get basic info
    features = data.get("features", [])

    return {
        "filename": file.filename,
        "type": data.get("type"),
        "feature_count": len(features),
        "crs": data.get("crs", "Not specified"),
        "message": "GeoJSON parsed successfully (detailed processing not yet implemented)",
    }

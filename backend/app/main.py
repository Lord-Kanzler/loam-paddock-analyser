"""
Loam Paddock Analyser API

A simple FastAPI application for processing GeoJSON paddock data.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException

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
        Basic file information (for now)
    """
    # Check file extension
    if not file.filename.lower().endswith((".geojson", ".json")):
        raise HTTPException(
            status_code=400,
            detail="Please upload a .geojson or .json file",
        )

    # Read file content
    content = await file.read()

    # Return basic info
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "message": "File received successfully (processing not yet implemented)",
    }

"""
Loam Paddock Analyser API

A simple FastAPI application for processing GeoJSON paddock data.
"""

from fastapi import FastAPI

# Create a FastAPI application instance
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

"""
Basic API tests for the Loam Paddock Analyser.

Tests:
- Health check endpoint
- File upload with valid GeoJSON
- Error handling for invalid files
"""

import io
import json
from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"


def test_upload_empty_feature_collection():
    """Test uploading an empty but valid FeatureCollection."""
    # Create minimal valid GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    
    # Convert to bytes
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    # Upload
    response = client.post(
        "/api/upload",
        files={"file": ("empty.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "summary" in data
    assert "projects" in data
    assert "normalized_geojson" in data
    
    # Check summary
    assert data["summary"]["total_projects"] == 0
    assert data["summary"]["total_paddocks"] == 0
    assert data["summary"]["invalid_paddocks"] == 0


def test_upload_single_paddock():
    """Test uploading a FeatureCollection with one valid paddock."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Test Paddock",
                    "Project__Name": "Test Project"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.5, 47.0],
                        [-109.4, 47.0],
                        [-109.4, 47.1],
                        [-109.5, 47.1],
                        [-109.5, 47.0]
                    ]]
                }
            }
        ]
    }
    
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("test.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check counts
    assert data["summary"]["total_projects"] == 1
    assert data["summary"]["total_paddocks"] == 1
    assert data["summary"]["invalid_paddocks"] == 0
    
    # Check project data
    assert len(data["projects"]) == 1
    project = data["projects"][0]
    assert project["project_name"] == "Test Project"
    assert project["paddock_count"] == 1
    assert project["valid_paddocks"] == 1
    assert project["area_m2"] > 0  # Should have calculated area
    
    # Check normalized GeoJSON
    assert len(data["normalized_geojson"]["features"]) == 1
    feature = data["normalized_geojson"]["features"][0]
    assert feature["properties"]["geometry_valid"] is True
    assert "area_m2" in feature["properties"]
    assert "area_ha" in feature["properties"]
    assert "area_ac" in feature["properties"]


def test_upload_multiple_projects():
    """Test uploading paddocks from multiple projects."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Paddock A",
                    "Project__Name": "Project 1"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.5, 47.0],
                        [-109.4, 47.0],
                        [-109.4, 47.1],
                        [-109.5, 47.1],
                        [-109.5, 47.0]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Paddock B",
                    "Project__Name": "Project 2"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.3, 47.0],
                        [-109.2, 47.0],
                        [-109.2, 47.1],
                        [-109.3, 47.1],
                        [-109.3, 47.0]
                    ]]
                }
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Paddock C",
                    "Project__Name": "Project 1"  # Same as first
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.1, 47.0],
                        [-109.0, 47.0],
                        [-109.0, 47.1],
                        [-109.1, 47.1],
                        [-109.1, 47.0]
                    ]]
                }
            }
        ]
    }
    
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("test.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check counts
    assert data["summary"]["total_projects"] == 2
    assert data["summary"]["total_paddocks"] == 3
    
    # Check projects are grouped correctly
    projects = {p["project_name"]: p for p in data["projects"]}
    assert "Project 1" in projects
    assert "Project 2" in projects
    
    # Project 1 should have 2 paddocks
    assert projects["Project 1"]["paddock_count"] == 2
    assert len(projects["Project 1"]["paddocks"]) == 2
    
    # Project 2 should have 1 paddock
    assert projects["Project 2"]["paddock_count"] == 1
    assert len(projects["Project 2"]["paddocks"]) == 1


def test_upload_paddock_without_project():
    """Test that paddocks without project names are grouped as 'Unknown'."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Orphan Paddock",
                    "Project__Name": None  # No project
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.5, 47.0],
                        [-109.4, 47.0],
                        [-109.4, 47.1],
                        [-109.5, 47.1],
                        [-109.5, 47.0]
                    ]]
                }
            }
        ]
    }
    
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("test.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should be grouped under "Unknown"
    assert data["summary"]["total_projects"] == 1
    assert data["projects"][0]["project_name"] == "Unknown"


def test_upload_invalid_json():
    """Test uploading invalid JSON returns error."""
    file_content = b"not json at all"
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("bad.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 400
    assert "Invalid JSON" in response.json()["detail"]


def test_upload_wrong_file_type():
    """Test uploading non-GeoJSON file returns error."""
    file_content = b"some text content"
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("document.txt", file, "text/plain")}
    )
    
    assert response.status_code == 400
    assert "Please upload a .geojson" in response.json()["detail"]


def test_upload_not_feature_collection():
    """Test uploading valid JSON but not a FeatureCollection."""
    geojson = {
        "type": "Feature",  # Wrong! Should be FeatureCollection
        "properties": {},
        "geometry": {
            "type": "Point",
            "coordinates": [-109.5, 47.0]
        }
    }
    
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("feature.geojson", file, "application/geo+json")}
    )
    
    assert response.status_code == 400
    assert "Expected a GeoJSON FeatureCollection" in response.json()["detail"]


def test_upload_invalid_geometry():
    """Test that invalid geometries are handled gracefully."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Bad Geometry",
                    "Project__Name": "Test"
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109.5, 47.0],
                        [-109.4, 47.1],
                        [-109.4, 47.0],
                        [-109.5, 47.1],  # Bow-tie (self-intersecting)
                        [-109.5, 47.0]
                    ]]
                }
            }
        ]
    }
    
    file_content = json.dumps(geojson).encode()
    file = io.BytesIO(file_content)
    
    response = client.post(
        "/api/upload",
        files={"file": ("test.geojson", file, "application/geo+json")}
    )
    
    # Should succeed (geometry gets repaired)
    assert response.status_code == 200
    data = response.json()
    
    # Geometry should be repaired and valid
    assert data["summary"]["invalid_paddocks"] == 0
    assert data["projects"][0]["valid_paddocks"] == 1
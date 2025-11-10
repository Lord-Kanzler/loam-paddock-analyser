"""
Geometry processing and geodesic area calculations.

This module handles:
1. Converting GeoJSON to Shapely geometries
2. Validating and repairing invalid geometries
3. Calculating geodesic area (accounting for Earth's curvature)
4. Supporting multiple units (m², hectares, acres)
"""

from typing import Dict, Any, Optional, Tuple
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid
from pyproj import Geod

# WGS84 ellipsoid - standard for GPS and GeoJSON
# This is Earth's actual shape (slightly flattened sphere)
WGS84 = Geod(ellps="WGS84")


def calculate_geodesic_area_m2(geom: BaseGeometry) -> float:
    """
    Calculate geodesic area in square meters.
    
    Why geodesic instead of planar?
    - Planar assumes flat surface (wrong for large areas)
    - Geodesic accounts for Earth's curvature
    - Example: A 1° × 1° square at equator ≈ 12,364 km²
    
    Handles:
    - Simple polygons
    - Polygons with holes (subtracts hole area)
    - MultiPolygons (sums all parts)
    
    Args:
        geom: Shapely geometry object
        
    Returns:
        Area in square meters (always positive)
    """
    
    def _polygon_area(poly: Polygon) -> float:
        """Calculate area of a single polygon including holes."""
        # Get exterior ring coordinates
        lons, lats = poly.exterior.coords.xy
        
        # Calculate area using geodesic method
        # Returns: (area, perimeter)
        area, _ = WGS84.polygon_area_perimeter(lons, lats)
        
        # Subtract holes (interior rings)
        for interior_ring in poly.interiors:
            i_lons, i_lats = interior_ring.coords.xy
            hole_area, _ = WGS84.polygon_area_perimeter(i_lons, i_lats)
            # hole_area is typically negative, so adding it subtracts
            area += hole_area
        
        return abs(area)
    
    # Handle different geometry types
    if isinstance(geom, Polygon):
        return _polygon_area(geom)
    elif isinstance(geom, MultiPolygon):
        # Sum all component polygons
        return sum(_polygon_area(p) for p in geom.geoms)
    else:
        # Unsupported type (Point, LineString, etc.)
        return 0.0


def validate_and_repair_geometry(feature: Dict[str, Any]) -> Tuple[Optional[BaseGeometry], Optional[str]]:
    """
    Validate and attempt to repair a feature's geometry.
    
    Process:
    1. Parse GeoJSON geometry to Shapely
    2. Check if geometry is valid
    3. If invalid, attempt repair using make_valid()
    4. Check if result is empty
    
    Args:
        feature: GeoJSON Feature dict
        
    Returns:
        Tuple of (geometry, error_message)
        - geometry: Valid Shapely geometry or None if unfixable
        - error_message: None if valid, error description if invalid
        
    Common issues that can be repaired:
    - Self-intersecting polygons
    - Duplicate vertices
    - Bow-tie polygons
    - Invalid ring orientation
    """
    try:
        geometry_dict = feature.get("geometry")
        if not geometry_dict:
            return None, "Missing geometry"
        
        # Convert GeoJSON to Shapely
        geom = shape(geometry_dict)
        
        # Check if valid
        if not geom.is_valid:
            # Attempt to repair
            geom = make_valid(geom)
            
            # Check if repair succeeded
            if not geom.is_valid:
                return None, "Could not repair invalid geometry"
        
        # Check if empty (can happen after repair)
        if geom.is_empty:
            return None, "Empty geometry after repair"
        
        return geom, None
        
    except Exception as e:
        return None, f"Geometry error: {str(e)}"


def get_feature_area(feature: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract and calculate area for a GeoJSON feature.
    
    Args:
        feature: GeoJSON Feature dict
        
    Returns:
        Dict with area in multiple units, or None if geometry is invalid
        {
            "area_m2": 1234567.89,
            "area_ha": 123.46,
            "area_ac": 305.12
        }
    """
    # Validate and repair geometry
    geom, error = validate_and_repair_geometry(feature)
    
    if error or not geom:
        return None
    
    # Calculate area in square meters
    area_m2 = calculate_geodesic_area_m2(geom)
    
    # Convert to other units
    # 1 hectare = 10,000 m²
    # 1 acre = 4,046.86 m² (approximately)
    return {
        "area_m2": area_m2,
        "area_ha": area_m2 / 10_000,
        "area_ac": area_m2 * 0.000247105,  # More precise conversion factor
    }


def create_normalized_feature(feature: Dict[str, Any], area_info: Optional[Dict[str, float]]) -> Dict[str, Any]:
    """
    Create a normalized GeoJSON feature with computed area properties.
    
    Args:
        feature: Original GeoJSON Feature
        area_info: Area calculations (or None if invalid)
        
    Returns:
        Normalized Feature dict with area properties added
    """
    # Validate and repair geometry
    geom, error = validate_and_repair_geometry(feature)
    
    # Start with original feature
    normalized = {
        "type": "Feature",
        "geometry": feature.get("geometry"),
        "properties": dict(feature.get("properties", {}))
    }
    
    # Add computed area properties if valid
    if area_info and geom:
        normalized["properties"]["area_m2"] = round(area_info["area_m2"], 2)
        normalized["properties"]["area_ha"] = round(area_info["area_ha"], 2)
        normalized["properties"]["area_ac"] = round(area_info["area_ac"], 2)
        normalized["properties"]["geometry_valid"] = True
        
        # Update geometry to repaired version
        normalized["geometry"] = geom.__geo_interface__
    else:
        normalized["properties"]["geometry_valid"] = False
        normalized["properties"]["error"] = error or "Unknown error"
    
    return normalized

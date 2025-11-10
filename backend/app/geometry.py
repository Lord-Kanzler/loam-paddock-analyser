"""
Geometry processing and geodesic area calculations.

This module handles:
1. Converting GeoJSON to Shapely geometries
2. Calculating geodesic area (accounting for Earth's curvature)
3. Supporting multiple units (m², hectares, acres)
"""

from typing import Dict, Any, Optional
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely.geometry.base import BaseGeometry
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
    try:
        # Convert GeoJSON geometry to Shapely object
        geometry = feature.get("geometry")
        if not geometry:
            return None

        geom = shape(geometry)

        # Check if geometry is valid and not empty
        if not geom.is_valid or geom.is_empty:
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

    except Exception as e:
        # Geometry parsing or calculation failed
        print(f"Error calculating area: {e}")
        return None

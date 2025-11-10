"""
Tests for geometry processing and area calculations.

These tests verify:
- Geodesic area calculations are working
- Area conversions (m², ha, acres) are correct
- Geometry validation and repair works
"""

import pytest
from shapely.geometry import Polygon, MultiPolygon
from app.geometry import (
    calculate_geodesic_area_m2,
    validate_and_repair_geometry,
    get_feature_area,
)


def test_simple_polygon_area():
    """Test area calculation for a simple square polygon."""
    # Create a ~0.1° x 0.1° square near Montana
    # At this latitude, ~0.1° ≈ 11km x 8km
    poly = Polygon(
        [[-109.5, 47.0], [-109.4, 47.0], [-109.4, 47.1], [-109.5, 47.1], [-109.5, 47.0]]
    )

    area_m2 = calculate_geodesic_area_m2(poly)

    # Should be roughly 88 km² = 88,000,000 m²
    # (11km × 8km ≈ 88 km²)
    assert 80_000_000 < area_m2 < 95_000_000

    # Convert to hectares (1 ha = 10,000 m²)
    area_ha = area_m2 / 10_000
    assert 8000 < area_ha < 9500

    # Convert to acres (1 ac ≈ 4046.86 m²)
    area_ac = area_m2 * 0.000247105
    assert 19_000 < area_ac < 24_000


def test_polygon_with_hole():
    """Test that holes are correctly subtracted from area."""
    # Outer ring: 1° x 1° square
    outer = [
        [-109.0, 47.0],
        [-108.0, 47.0],
        [-108.0, 48.0],
        [-109.0, 48.0],
        [-109.0, 47.0],
    ]

    # Inner ring (hole): 0.5° x 0.5° square in center
    hole = [
        [-108.75, 47.25],
        [-108.25, 47.25],
        [-108.25, 47.75],
        [-108.75, 47.75],
        [-108.75, 47.25],
    ]

    # Polygon without hole
    poly_no_hole = Polygon(outer)
    area_no_hole = calculate_geodesic_area_m2(poly_no_hole)

    # Polygon with hole
    poly_with_hole = Polygon(outer, [hole])
    area_with_hole = calculate_geodesic_area_m2(poly_with_hole)

    # Area with hole should be less
    assert area_with_hole < area_no_hole

    # Hole should be roughly 1/4 the size of the outer square
    hole_area = area_no_hole - area_with_hole
    assert 0.2 < (hole_area / area_no_hole) < 0.3


def test_multipolygon_area():
    """Test that MultiPolygon areas are summed correctly."""
    poly1 = Polygon(
        [[-109.5, 47.0], [-109.4, 47.0], [-109.4, 47.1], [-109.5, 47.1], [-109.5, 47.0]]
    )

    poly2 = Polygon(
        [[-109.3, 47.0], [-109.2, 47.0], [-109.2, 47.1], [-109.3, 47.1], [-109.3, 47.0]]
    )

    area1 = calculate_geodesic_area_m2(poly1)
    area2 = calculate_geodesic_area_m2(poly2)

    multi = MultiPolygon([poly1, poly2])
    multi_area = calculate_geodesic_area_m2(multi)

    # MultiPolygon area should equal sum of parts (within rounding)
    assert abs(multi_area - (area1 + area2)) < 1.0  # Within 1 m²


def test_valid_geometry():
    """Test that valid geometries are accepted."""
    feature = {
        "type": "Feature",
        "properties": {"name": "Test"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-109.5, 47.0],
                    [-109.4, 47.0],
                    [-109.4, 47.1],
                    [-109.5, 47.1],
                    [-109.5, 47.0],
                ]
            ],
        },
    }

    geom, error = validate_and_repair_geometry(feature)

    assert geom is not None
    assert error is None
    assert geom.is_valid
    assert not geom.is_empty


def test_invalid_geometry_repair():
    """Test that invalid geometries are repaired when possible."""
    # Create a bow-tie polygon (self-intersecting)
    feature = {
        "type": "Feature",
        "properties": {"name": "Test"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-109.5, 47.0],
                    [-109.4, 47.1],  # Crossed
                    [-109.4, 47.0],  # lines
                    [-109.5, 47.1],  # create bow-tie
                    [-109.5, 47.0],
                ]
            ],
        },
    }

    geom, error = validate_and_repair_geometry(feature)

    # Should repair successfully
    assert geom is not None
    assert error is None
    assert geom.is_valid


def test_missing_geometry():
    """Test handling of features with missing geometry."""
    feature = {"type": "Feature", "properties": {"name": "Test"}, "geometry": None}

    geom, error = validate_and_repair_geometry(feature)

    assert geom is None
    assert "Missing geometry" in error


def test_get_feature_area_integration():
    """Test the complete area calculation pipeline."""
    feature = {
        "type": "Feature",
        "properties": {
            "name": "Test Paddock",
            "area_acres": 100,  # Original (possibly incorrect) value
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-109.5, 47.0],
                    [-109.4, 47.0],
                    [-109.4, 47.1],
                    [-109.5, 47.1],
                    [-109.5, 47.0],
                ]
            ],
        },
    }

    area_info = get_feature_area(feature)

    assert area_info is not None
    assert "area_m2" in area_info
    assert "area_ha" in area_info
    assert "area_ac" in area_info

    # All areas should be positive
    assert area_info["area_m2"] > 0
    assert area_info["area_ha"] > 0
    assert area_info["area_ac"] > 0

    # Check conversions are consistent
    assert abs(area_info["area_ha"] - (area_info["area_m2"] / 10_000)) < 0.01
    assert abs(area_info["area_ac"] - (area_info["area_m2"] * 0.000247105)) < 0.01


def test_sample_paddock_cornfield():
    """
    Test the exact CornField paddock from sample data.

    This tests why our calculation differs from the original.
    Original: 309.28 acres
    Our calculation: should be ~341 acres
    """
    cornfield_feature = {
        "type": "Feature",
        "properties": {
            "id": 24,
            "area_acres": 309.28,  # Original value
            "owner": "Stephanie Ice",
            "name": "CornField",
            "Project__Name": "Soybean2023",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-109.510006192959665, 46.969192404616209],
                    [-109.494450159174093, 46.969158579411769],
                    [-109.494374475773014, 46.97965376678124],
                    [-109.509930509560704, 46.979687591985687],
                    [-109.510006192959665, 46.969192404616209],
                ]
            ],
        },
    }

    area_info = get_feature_area(cornfield_feature)

    assert area_info is not None

    # Our geodesic calculation
    calculated_acres = area_info["area_ac"]

    # Original (possibly planar) calculation
    original_acres = 309.28

    print(f"\nCornField Analysis:")
    print(f"Original area_acres: {original_acres:.2f} ac")
    print(f"Calculated (geodesic): {calculated_acres:.2f} ac")
    print(
        f"Difference: {calculated_acres - original_acres:.2f} ac ({((calculated_acres - original_acres) / original_acres * 100):.1f}%)"
    )
    print(f"Area in hectares: {area_info['area_ha']:.2f} ha")
    print(f"Area in m²: {area_info['area_m2']:.2f} m²")

    # Our calculation should be larger (geodesic accounts for curvature)
    # At 47° latitude, geodesic should be ~10% larger than planar
    assert calculated_acres > original_acres
    assert 330 < calculated_acres < 350  # Should be ~341 acres

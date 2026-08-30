"""
Unit Tests for CIRIS GIS Service Engine.
"""

import pytest
from src.db.geo_models import BoundingBox
from src.services.gis_service import GISService, haversine_distance_km, create_circle_polygon


@pytest.fixture(scope="module")
def gis_service():
    return GISService()


def test_haversine_distance():
    # Distance between Mumbai (18.9388, 72.8354) and Pune (18.5204, 73.8567) is approx ~120 km
    dist = haversine_distance_km(18.9388, 72.8354, 18.5204, 73.8567)
    assert 110.0 <= dist <= 130.0

    # Distance to same point is 0
    assert haversine_distance_km(18.9388, 72.8354, 18.9388, 72.8354) == 0.0


def test_circle_polygon_generation():
    poly = create_circle_polygon(center_lat=19.0, center_lon=72.8, radius_km=5.0, num_points=16)
    assert len(poly) == 1
    # Linear ring should be closed (first and last coordinate match)
    assert poly[0][0] == poly[0][-1]
    assert len(poly[0]) == 17


def test_get_cases_geojson(gis_service):
    res = gis_service.get_cases_geojson(limit=10)
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) > 0
    assert len(res["features"]) <= 10

    # Check GeoJSON RFC 7946 feature format
    feat = res["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Point"
    assert len(feat["geometry"]["coordinates"]) == 2
    # Longitude is first in GeoJSON
    lon, lat = feat["geometry"]["coordinates"]
    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0
    assert "complaint_id" in feat["properties"]
    assert "fraud_type" in feat["properties"]


def test_cases_bounding_box_filter(gis_service):
    # Mumbai bounding box
    bbox = BoundingBox(min_lat=18.8, min_lon=72.7, max_lat=19.3, max_lon=73.1)
    res = gis_service.get_cases_geojson(bbox=bbox, limit=50)
    assert res["type"] == "FeatureCollection"
    for feat in res["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        assert 72.7 <= lon <= 73.1
        assert 18.8 <= lat <= 19.3


def test_cases_radius_filter(gis_service):
    # Search within 15 km of Mumbai center
    res = gis_service.get_cases_geojson(center_lat=19.0760, center_lon=72.8777, radius_km=15.0, limit=20)
    assert res["type"] == "FeatureCollection"
    for feat in res["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        dist = haversine_distance_km(19.0760, 72.8777, lat, lon)
        assert dist <= 15.1  # with slight float tolerance


def test_cases_clustering(gis_service):
    res = gis_service.get_cases_geojson(limit=100, cluster=True, zoom=8)
    assert res["type"] == "FeatureCollection"
    assert res.get("metadata", {}).get("clustered") is True
    # Verify cluster features have point_count
    for feat in res["features"]:
        if feat["properties"].get("cluster"):
            assert feat["properties"]["point_count"] >= 1


def test_predicted_atms_geojson(gis_service):
    res = gis_service.get_predicted_atms_geojson(limit=10)
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) > 0
    feat = res["features"][0]
    assert feat["geometry"]["type"] == "Point"
    assert "atm_id" in feat["properties"]
    assert "prediction_score" in feat["properties"]
    assert "rank" in feat["properties"]


def test_risk_heatmap_geojson(gis_service):
    res = gis_service.get_risk_heatmap_geojson()
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) > 0
    types = {f["geometry"]["type"] for f in res["features"]}
    assert "Point" in types
    assert "Polygon" in types


def test_networks_geojson(gis_service):
    res = gis_service.get_networks_geojson(limit=10, include_nodes=True, include_edges=True)
    assert res["type"] == "FeatureCollection"
    geom_types = {f["geometry"]["type"] for f in res["features"]}
    assert "LineString" in geom_types or "Point" in geom_types


def test_merchants_geojson(gis_service):
    res = gis_service.get_merchants_geojson(limit=10)
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) > 0
    feat = res["features"][0]
    assert "entity_id" in feat["properties"]
    assert "risk_score" in feat["properties"]


def test_nearby_entities(gis_service):
    # Search around Delhi center
    res = gis_service.get_nearby_entities(lat=28.6139, lon=77.2090, radius_km=25.0, limit=20)
    assert res["type"] == "FeatureCollection"
    assert len(res["features"]) > 0
    distances = [f["properties"]["distance_km"] for f in res["features"]]
    # Distances should be sorted ascending
    assert distances == sorted(distances)


def test_viewport_query(gis_service):
    res = gis_service.get_viewport_data(
        min_lat=18.5, min_lon=72.5, max_lat=19.5, max_lon=73.5, zoom=10
    )
    assert "viewport" in res
    assert "layers" in res
    assert "cases" in res["layers"]
    assert "predicted_atms" in res["layers"]
    assert "risk" in res["layers"]


def test_map_layer_definitions():
    layers = GISService.get_map_layer_definitions()
    assert len(layers) >= 5
    layer_ids = {l["id"] for l in layers}
    assert {"cases", "predicted_atms", "risk", "networks", "merchants"}.issubset(layer_ids)


def test_gis_stats(gis_service):
    stats = gis_service.get_gis_stats()
    assert stats["total_cases_mapped"] > 0
    assert stats["total_atms_indexed"] > 0
    assert stats["total_predictions_indexed"] > 0
    assert stats["geographic_envelope_bbox"] is not None

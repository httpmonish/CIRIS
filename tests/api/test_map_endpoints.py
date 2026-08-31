"""
Integration Tests for CIRIS GIS & Map Data FastAPI Endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_root_and_health_endpoints():
    r_root = client.get("/")
    assert r_root.status_code == 200

    r_info = client.get("/api-info")
    assert r_info.status_code == 200
    data = r_info.json()
    assert data["status"] == "OPERATIONAL"


def test_get_cases_endpoint():
    response = client.get("/api/v1/map/cases?limit=25")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) <= 25
    assert len(data["features"]) > 0

    # Test filtering by fraud_type
    r_filtered = client.get("/api/v1/map/cases?fraud_type=UPI%20Fraud&limit=10")
    assert r_filtered.status_code == 200
    for f in r_filtered.json()["features"]:
        assert f["properties"]["fraud_type"] == "UPI Fraud"


def test_get_predicted_atms_endpoint():
    response = client.get("/api/v1/map/predicted-atms?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    first_feat = data["features"][0]
    assert "prediction_score" in first_feat["properties"]
    assert "rank" in first_feat["properties"]


def test_get_risk_endpoint():
    response = client.get("/api/v1/map/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_get_networks_endpoint():
    response = client.get("/api/v1/map/networks?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"


def test_get_merchants_endpoint():
    response = client.get("/api/v1/map/merchants?limit=20")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0


def test_get_nearby_endpoint():
    # Query nearby entities around Bengaluru (12.9716, 77.5946)
    response = client.get("/api/v1/map/nearby?lat=12.9716&lon=77.5946&radius_km=30&limit=15")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    assert "distance_km" in data["features"][0]["properties"]


def test_get_viewport_endpoint():
    response = client.get("/api/v1/map/viewport?min_lat=12.0&min_lon=76.0&max_lat=14.0&max_lon=78.0&zoom=10")
    assert response.status_code == 200
    data = response.json()
    assert "viewport" in data
    assert "layers" in data
    assert "cases" in data["layers"]
    assert "predicted_atms" in data["layers"]


def test_get_layers_endpoint():
    response = client.get("/api/v1/map/layers")
    assert response.status_code == 200
    layers = response.json()
    assert isinstance(layers, list)
    assert len(layers) >= 5


def test_get_stats_endpoint():
    response = client.get("/api/v1/map/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_cases_mapped"] > 0
    assert stats["total_atms_indexed"] > 0
    assert stats["total_predictions_indexed"] > 0

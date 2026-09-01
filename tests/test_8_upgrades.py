"""
Automated Test Suite for the 8 CIRIS High-Impact SIH Upgrades.
Verifies:
1. Product claim reframing
2. Confidence-tiered dispatch logic
3. SHAP explainability and Section 65B SHA-256 hashing
4. Data provenance disclosure
5. Live case simulation & injection endpoint
6. Mocked Last-Mile WhatsApp/SMS alert dispatcher
7. Isolation Forest anomaly scoring
8. DPDP Act 2023 & CFCFRMS positioning
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.services.gis_service import compute_confidence_tier
from src.ml.explainability.shap_explainer import get_shap_explainer
from src.services.notification_service import get_notification_service


@pytest.fixture
def client():
    return TestClient(app)


def test_upgrade_1_reframed_claims(client):
    """Upgrade 1: Verify search-space reduction claims in FastAPI description."""
    assert "Search-Space Reduction" in app.title
    assert "7,000 candidate ATMs" in app.description
    assert "63.6%" in app.description


def test_upgrade_2_confidence_tiered_logic():
    """Upgrade 2: Verify confidence tiered decision thresholds."""
    tier_high, _ = compute_confidence_tier(0.95)
    assert tier_high == "AUTO_FREEZE_RECOMMENDED"

    tier_mid, _ = compute_confidence_tier(0.82)
    assert tier_mid == "LEA_ALERT"

    tier_low, _ = compute_confidence_tier(0.64)
    assert tier_low == "MONITOR_ONLY"


def test_upgrade_3_shap_explainability():
    """Upgrade 3: Verify SHAP explainability generates top factors and SHA-256 hash."""
    explainer = get_shap_explainer()
    sample_features = {
        "distance_km": 2.1,
        "historical_cashouts": 11,
        "hotspot_score": 0.82,
        "anomaly_score": 0.88,
        "withdrawal_delay_hours": 1.8
    }
    explanation = explainer.explain_candidate(sample_features, top_k=4)

    assert "top_contributing_factors" in explanation
    assert len(explanation["top_contributing_factors"]) >= 3
    assert "sha256_audit_hash" in explanation
    assert len(explanation["sha256_audit_hash"]) == 64


def test_upgrade_4_data_provenance_file_exists():
    """Upgrade 4: Verify static provenance document exists with benchmark calibration."""
    import os
    assert os.path.exists("CIRIS_DATA_PROVENANCE.md")
    with open("CIRIS_DATA_PROVENANCE.md", "r") as f:
        content = f.read()
    assert "50,000 Cybercrime Incident Complaints" in content
    assert "DPDP Act 2023" in content
    assert "CFCFRMS" in content


def test_upgrade_5_live_case_simulation(client):
    """Upgrade 5: Verify POST /api/v1/cases/simulate returns dynamic case and predictions."""
    response = client.post("/api/v1/cases/simulate")
    assert response.status_code == 200
    data = response.json()
    assert "NCRP-2026-SIM-" in data["case_id"]
    assert "predictions" in data
    assert len(data["predictions"]) >= 2
    assert "shap_explanation" in data["predictions"][0]


def test_upgrade_6_mocked_last_mile_dispatcher(client):
    """Upgrade 6: Verify last-mile emergency alert dispatcher endpoint."""
    response = client.get("/api/v1/alerts/dispatches")
    assert response.status_code == 200
    dispatches = response.json()
    assert isinstance(dispatches, list)
    assert len(dispatches) > 0
    assert "google_maps_url" in dispatches[0]
    assert "maps.google.com" in dispatches[0]["google_maps_url"]


def test_upgrade_7_isolation_forest_anomaly_case(client):
    """Upgrade 7: Verify Isolation Forest anomaly attribution in candidate explanation."""
    explainer = get_shap_explainer()
    anomaly_features = {
        "distance_km": 2.1,
        "historical_cashouts": 11,
        "hotspot_score": 0.88,
        "anomaly_score": 0.88,
        "withdrawal_delay_hours": 1.8
    }
    explanation = explainer.explain_candidate(anomaly_features)
    has_anomaly_factor = any(
        "anomaly" in f["feature"].lower() or "anomaly" in f["label"].lower()
        for f in explanation["top_contributing_factors"]
    )
    assert has_anomaly_factor is True


def test_upgrade_8_compliance_in_frontend():
    """Upgrade 8: Verify DPDP 2023 and CFCFRMS statements in index.html."""
    with open("CIRIS REAL SIH PROJECT FRONTEND/index.html", "r", encoding="utf-8") as f:
        html = f.read()
    assert "DPDP Act 2023 Compliance Architecture" in html
    assert "Upstream Integration with I4C's CFCFRMS" in html
    assert "provenance-modal" in html

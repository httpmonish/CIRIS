"""
Targeted API Tests for CIRIS FastAPI Backend.
"""

import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.main import app
from src.db.schema import setup_database

client = TestClient(app)


def setup_module():
    setup_database()


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "UP"


def test_root_endpoint():
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert "swagger_docs" in data


def test_system_status_endpoint():
    res = client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert "components" in data
    assert data["components"]["api"] == "ONLINE"


def test_create_case_endpoint():
    payload = {
        "complaint_id": "CMP_TEST_API_001",
        "reported_loss_amount": 45000.0,
        "fraud_type": "Investment Cyber Fraud",
        "victim_location": {
            "state": "Maharashtra",
            "district": "Mumbai",
            "city": "Mumbai",
            "latitude": 19.1136,
            "longitude": 72.8697,
        },
    }
    res = client.post("/api/v1/cases", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["complaint_id"] == "CMP_TEST_API_001"
    assert data["case_id"] == "CASE-CMP_TEST_API_001"
    assert "overall_risk_score" in data


def test_list_cases_endpoint():
    res = client.get("/api/v1/cases")
    assert res.status_code == 200
    data = res.json()
    assert "cases" in data
    assert isinstance(data["cases"], list)


def test_get_case_by_id_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "CASE-CMP_TEST_API_001"
    assert data["reported_loss"] == 45000.0


def test_case_intelligence_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/intelligence")
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "CASE-CMP_TEST_API_001"
    assert "overall_case_risk" in data
    assert "potential_endpoints" in data


def test_money_flow_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/money-flow")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data


def test_prediction_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/prediction")
    assert res.status_code == 200
    data = res.json()
    assert data["endpoint_type"] == "ATM"
    assert "score" in data


def test_endpoints_classification_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/endpoints")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_amount_at_risk_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/amount-at-risk")
    assert res.status_code == 200
    data = res.json()
    assert "disputed_amount" in data
    assert "observed_remaining" in data


def test_evidence_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/evidence")
    assert res.status_code == 200
    data = res.json()
    assert "MODEL_EVIDENCE" in data
    assert "GRAPH_EVIDENCE" in data


def test_timeline_endpoint():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/timeline")
    assert res.status_code == 200
    data = res.json()
    assert "timeline" in data


def test_entity_endpoint():
    res = client.get("/api/v1/entities/ENT_001")
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "ENT_001"
    assert "accounts" in data


def test_transaction_endpoint():
    res = client.get("/api/v1/transactions/TX_001")
    assert res.status_code == 200
    data = res.json()
    assert data["transaction_id"] == "TX_001"


def test_atm_endpoint():
    res = client.get("/api/v1/atms/ATM_9981")
    assert res.status_code == 200
    data = res.json()
    assert data["atm_id"] == "ATM_9981"


def test_alerts_workflow_endpoints():
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200

    # Acknowledge
    res_ack = client.post("/api/v1/alerts/ALT-CASE-CMP_TEST_API_001/acknowledge")
    if res_ack.status_code == 200:
        assert res_ack.json()["acknowledged"] is True

    # Assign
    res_ass = client.post(
        "/api/v1/alerts/ALT-CASE-CMP_TEST_API_001/assign",
        json={"assigned_to": "Officer_Sharma"},
    )
    if res_ass.status_code == 200:
        assert res_ass.json()["assigned_to"] == "Officer_Sharma"


def test_intervention_endpoints():
    res = client.get("/api/v1/cases/CASE-CMP_TEST_API_001/intervention")
    assert res.status_code == 200
    data = res.json()
    assert "recommended_action" in data

    # Review
    res_rev = client.post(
        "/api/v1/cases/CASE-CMP_TEST_API_001/intervention/review",
        json={
            "reviewer": "Officer_Kulkarni",
            "decision": "APPROVE_HOLD_REVIEW",
            "notes": "Reviewed and approved for bank lien workflow",
        },
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["reviewed_by"] == "Officer_Kulkarni"


def test_gis_geojson_endpoints():
    res_risk = client.get("/api/v1/map/risk")
    assert res_risk.status_code == 200
    assert res_risk.json()["type"] == "FeatureCollection"

    res_atms = client.get("/api/v1/map/predicted-atms")
    assert res_atms.status_code == 200
    assert res_atms.json()["type"] == "FeatureCollection"


def test_networks_endpoint():
    res = client.get("/api/v1/networks/CLUST_001?hop_depth=2")
    assert res.status_code == 200
    data = res.json()
    assert data["network_id"] == "CLUST_001"


def test_404_error_handling():
    res = client.get("/api/v1/cases/NON_EXISTENT_CASE_ID_999")
    assert res.status_code == 404
    data = res.json()
    assert "detail" in data

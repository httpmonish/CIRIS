"""
Demo Scenario & Seed Integrity Tests for CIRIS Productization.

Validates that CASE-DEMO-001 and CASE-DEMO-002 are seeded cleanly and idempotently.
"""

import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.seed_demo import seed_demo_data
from src.main import app

client = TestClient(app)


def test_demo_seed_execution_and_idempotency():
    # Run seeding twice to verify idempotency (no duplicate errors)
    seed_demo_data()
    seed_demo_data()

    # 1. Verify CASE-DEMO-001 (ATM Cashout Endpoint)
    res1 = client.get("/api/v1/cases/CASE-DEMO-001")
    assert res1.status_code == 200
    case1 = res1.json()
    assert case1["case_id"] == "CASE-DEMO-001"
    assert case1["reported_loss"] == 50000.0

    res1_pred = client.get("/api/v1/cases/CASE-DEMO-001/prediction")
    assert res1_pred.status_code == 200
    pred1 = res1_pred.json()
    assert pred1["endpoint_type"] == "ATM"
    assert "atm_id" in pred1 and len(pred1["atm_id"]) > 0

    # 2. Verify CASE-DEMO-002 (Merchant/Transfer Endpoint)
    res2 = client.get("/api/v1/cases/CASE-DEMO-002")
    assert res2.status_code == 200
    case2 = res2.json()
    assert case2["case_id"] == "CASE-DEMO-002"
    assert case2["reported_loss"] == 120000.0

    res2_eps = client.get("/api/v1/cases/CASE-DEMO-002/endpoints")
    assert res2_eps.status_code == 200
    eps2 = res2_eps.json()
    assert any(ep["endpoint_type"] == "MERCHANT" for ep in eps2)

    print("✔ Demo Scenario & Seed Integrity Tests Passed!")

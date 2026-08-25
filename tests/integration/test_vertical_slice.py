"""
Vertical Slice Integration Test for CIRIS Productization.

Tests complete workflow:
COMPLAINT -> CASE CREATION -> CASE INTELLIGENCE -> MONEY FLOW ->
ENTITY NETWORK -> RISK -> AMOUNT AT RISK -> NEXT ENDPOINT -> ATM PREDICTION ->
TIME -> WHY/EVIDENCE -> INTERVENTION RECOMMENDATION
"""

import sys
import os
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.main import app
from src.db.schema import setup_database

client = TestClient(app)


def test_complete_vertical_slice():
    setup_database()

    # 1. Complaint Submission / Case Creation
    payload = {
        "complaint_id": "CMP_VERTICAL_SLICE_99",
        "reported_loss_amount": 100000.0,
        "fraud_type": "Investment Cyber Fraud",
        "victim_location": {
            "state": "Maharashtra",
            "district": "Mumbai",
            "city": "Mumbai",
            "latitude": 19.1136,
            "longitude": 72.8697,
        },
    }

    res_create = client.post("/api/v1/cases", json=payload)
    assert res_create.status_code == 201
    create_data = res_create.json()
    case_id = create_data["case_id"]
    assert case_id == "CASE-CMP_VERTICAL_SLICE_99"

    # 2. Read Case Intelligence
    res_intel = client.get(f"/api/v1/cases/{case_id}/intelligence")
    assert res_intel.status_code == 200
    intel = res_intel.json()

    assert intel["case_id"] == case_id
    assert "overall_case_risk" in intel
    assert intel["disputed_amount"] == 100000.0

    # 3. Read Money Flow Graph
    res_flow = client.get(f"/api/v1/cases/{case_id}/money-flow")
    assert res_flow.status_code == 200
    flow = res_flow.json()
    assert len(flow["nodes"]) > 0
    assert len(flow["edges"]) > 0

    # 4. Read Endpoint & ATM Predictions
    res_pred = client.get(f"/api/v1/cases/{case_id}/prediction")
    assert res_pred.status_code == 200
    pred = res_pred.json()
    assert pred["endpoint_type"] == "ATM"
    assert "atm_name" in pred
    assert "predicted_time_window" in pred

    # 5. Read Amount at Risk Accounting
    res_ar = client.get(f"/api/v1/cases/{case_id}/amount-at-risk")
    assert res_ar.status_code == 200
    ar = res_ar.json()
    assert ar["disputed_amount"] == 100000.0

    # 6. Read Evidence & SHAP Attributions
    res_ev = client.get(f"/api/v1/cases/{case_id}/evidence")
    assert res_ev.status_code == 200
    ev = res_ev.json()
    assert "MODEL_EVIDENCE" in ev

    # 7. Read & Review Intervention
    res_int = client.get(f"/api/v1/cases/{case_id}/intervention")
    assert res_int.status_code == 200
    interv = res_int.json()
    assert "recommended_action" in interv

    # Officer review
    res_review = client.post(
        f"/api/v1/cases/{case_id}/intervention/review",
        json={
            "reviewer": "Officer_Deshmukh",
            "decision": "APPROVE_HOLD_REVIEW",
            "notes": "Approved for bank lien review",
        },
    )
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "REVIEWED"
    assert res_review.json()["reviewed_by"] == "Officer_Deshmukh"

    print("✔ Complete Vertical Slice Integration Test Passed!")

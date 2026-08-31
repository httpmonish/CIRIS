"""
Automated Test Suite for Authentication & Role-Based Access Control (RBAC).
Verifies:
1. Multi-role user registration and login token issuance.
2. Role-based endpoint guards (401 unauthenticated / 403 unauthorized).
3. Strict multi-tenant Row-Level Security (Bank data isolation).
4. Citizen complaint submission and private history retrieval.
5. Bank Official internal action and LEA direct escalation.
6. Government Official global supervisory oversight.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db.auth_db import seed_default_auth_data
from src.security.auth import hash_password

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_auth_environment():
    """Ensure auth tables and demo users are seeded before tests run."""
    seed_default_auth_data(hash_func=hash_password)


def test_public_bank_list():
    """Verify public banks list for registration and complaint targeting."""
    res = client.get("/api/v1/auth/banks")
    assert res.status_code == 200
    banks = res.json()
    assert len(banks) >= 5
    bank_ids = [b["id"] for b in banks]
    assert "BANK_SBI" in bank_ids
    assert "BANK_ICICI" in bank_ids


def test_unauthenticated_access_blocked():
    """Verify strict route protection: unauthenticated requests to protected endpoints return 401."""
    # List complaints without token
    res = client.get("/api/v1/complaints")
    assert res.status_code == 401

    # Submit complaint without token
    res = client.post("/api/v1/complaints", json={"target_bank_id": "BANK_ICICI", "disputed_amount": 1000, "transaction_rrn": "RRN1", "fraud_type": "UPI", "victim_city": "Delhi"})
    assert res.status_code == 401

    # Govt overview without token
    res = client.get("/api/v1/complaints/overview/govt")
    assert res.status_code == 401


def test_demo_user_logins():
    """Verify all 3 pre-seeded demonstration accounts authenticate successfully."""
    # 1. Citizen Login
    r_cit = client.post("/api/v1/auth/login", json={"email": "citizen@ciris.gov.in", "password": "Citizen@123"})
    assert r_cit.status_code == 200
    d_cit = r_cit.json()
    assert d_cit["user"]["role"] == "CITIZEN"
    assert "access_token" in d_cit

    # 2. Bank Official (ICICI) Login
    r_bnk = client.post("/api/v1/auth/login", json={"email": "nodal.icici@bank.in", "password": "Bank@123"})
    assert r_bnk.status_code == 200
    d_bnk = r_bnk.json()
    assert d_bnk["user"]["role"] == "BANK_OFFICIAL"
    assert d_bnk["user"]["bank_id"] == "BANK_ICICI"

    # 3. Government Official Login
    r_gvt = client.post("/api/v1/auth/login", json={"email": "officer.i4c@mha.gov.in", "password": "GovtAdmin@123"})
    assert r_gvt.status_code == 200
    d_gvt = r_gvt.json()
    assert d_gvt["user"]["role"] == "GOVT_OFFICIAL"
    assert d_gvt["user"]["govt_badge_id"] == "I4C-DIRECTOR-0891"


def test_citizen_complaint_workflow():
    """Verify Citizen can submit complaint and view only their own complaints."""
    # Authenticate as Citizen
    r_login = client.post("/api/v1/auth/login", json={"email": "citizen@ciris.gov.in", "password": "Citizen@123"})
    token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Submit new complaint
    payload = {
        "target_bank_id": "BANK_ICICI",
        "disputed_amount": 25000.0,
        "transaction_rrn": "UPI998877665544",
        "fraud_type": "DIGITAL_ARREST",
        "victim_city": "Mumbai",
        "evidence_notes": "Fake CBI digital arrest extortion call"
    }
    r_sub = client.post("/api/v1/complaints", json=payload, headers=headers)
    assert r_sub.status_code == 201
    complaint_res = r_sub.json()
    assert complaint_res["status"] == "SUCCESS"
    assert "complaint_number" in complaint_res

    # Retrieve citizen complaints
    r_list = client.get("/api/v1/complaints", headers=headers)
    assert r_list.status_code == 200
    complaints = r_list.json()
    assert len(complaints) >= 1
    for c in complaints:
        assert c["citizen_id"] == "USR_CITIZEN_001"


def test_bank_official_data_isolation():
    """
    CRITICAL TEST: Multi-tenant Bank Data Isolation.
    ICICI Bank Official must ONLY see ICICI complaints and CANNOT action SBI complaints.
    """
    # 1. Login as ICICI Nodal Officer
    r_icici = client.post("/api/v1/auth/login", json={"email": "nodal.icici@bank.in", "password": "Bank@123"})
    token_icici = r_icici.json()["access_token"]
    headers_icici = {"Authorization": f"Bearer {token_icici}"}

    # 2. Login as SBI Nodal Officer
    r_sbi = client.post("/api/v1/auth/login", json={"email": "nodal.sbi@bank.in", "password": "Bank@123"})
    token_sbi = r_sbi.json()["access_token"]
    headers_sbi = {"Authorization": f"Bearer {token_sbi}"}

    # ICICI complaints view
    r_icici_list = client.get("/api/v1/complaints", headers=headers_icici)
    assert r_icici_list.status_code == 200
    icici_complaints = r_icici_list.json()
    for c in icici_complaints:
        assert c["target_bank_id"] == "BANK_ICICI"  # Zero data leakage from other banks

    # SBI complaints view
    r_sbi_list = client.get("/api/v1/complaints", headers=headers_sbi)
    assert r_sbi_list.status_code == 200
    sbi_complaints = r_sbi_list.json()
    for c in sbi_complaints:
        assert c["target_bank_id"] == "BANK_SBI"

    # Cross-bank unauthorized action test: ICICI officer tries to action an SBI complaint (CMP_002)
    r_hack = client.post(
        "/api/v1/complaints/CMP_002/action",
        json={"action_type": "ACCOUNT_FROZEN", "notes": "Unauthorized cross-bank attempt"},
        headers=headers_icici
    )
    assert r_hack.status_code == 404  # Blocked by isolation logic


def test_bank_action_and_lea_escalation():
    """Verify Bank Official can freeze account and escalate to Law Enforcement."""
    r_icici = client.post("/api/v1/auth/login", json={"email": "nodal.icici@bank.in", "password": "Bank@123"})
    headers_icici = {"Authorization": f"Bearer {r_icici.json()['access_token']}"}

    # Freeze mule account on CMP_001
    r_act = client.post(
        "/api/v1/complaints/CMP_001/action",
        json={"action_type": "ACCOUNT_FROZEN", "notes": "Beneficiary mule account locked via CBS API."},
        headers=headers_icici
    )
    assert r_act.status_code == 200
    assert r_act.json()["updated_status"] == "ACCOUNT_FROZEN"

    # Escalate CMP_001 to LEA
    r_esc = client.post(
        "/api/v1/complaints/CMP_001/escalate",
        json={
            "lea_jurisdiction": "I4C Interstate Cybercrime Cell / Hyderabad Beat",
            "escalation_reason": "High-velocity splinter cashout detected at ATM cluster."
        },
        headers=headers_icici
    )
    assert r_esc.status_code == 200
    assert r_esc.json()["status"] == "ESCALATED_TO_LAW_ENFORCEMENT"


def test_govt_official_global_oversight():
    """Verify Government Official (Super Admin) sees all complaints across all banks and system metrics."""
    r_govt = client.post("/api/v1/auth/login", json={"email": "officer.i4c@mha.gov.in", "password": "GovtAdmin@123"})
    headers_govt = {"Authorization": f"Bearer {r_govt.json()['access_token']}"}

    # Global complaints list
    r_all = client.get("/api/v1/complaints", headers=headers_govt)
    assert r_all.status_code == 200
    all_complaints = r_all.json()
    # Contains complaints from both ICICI and SBI
    bank_ids = set(c["target_bank_id"] for c in all_complaints)
    assert "BANK_ICICI" in bank_ids
    assert "BANK_SBI" in bank_ids

    # Global overview metrics
    r_metrics = client.get("/api/v1/complaints/overview/govt", headers=headers_govt)
    assert r_metrics.status_code == 200
    metrics = r_metrics.json()
    assert metrics["badge_id"] == "I4C-DIRECTOR-0891"
    assert metrics["total_complaints"] >= 3
    assert metrics["monitored_banks"] >= 5

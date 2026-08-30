"""
Phase 4 Tests: FastAPI HTTP Endpoints Integration Tests.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_alerts_api():
    # List alerts
    r_list = client.get("/api/v1/alerts?limit=10")
    assert r_list.status_code == 200
    alerts = r_list.json()
    assert isinstance(alerts, list)

    if alerts:
        alt_id = alerts[0]["alert_id"]
        r_get = client.get(f"/api/v1/alerts/{alt_id}")
        assert r_get.status_code == 200
        assert r_get.json()["alert_id"] == alt_id


def test_cases_investigation_api():
    # Test on CASE_000001
    r_inv = client.get("/api/v1/cases/CASE_000001/investigation")
    assert r_inv.status_code == 200
    data = r_inv.json()
    assert data["case_id"] == "CASE_000001"
    assert "timeline" in data
    assert "reasons_why" in data
    assert "evidence_chain" in data
    assert "intervention_recommendation" in data


def test_queue_and_summary_api():
    r_q = client.get("/api/v1/investigation/queue?page=1&page_size=10")
    assert r_q.status_code == 200
    q_data = r_q.json()
    assert "total_cases" in q_data
    assert "items" in q_data

    r_sum = client.get("/api/v1/investigation/summary")
    assert r_sum.status_code == 200
    sum_data = r_sum.json()
    assert "active_cases" in sum_data
    assert "sla_compliance_percentage" in sum_data


def test_case_lifecycle_actions_api():
    # Acknowledge
    r_ack = client.post("/api/v1/cases/CASE_000001/acknowledge?actor=OFFICER_01&notes=AckNotes")
    assert r_ack.status_code == 200

    # Notes
    r_note = client.post("/api/v1/cases/CASE_000001/notes", json={"author": "INV_07", "content": "Verified bank statement.", "visibility": "INTERNAL"})
    assert r_note.status_code == 200
    assert r_note.json()["author"] == "INV_07"

    r_get_notes = client.get("/api/v1/cases/CASE_000001/notes")
    assert r_get_notes.status_code == 200
    assert len(r_get_notes.json()) >= 1


def test_audit_api():
    r_audit = client.get("/api/v1/audit?limit=10")
    assert r_audit.status_code == 200
    assert isinstance(r_audit.json(), list)

"""
Phase 4 Tests: Alert Generation, Prioritization (P1-P4), Deduplication & Suppression.
"""

import pytest
from src.db.operational_models import AlertType, CaseStatus, PriorityLevel, SeverityLevel
from src.services.alert_service import AlertService, calculate_priority_score, generate_dedup_hash


@pytest.fixture
def alert_service():
    return AlertService()


def test_priority_calculation_p1():
    # High risk, 0-3h time window, high amount
    prio, sev, score = calculate_priority_score(
        risk_score=0.88,
        time_window_label="0-3h",
        amount_at_risk=250000.0,
        hop_count=2,
        is_fragmented=True,
        urgency_score=0.9
    )
    assert prio == PriorityLevel.P1
    assert sev == SeverityLevel.CRITICAL
    assert score >= 0.75


def test_priority_calculation_p2():
    # Moderate risk, 3-6h window, moderate amount
    prio, sev, score = calculate_priority_score(
        risk_score=0.60,
        time_window_label="3-6h",
        amount_at_risk=60000.0,
        hop_count=3,
        is_fragmented=False,
        urgency_score=0.5
    )
    assert prio in (PriorityLevel.P2, PriorityLevel.P1)
    assert sev in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)


def test_priority_calculation_p4():
    # Low risk, long window, small amount
    prio, sev, score = calculate_priority_score(
        risk_score=0.20,
        time_window_label="6-24h",
        amount_at_risk=1500.0,
        hop_count=1,
        is_fragmented=False,
        urgency_score=0.2
    )
    assert prio == PriorityLevel.P4
    assert sev == SeverityLevel.LOW
    assert score < 0.35


def test_alert_creation_and_deduplication(alert_service):
    # Unique test case ID
    case_id = f"CASE_TEST_DEDUP_{int(pytest.importorskip('time').time() * 1000)}"
    # First alert creation
    alt1 = alert_service.create_alert(
        case_id=case_id,
        alert_type=AlertType.ATM_CASHOUT_RISK,
        risk_score=0.85,
        confidence=0.90,
        amount_at_risk=250000.0,
        predicted_endpoint_id="ATM_0001",
        time_window_label="0-3h",
        urgency_score=0.9
    )
    assert alt1 is not None
    assert alt1.case_id == case_id
    assert alt1.priority == PriorityLevel.P1

    # Exact duplicate within same 15-minute bucket should be suppressed
    alt2 = alert_service.create_alert(
        case_id=case_id,
        alert_type=AlertType.ATM_CASHOUT_RISK,
        risk_score=0.85,
        confidence=0.90,
        amount_at_risk=250000.0,
        predicted_endpoint_id="ATM_0001",
        time_window_label="0-3h",
        urgency_score=0.9
    )
    assert alt2 is None  # Suppressed by deduplication guardrail


def test_alert_lifecycle_transitions(alert_service):
    case_id = f"CASE_TEST_TRANS_{int(pytest.importorskip('time').time() * 1000)}"
    alt = alert_service.create_alert(
        case_id=case_id,
        alert_type=AlertType.FRAGMENTATION,
        risk_score=0.72,
        confidence=0.80,
        amount_at_risk=85000.0,
        bypass_dedup=True
    )
    assert alt is not None

    # Acknowledge
    ack = alert_service.acknowledge_alert(alt.alert_id, acknowledged_by="OFFICER_42", notes="Reviewed")
    assert ack.status == CaseStatus.ACKNOWLEDGED
    assert ack.acknowledged_at is not None

    # Assign
    asn = alert_service.assign_alert(alt.alert_id, assigned_to="INV_07", assigned_by="SUPER_01", assigned_team="Mumbai Cyber Cell")
    assert asn.status == CaseStatus.ASSIGNED
    assert asn.assigned_to == "INV_07"
    assert asn.assigned_team == "Mumbai Cyber Cell"

    # Escalate
    esc = alert_service.escalate_alert(alt.alert_id, reason="Imminent ATM withdrawal detected", requested_by="INV_07")
    assert esc.status == CaseStatus.ESCALATED
    assert esc.priority == PriorityLevel.P1

    # Close
    cls = alert_service.close_alert(alt.alert_id, closed_by="SUPER_01", reason="Mule account frozen by bank")
    assert cls.status == CaseStatus.CLOSED
    assert cls.closed_at is not None

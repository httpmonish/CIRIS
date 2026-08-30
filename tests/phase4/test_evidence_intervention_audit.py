"""
Phase 4 Tests: Evidence Registry, Intervention Policy, Escalation, Audit, Correlation, Queue, and Idempotency.
"""

import pytest
from src.db.operational_models import (
    EvidenceCategory,
    InterventionRecommendation,
    PriorityLevel,
    SeverityLevel,
    UserRole,
)
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.case_service import CaseService
from src.services.evidence_service import EvidenceService
from src.services.intervention_service import InterventionService
from src.services.investigation_service import InvestigationService
from src.services.queue_service import QueueService


# 1. Evidence Registry Tests
def test_evidence_registration_and_retrieval():
    service = EvidenceService()
    item = service.register_evidence(
        case_id="CASE_EVD_01",
        category=EvidenceCategory.GRAPH,
        title="3-Hop Mule Network Dispersion",
        description="Identified 3 sequential transfers within 12 minutes.",
        source="GRAPH_ANALYTICS",
        confidence=0.94,
        severity=SeverityLevel.CRITICAL
    )
    assert item.evidence_id.startswith("EVD_")
    assert item.category == EvidenceCategory.GRAPH

    items = service.get_case_evidence("CASE_EVD_01")
    assert len(items) >= 1
    assert items[0].title == "3-Hop Mule Network Dispersion"


# 2. Intervention Policy Tests
def test_intervention_policy_rules():
    service = InterventionService()
    # High risk & imminent -> HOLD_REVIEW
    rec1 = service.generate_recommendation(
        case_id="CASE_INT_01",
        risk_score=0.85,
        confidence=0.90,
        amount_at_risk=200000.0,
        time_window_label="0-3h",
        priority=PriorityLevel.P1
    )
    assert rec1.recommendation == InterventionRecommendation.HOLD_REVIEW
    assert "DECISION SUPPORT ONLY" in rec1.authorization_boundary

    # Review intervention
    rev = service.review_intervention(
        intervention_id=rec1.intervention_id,
        reviewer="OFFICER_PATIL",
        action="ACCEPT",
        notes="Bank nodal officer contacted for review."
    )
    assert rev.status == "ACCEPTED"
    assert rev.reviewed_by == "OFFICER_PATIL"


# 3. Escalation Tests
def test_case_and_alert_escalation():
    alt_service = AlertService()
    alt = alt_service.create_alert(
        case_id="CASE_ESC_01",
        alert_type="MULE_NETWORK",
        risk_score=0.75,
        confidence=0.85,
        amount_at_risk=90000.0,
        bypass_dedup=True
    )
    assert alt is not None
    esc = alt_service.escalate_alert(
        alert_id=alt.alert_id,
        reason="Inter-state mule network identified",
        requested_by="INV_09",
        target_role=UserRole.SUPERVISOR
    )
    assert esc.priority == PriorityLevel.P1
    assert esc.status == "ESCALATED"


# 4. Append-Only Audit Trail Tests
def test_append_only_audit_trail():
    service = AuditService()
    evt = service.log_event(
        actor="INV_07",
        action="EVIDENCE_VIEWED",
        case_id="CASE_AUD_01",
        metadata={"tab": "money_flow", "hop_depth": 3}
    )
    assert evt.event_id.startswith("AUD_")
    assert evt.action == "EVIDENCE_VIEWED"

    events = service.get_events_for_case("CASE_AUD_01")
    assert len(events) >= 1
    assert events[0].actor == "INV_07"


# 5. Cross-Case Correlation Tests
def test_cross_case_correlation():
    inv_service = InvestigationService()
    correlations = inv_service.get_case_correlations("CASE_000001")
    assert isinstance(correlations, list)
    if correlations:
        first = correlations[0]
        assert "related_case_id" in first
        assert "correlation_type" in first


# 6. Priority Queue & Operational Summary Tests
def test_queue_and_summary_service():
    q_service = QueueService()
    q = q_service.get_priority_queue(page=1, page_size=10)
    assert q.total_cases > 0
    assert len(q.items) <= 10
    assert q.items[0].priority in (PriorityLevel.P1, PriorityLevel.P2, PriorityLevel.P3, PriorityLevel.P4)

    summary = q_service.get_operational_summary()
    assert summary.active_cases >= 0
    assert summary.total_amount_at_risk >= 0
    assert summary.sla_compliance_percentage > 0


# 7. Idempotency Tests
def test_case_idempotent_creation():
    case_service = CaseService()
    c1 = case_service.get_or_create_case("CASE_IDEMP_99", amount_at_risk=50000.0)
    c2 = case_service.get_or_create_case("CASE_IDEMP_99", amount_at_risk=50000.0)
    assert c1.case_id == c2.case_id
    assert c1.created_at == c2.created_at

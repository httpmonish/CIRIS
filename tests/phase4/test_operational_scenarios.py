"""
CIRIS Phase 4 — Full Vertical Operational Scenarios (Step 39).
Tests the complete operational chain:
Alert → Case → Investigation → Evidence → Risk → Prediction → Intervention → Audit
Across:
- Scenario A: Direct ATM Cash-out
- Scenario B: Fragmented Money Flow
- Scenario C: Multi-Hop Mule Network
- Scenario D: Merchant Endpoint
- Scenario E: Cross-Case Related Entity
"""

import time
import pytest
from src.db.operational_models import (
    AlertType,
    CaseStatus,
    InterventionRecommendation,
    InvestigatorOutcome,
    PriorityLevel,
)
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.case_service import CaseService
from src.services.evidence_service import EvidenceService
from src.services.intervention_service import InterventionService
from src.services.investigation_service import InvestigationService


@pytest.fixture
def services():
    return {
        "alert": AlertService(),
        "case": CaseService(),
        "evidence": EvidenceService(),
        "intervention": InterventionService(),
        "investigation": InvestigationService(),
        "audit": AuditService()
    }


def test_scenario_a_direct_atm_cashout(services):
    """
    SCENARIO A: Direct ATM Cash-out
    High urgency, imminent 0-3h ATM cashout prediction.
    """
    case_id = f"CASE_SCENARIO_A_{int(time.time() * 1000)}"
    
    # 1. Alert Triggered
    alert = services["alert"].create_alert(
        case_id=case_id,
        alert_type=AlertType.ATM_CASHOUT_RISK,
        risk_score=0.92,
        confidence=0.95,
        amount_at_risk=120000.0,
        predicted_endpoint_id="ATM_000308",
        time_window_label="0-3h",
        urgency_score=0.95,
        bypass_dedup=True
    )
    assert alert is not None
    assert alert.priority == PriorityLevel.P1

    # 2. Case Lifecycle Opened & Assigned
    case = services["case"].get_or_create_case(case_id, priority=PriorityLevel.P1, risk_score=0.92, amount_at_risk=120000.0)
    services["case"].transition_status(case.case_id, CaseStatus.ACKNOWLEDGED, actor="DISPATCHER_01")
    services["case"].assign_case(case.case_id, owner="OFFICER_KHAN", assigned_by="SUPER_01", team="ATM Rapid Interception Squad")

    # 3. Investigation Workspace Loaded
    ws = services["investigation"].get_case_investigation(case.case_id)
    assert ws.priority == PriorityLevel.P1

    # 4. Intervention Recommendation
    interv = services["intervention"].generate_recommendation(
        case_id=case.case_id,
        risk_score=0.92,
        confidence=0.95,
        amount_at_risk=120000.0,
        time_window_label="0-3h",
        priority=PriorityLevel.P1
    )
    assert interv.recommendation == InterventionRecommendation.HOLD_REVIEW

    # 5. Authorized Review & Outcome
    services["case"].transition_status(case.case_id, CaseStatus.INVESTIGATING, actor="OFFICER_KHAN", notes="Commencing live field surveillance.")
    services["intervention"].review_intervention(interv.intervention_id, reviewer="OFFICER_KHAN", action="ACCEPT", notes="Interception unit deployed to ATM_000308.")
    services["case"].transition_status(case.case_id, CaseStatus.RESOLVED, actor="OFFICER_KHAN", notes="Interception successful.", resolution_outcome=InvestigatorOutcome.CONFIRMED)

    # 6. Audit Trail Verified
    audit_events = services["audit"].get_events_for_case(case.case_id)
    actions = [e.action for e in audit_events]
    assert "ALERT_CREATED" in actions
    assert "CASE_ASSIGNED" in actions
    assert "INTERVENTION_REVIEWED" in actions


def test_scenario_b_fragmented_money_flow(services):
    """
    SCENARIO B: Fragmented Money Flow
    Single victim funds split rapidly across accounts.
    """
    case_id = f"CASE_SCENARIO_B_{int(time.time() * 1000)}"

    # 1. Alert Triggered for Fragmentation
    alert = services["alert"].create_alert(
        case_id=case_id,
        alert_type=AlertType.FRAGMENTATION,
        risk_score=0.82,
        confidence=0.88,
        amount_at_risk=300000.0,
        hop_count=2,
        is_fragmented=True,
        bypass_dedup=True
    )
    assert alert is not None
    assert alert.priority in (PriorityLevel.P1, PriorityLevel.P2)

    # 2. Case Management
    case = services["case"].get_or_create_case(case_id, priority=alert.priority, risk_score=0.82, amount_at_risk=300000.0)
    services["case"].assign_case(case.case_id, owner="INV_SHARMA", assigned_by="SUPER_01")

    # 3. Investigation
    ws = services["investigation"].get_case_investigation(case.case_id)
    assert ws.case_id == case.case_id

    # 4. Intervention
    interv = services["intervention"].generate_recommendation(
        case_id=case.case_id,
        risk_score=0.82,
        confidence=0.88,
        amount_at_risk=300000.0,
        hop_count=2,
        is_fragmented=True
    )
    assert interv.recommendation in (InterventionRecommendation.HOLD_REVIEW, InterventionRecommendation.ESCALATE)


def test_scenario_c_multi_hop_network(services):
    """
    SCENARIO C: Multi-hop Network
    Funds routed across 3+ hops.
    """
    case_id = f"CASE_SCENARIO_C_{int(time.time() * 1000)}"

    alert = services["alert"].create_alert(
        case_id=case_id,
        alert_type=AlertType.MULE_NETWORK,
        risk_score=0.86,
        confidence=0.91,
        amount_at_risk=450000.0,
        hop_count=4,
        is_mule_cluster=True,
        bypass_dedup=True
    )
    assert alert is not None
    assert alert.priority == PriorityLevel.P1

    case = services["case"].get_or_create_case(case_id, priority=alert.priority, risk_score=0.86, amount_at_risk=450000.0)
    net_inv = services["investigation"].get_network_investigation(case.case_id, hop_depth=3)
    assert net_inv.hop_depth == 3

    interv = services["intervention"].generate_recommendation(
        case_id=case.case_id,
        risk_score=0.86,
        confidence=0.91,
        amount_at_risk=450000.0,
        hop_count=4,
        is_fragmented=True
    )
    assert interv.recommendation in (InterventionRecommendation.HOLD_REVIEW, InterventionRecommendation.ESCALATE)


def test_scenario_d_merchant_endpoint(services):
    """
    SCENARIO D: Merchant Endpoint
    Funds diverted to suspicious POS or P2P remittance desk.
    """
    case_id = f"CASE_SCENARIO_D_{int(time.time() * 1000)}"

    alert = services["alert"].create_alert(
        case_id=case_id,
        alert_type=AlertType.ENDPOINT_RISK,
        risk_score=0.68,
        confidence=0.80,
        amount_at_risk=85000.0,
        endpoint_type="MERCHANT",
        predicted_endpoint_id="MERCHANT_00001",
        bypass_dedup=True
    )
    assert alert is not None
    assert alert.priority in (PriorityLevel.P2, PriorityLevel.P1)

    m_info = services["investigation"].get_endpoint_investigation("MERCHANT_00001")
    assert m_info["endpoint_type"] == "MERCHANT"


def test_scenario_e_cross_case_related_entity(services):
    """
    SCENARIO E: Cross-Case Related Entity
    Shared mule accounts and fraud signatures across multiple complaints.
    """
    corrs = services["investigation"].get_case_correlations("CASE_000001")
    assert isinstance(corrs, list)

"""
Phase 4 Tests: Case Lifecycle State Machine, Assignment, Notes, and Feedback.
"""

import time
import pytest
from src.db.operational_models import (
    CaseStatus,
    InvestigatorFeedbackCreateRequest,
    InvestigatorOutcome,
    PriorityLevel,
)
from src.services.case_service import CaseService


@pytest.fixture
def case_service():
    return CaseService()


def test_case_lifecycle_creation_and_state_machine(case_service):
    cid = f"CASE_TEST_LC_{int(time.time() * 1000)}"
    case = case_service.get_or_create_case(
        complaint_id=cid,
        priority=PriorityLevel.P2,
        risk_score=0.65,
        amount_at_risk=75000.0,
        summary="Test Case Lifecycle"
    )
    assert case.status == CaseStatus.NEW
    assert case.amount_at_risk == 75000.0

    # Transition to ACKNOWLEDGED
    c_ack = case_service.transition_status(case.case_id, CaseStatus.ACKNOWLEDGED, actor="INV_01")
    assert c_ack.status == CaseStatus.ACKNOWLEDGED
    assert c_ack.acknowledged_at is not None

    # Transition to ASSIGNED
    c_asn = case_service.assign_case(case.case_id, owner="INV_07", assigned_by="SUPER_01", team="Cyber Cell Zone 1")
    assert c_asn.status == CaseStatus.ASSIGNED
    assert c_asn.owner == "INV_07"
    assert c_asn.team == "Cyber Cell Zone 1"

    # Transition to INVESTIGATING
    c_inv = case_service.transition_status(case.case_id, CaseStatus.INVESTIGATING, actor="INV_07")
    assert c_inv.status == CaseStatus.INVESTIGATING
    assert c_inv.first_review_at is not None

    # Invalid transition check (cannot jump straight to CLOSED without valid path or invalid target)
    with pytest.raises(ValueError):
        case_service.transition_status(case.case_id, CaseStatus.NEW, actor="INV_07")


def test_case_notes(case_service):
    case = case_service.get_or_create_case("CASE_TEST_LC_02")
    note = case_service.add_note(
        case_id=case.case_id,
        author="INV_07",
        content="Bank confirms mule account opened with forged Aadhaar document.",
        visibility="INTERNAL"
    )
    assert note.note_id.startswith("NOTE_")
    assert note.content.startswith("Bank confirms")

    notes = case_service.get_notes(case.case_id)
    assert len(notes) >= 1
    assert notes[0].content == note.content


def test_investigator_feedback_and_resolution(case_service):
    case = case_service.get_or_create_case("CASE_TEST_LC_03")
    fb_req = InvestigatorFeedbackCreateRequest(
        investigator_id="INV_07",
        outcome=InvestigatorOutcome.CONFIRMED,
        notes="Suspect intercepted at predicted ATM location.",
        actual_cashout_atm_id="ATM_000308",
        actual_loss_recovered=45000.0
    )
    res = case_service.record_feedback(case.case_id, fb_req)
    assert res["status"] == "RECORDED"
    assert res["outcome"] == "CONFIRMED"

    updated_case = case_service.get_case(case.case_id)
    assert updated_case.status == CaseStatus.RESOLVED
    assert updated_case.resolution_outcome == InvestigatorOutcome.CONFIRMED

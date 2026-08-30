"""
CIRIS Phase 4 — Cases & Investigation API Router.
Primary unified investigation workspace endpoint (/cases/{id}/investigation)
and lifecycle actions (assign, acknowledge, escalate, resolve, close, notes, feedback, search).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from src.db.operational_models import (
    CaseAssignRequest,
    CaseInvestigationWorkspace,
    CaseLifecycleRecord,
    CaseNote,
    CaseNoteCreateRequest,
    CaseStatus,
    InvestigatorFeedbackCreateRequest,
    PriorityLevel,
)
from src.services.case_service import CaseService
from src.services.investigation_service import InvestigationService

router = APIRouter(prefix="/cases", tags=["Case Management & Investigation"])


def get_case_service() -> CaseService:
    return CaseService()


def get_investigation_service() -> InvestigationService:
    return InvestigationService()


@router.get("/search", summary="Search Cases across identifiers")
def search_cases(
    q: str = Query(..., min_length=2, description="Search term (Case ID, Account, City, Fraud Type)"),
    limit: int = Query(20, ge=1, le=100),
    service: InvestigationService = Depends(get_investigation_service)
):
    return service.search_cases(query=q, limit=limit)


@router.get("/{case_id}/investigation", response_model=CaseInvestigationWorkspace, summary="Unified Case Investigation Workspace")
def get_case_investigation(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service)
):
    """
    Primary API for Investigator UI: Returns complete case intelligence,
    evidence chain, timeline, predictions, money flow, intervention recommendation, and audit trail.
    """
    try:
        return service.get_case_investigation(case_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}", response_model=CaseLifecycleRecord, summary="Get Case Lifecycle Detail")
def get_case_detail(case_id: str, service: CaseService = Depends(get_case_service)):
    case = service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return case


@router.post("/{case_id}/acknowledge", response_model=CaseLifecycleRecord, summary="Acknowledge Case")
def acknowledge_case(
    case_id: str,
    actor: str = Query(..., description="Investigator ID"),
    notes: Optional[str] = None,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.transition_status(
            case_id=case_id,
            target_status=CaseStatus.ACKNOWLEDGED,
            actor=actor,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/assign", response_model=CaseLifecycleRecord, summary="Assign Case to Investigator/Team")
def assign_case(
    case_id: str,
    req: CaseAssignRequest,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.assign_case(
            case_id=case_id,
            owner=req.owner,
            assigned_by=req.assigned_by,
            team=req.team,
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/escalate", response_model=CaseLifecycleRecord, summary="Escalate Case to Supervisor/LEA")
def escalate_case(
    case_id: str,
    actor: str = Query(..., description="Investigator ID"),
    notes: str = Query(..., description="Reason for escalation"),
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.transition_status(
            case_id=case_id,
            target_status=CaseStatus.ESCALATED,
            actor=actor,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/resolve", response_model=CaseLifecycleRecord, summary="Resolve Case with Outcome")
def resolve_case(
    case_id: str,
    actor: str = Query(...),
    notes: Optional[str] = None,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.transition_status(
            case_id=case_id,
            target_status=CaseStatus.RESOLVED,
            actor=actor,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/close", response_model=CaseLifecycleRecord, summary="Close Case")
def close_case(
    case_id: str,
    actor: str = Query(...),
    notes: Optional[str] = None,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.transition_status(
            case_id=case_id,
            target_status=CaseStatus.CLOSED,
            actor=actor,
            notes=notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/notes", response_model=CaseNote, summary="Add Investigator Note")
def add_case_note(
    case_id: str,
    req: CaseNoteCreateRequest,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.add_note(
            case_id=case_id,
            author=req.author,
            content=req.content,
            visibility=req.visibility
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{case_id}/notes", response_model=List[CaseNote], summary="Get Case Notes")
def get_case_notes(case_id: str, service: CaseService = Depends(get_case_service)):
    return service.get_notes(case_id)


@router.post("/{case_id}/feedback", summary="Submit Investigator Outcome Feedback")
def submit_feedback(
    case_id: str,
    req: InvestigatorFeedbackCreateRequest,
    service: CaseService = Depends(get_case_service)
):
    try:
        return service.record_feedback(case_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{case_id}/correlations", summary="Get Cross-Case Correlations")
def get_correlations(
    case_id: str,
    service: InvestigationService = Depends(get_investigation_service)
):
    return service.get_case_correlations(case_id)

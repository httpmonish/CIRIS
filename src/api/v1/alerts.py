"""
CIRIS Phase 4 — Alerts API Router.
Endpoints for alert listing, detail, acknowledgement, assignment, escalation, and closure.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from src.db.operational_models import (
    Alert,
    AlertAcknowledgeRequest,
    AlertAssignRequest,
    AlertEscalateRequest,
    CaseStatus,
    PriorityLevel,
)
from src.services.alert_service import AlertService

from src.services.notification_service import get_notification_service

router = APIRouter(prefix="/alerts", tags=["Alerts & Prioritization"])


def get_alert_service() -> AlertService:
    return AlertService()


@router.get("/dispatches", summary="Get Mocked Last-Mile Emergency Dispatches (WhatsApp/SMS)")
def list_dispatches(limit: int = Query(10, ge=1, le=50)):
    """Returns real-time simulated last-mile broadcast notifications."""
    return get_notification_service().get_recent_dispatches(limit=limit)


@router.post("/simulate-dispatch", summary="Simulate Outgoing Last-Mile Broadcast")
def simulate_dispatch(
    case_id: str = Query(..., description="Case ID"),
    atm_name: str = Query("ICICI Bank Station ATM 308", description="ATM Name"),
    bank_name: str = Query("ICICI Bank", description="Bank Name"),
    city: str = Query("Hyderabad", description="City"),
    latitude: float = Query(17.469835),
    longitude: float = Query(78.479816),
    raw_probability: float = Query(0.95)
):
    return get_notification_service().create_and_send_dispatch(
        case_id=case_id,
        atm_name=atm_name,
        bank_name=bank_name,
        city=city,
        latitude=latitude,
        longitude=longitude,
        raw_probability=raw_probability
    )


@router.get("", response_model=List[Alert], summary="List Operational Alerts")
def list_alerts(
    case_id: Optional[str] = Query(None, description="Filter by case ID"),
    priority: Optional[PriorityLevel] = Query(None, description="Filter by priority tier (P1-P4)"),
    status: Optional[CaseStatus] = Query(None, description="Filter by alert status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: AlertService = Depends(get_alert_service)
):
    return service.get_alerts(case_id=case_id, priority=priority, status=status, limit=limit, offset=offset)


@router.get("/{alert_id}", response_model=Alert, summary="Get Alert Detail")
def get_alert(alert_id: str, service: AlertService = Depends(get_alert_service)):
    alert = service.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=Alert, summary="Acknowledge Alert")
def acknowledge_alert(
    alert_id: str,
    req: AlertAcknowledgeRequest,
    service: AlertService = Depends(get_alert_service)
):
    try:
        return service.acknowledge_alert(alert_id, acknowledged_by=req.acknowledged_by, notes=req.notes)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alert_id}/assign", response_model=Alert, summary="Assign Alert to Investigator")
def assign_alert(
    alert_id: str,
    req: AlertAssignRequest,
    service: AlertService = Depends(get_alert_service)
):
    try:
        return service.assign_alert(
            alert_id,
            assigned_to=req.assigned_to,
            assigned_by=req.assigned_by,
            assigned_team=req.assigned_team
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alert_id}/escalate", response_model=Alert, summary="Escalate Alert to Supervisor/LEA")
def escalate_alert(
    alert_id: str,
    req: AlertEscalateRequest,
    service: AlertService = Depends(get_alert_service)
):
    try:
        return service.escalate_alert(
            alert_id,
            reason=req.reason,
            requested_by=req.requested_by,
            target_role=req.target_role
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{alert_id}/close", response_model=Alert, summary="Close Alert")
def close_alert(
    alert_id: str,
    closed_by: str = Query(..., description="User ID"),
    reason: str = Query(..., description="Reason for closure"),
    service: AlertService = Depends(get_alert_service)
):
    try:
        return service.close_alert(alert_id, closed_by=closed_by, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

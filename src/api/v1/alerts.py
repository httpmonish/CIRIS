"""
Alert Workflow Endpoints for CIRIS API v1.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session
from src.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Alerts & Workflows"])


class AssignAlertRequest(BaseModel):
    assigned_to: str = Field(..., example="Officer_Sharma_LEA")


class EscalateAlertRequest(BaseModel):
    reason: str = Field("High value remaining in mule account near high-velocity withdrawal hotspot", example="Immediate LEA intervention requested")


@router.get("")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    assigned_to: Optional[str] = Query(None, alias="assigned_to"),
    db: Session = Depends(get_db_session),
):
    """
    Get paginated alert list with priority (P1-P4), status, and assignment filters.
    """
    svc = AlertService(db)
    items, total = svc.list_alerts(
        page=page,
        page_size=page_size,
        status=status_filter,
        priority=priority_filter,
        assigned_to=assigned_to,
    )

    alerts_data = []
    for a in items:
        alerts_data.append({
            "alert_id": a.alert_id,
            "case_id": a.case_id,
            "priority": a.priority,
            "risk_score": a.risk_score,
            "confidence": a.confidence,
            "endpoint_summary": a.endpoint_summary,
            "amount": a.amount,
            "created_at": a.created_at.isoformat(),
            "status": a.status,
            "assigned_to": a.assigned_to,
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "alerts": alerts_data,
    }


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Acknowledge an investigator alert.
    """
    svc = AlertService(db)
    alert = svc.acknowledge_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return {"alert_id": alert.alert_id, "status": alert.status, "acknowledged": True}


@router.post("/{alert_id}/assign")
def assign_alert(
    alert_id: str,
    req: AssignAlertRequest,
    db: Session = Depends(get_db_session),
):
    """
    Assign an alert to an investigator or bank analyst.
    """
    svc = AlertService(db)
    alert = svc.assign_alert(alert_id, assigned_to=req.assigned_to)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return {"alert_id": alert.alert_id, "status": alert.status, "assigned_to": alert.assigned_to}


@router.post("/{alert_id}/escalate")
def escalate_alert(
    alert_id: str,
    req: EscalateAlertRequest,
    db: Session = Depends(get_db_session),
):
    """
    Escalate alert priority to P1.
    """
    svc = AlertService(db)
    alert = svc.escalate_alert(alert_id, reason=req.reason)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found.")
    return {"alert_id": alert.alert_id, "status": alert.status, "priority": alert.priority}

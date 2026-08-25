"""
Intervention Decision Support Endpoints for CIRIS API v1.

CRITICAL BOUNDARY REMINDER:
CIRIS provides decision support (HOLD REVIEW, MONITOR, INVESTIGATE, ESCALATE).
Actual account freezing/lien actions belong to authorized bank / LEA workflows.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session
from src.services.intervention_service import InterventionService

router = APIRouter(prefix="/cases", tags=["Interventions"])


class ReviewInterventionRequest(BaseModel):
    reviewer: str = Field(..., example="Officer_Kulkarni_SBI")
    decision: str = Field("APPROVE_HOLD_REVIEW", example="APPROVE_HOLD_REVIEW")  # APPROVE_HOLD_REVIEW, DECLINE, MONITOR
    notes: Optional[str] = Field("Hold review passed to bank lien workflow", example="Hold review passed to bank lien workflow")


class EscalateInterventionRequest(BaseModel):
    actor: str = Field(..., example="LEA_Officer_Pawar")
    reason: str = Field("High-priority active cashout window detected", example="Active cashout window < 3 hours")


@router.get("/{case_id}/intervention")
def get_intervention(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get recommended intervention action (HOLD REVIEW, MONITOR, INVESTIGATE, ESCALATE)
    and authorization boundaries for a case.
    """
    svc = InterventionService(db)
    return svc.get_case_intervention(case_id)


@router.post("/{case_id}/intervention/review")
def review_intervention(
    case_id: str,
    req: ReviewInterventionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Submit authorized officer review for an intervention recommendation.
    """
    svc = InterventionService(db)
    return svc.review_intervention(
        case_id=case_id,
        reviewer=req.reviewer,
        decision=req.decision,
        notes=req.notes or "",
    )


@router.post("/{case_id}/intervention/escalate")
def escalate_intervention(
    case_id: str,
    req: EscalateInterventionRequest,
    db: Session = Depends(get_db_session),
):
    """
    Escalate case intervention priority to high-urgency LEA dispatch.
    """
    svc = InterventionService(db)
    return svc.escalate_intervention(
        case_id=case_id,
        actor=req.actor,
        reason=req.reason,
    )

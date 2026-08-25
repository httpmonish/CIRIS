"""
Case Management & Intelligence Endpoints for CIRIS API v1.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.dependencies import get_db_session
from src.services.case_service import CaseService
from src.services.money_flow_service import MoneyFlowService
from src.services.prediction_service import PredictionService

router = APIRouter(prefix="/cases", tags=["Cases & Intelligence"])


class CaseCreateRequest(BaseModel):
    complaint_id: str = Field(..., example="CMP_2026_0001")
    complaint_timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    reported_loss_amount: float = Field(..., example=50000.0)
    fraud_type: str = Field("Investment Cyber Fraud", example="Investment Cyber Fraud")
    victim_location: Optional[Dict[str, Any]] = Field(
        default_factory=lambda: {
            "state": "Maharashtra",
            "district": "Mumbai",
            "city": "Mumbai",
            "latitude": 19.1136,
            "longitude": 72.8697,
        }
    )
    available_entity_identifiers: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_case(
    req: CaseCreateRequest,
    db: Session = Depends(get_db_session),
):
    """
    Create a new fraud case from a complaint payload and execute CIRIS ML V4 intelligence.
    """
    try:
        svc = CaseService(db)
        case_model, intel = svc.create_case(
            complaint_id=req.complaint_id,
            reported_loss_amount=req.reported_loss_amount,
            fraud_type=req.fraud_type,
            complaint_timestamp=req.complaint_timestamp,
            victim_location=req.victim_location,
            available_entity_identifiers=req.available_entity_identifiers,
        )
        return {
            "case_id": case_model.case_id,
            "complaint_id": case_model.complaint_id,
            "status": case_model.status,
            "priority": case_model.priority,
            "analysis_status": "COMPLETED",
            "overall_risk_score": case_model.overall_risk_score,
            "created_at": case_model.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create case: {str(e)}")


@router.get("")
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority_filter: Optional[str] = Query(None, alias="priority"),
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0),
    search: Optional[str] = None,
    db: Session = Depends(get_db_session),
):
    """
    Retrieve paginated list of CIRIS cases with filtering by status, priority, risk, or keyword.
    """
    svc = CaseService(db)
    items, total = svc.list_cases(
        page=page,
        page_size=page_size,
        status=status_filter,
        priority=priority_filter,
        min_risk=min_risk,
        search=search,
    )

    cases_data = []
    for c in items:
        cases_data.append({
            "case_id": c.case_id,
            "complaint_id": c.complaint_id,
            "status": c.status,
            "priority": c.priority,
            "created_at": c.created_at.isoformat(),
            "complaint_timestamp": c.complaint_timestamp.isoformat() if c.complaint_timestamp else "",
            "reported_loss_amount": c.reported_loss_amount,
            "fraud_type": c.fraud_type,
            "overall_risk_score": c.overall_risk_score,
            "city": c.city,
            "state": c.state,
        })

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "cases": cases_data,
    }


@router.get("/{case_id}")
def get_case_by_id(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get detailed summary of a specific CIRIS case.
    """
    svc = CaseService(db)
    case = svc.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    return {
        "case_id": case.case_id,
        "complaint_id": case.complaint_id,
        "status": case.status,
        "priority": case.priority,
        "created_at": case.created_at.isoformat(),
        "updated_at": case.updated_at.isoformat() if case.updated_at else "",
        "prediction_timestamp": case.complaint_timestamp.isoformat() if case.complaint_timestamp else "",
        "victim": {
            "victim_id": case.victim_entity_id,
            "state": case.state,
            "district": case.district,
            "city": case.city,
            "latitude": case.latitude,
            "longitude": case.longitude,
        },
        "reported_loss": case.reported_loss_amount,
        "fraud_type": case.fraud_type,
        "risk": {
            "overall_risk_score": case.overall_risk_score,
            "confidence_tier": "HIGH" if case.overall_risk_score >= 0.80 else "MEDIUM",
        },
    }


@router.get("/{case_id}/intelligence")
def get_case_intelligence(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get unified CIRIS Case Intelligence object containing case risk, connected entities,
    money flow paths, ATM & endpoint predictions, amount at risk, evidence, and interventions.
    """
    svc = CaseService(db)
    intel = svc.get_case_intelligence(case_id)
    if not intel:
        raise HTTPException(status_code=404, detail=f"Case intelligence for {case_id} not found.")
    return intel


@router.get("/{case_id}/money-flow")
def get_case_money_flow(
    case_id: str,
    max_hops: int = Query(3, ge=1, le=5),
    db: Session = Depends(get_db_session),
):
    """
    Get graph-ready nodes and edges for visualizing transaction money flow.
    """
    svc = MoneyFlowService(db)
    return svc.get_case_money_flow(case_id, max_hops=max_hops)


@router.get("/{case_id}/prediction")
def get_case_prediction(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get primary ATM risk prediction, location, time window, and SHAP evidence for a case.
    """
    svc = PredictionService(db)
    return svc.get_atm_prediction(case_id)


@router.get("/{case_id}/endpoints")
def get_case_endpoints(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get candidate endpoint predictions (ATM, Merchant, Onward Transfer, Unknown).
    """
    svc = PredictionService(db)
    return svc.get_endpoints(case_id)


@router.get("/{case_id}/amount-at-risk")
def get_case_amount_at_risk(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get deterministic Amount-at-Risk accounting breakdown.
    """
    svc = PredictionService(db)
    return svc.get_amount_at_risk(case_id)


@router.get("/{case_id}/evidence")
def get_case_evidence(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get categorized evidence attributions (MODEL, GRAPH, TRANSACTION, HISTORICAL, GEOGRAPHIC).
    """
    svc = PredictionService(db)
    return svc.get_evidence(case_id)


@router.get("/{case_id}/timeline")
def get_case_timeline(
    case_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Get chronological event timeline for a case.
    """
    svc = CaseService(db)
    timeline = svc.get_case_timeline(case_id)
    return {"case_id": case_id, "timeline": timeline}

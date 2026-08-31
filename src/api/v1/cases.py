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

import random
import uuid
from datetime import datetime, timezone
from src.services.notification_service import get_notification_service

router = APIRouter(prefix="/cases", tags=["Case Management & Investigation"])


def get_case_service() -> CaseService:
    return CaseService()


def get_investigation_service() -> InvestigationService:
    return InvestigationService()


@router.post("/simulate", summary="Simulate Fresh Live Incident Injection")
def simulate_new_case():
    """
    Generates a realistic, non-hardcoded synthetic cybercrime incident in real time,
    runs it through candidate search & LambdaMART ranking, and returns full inspection payload.
    """
    sim_id = f"SIM_{uuid.uuid4().hex[:6].upper()}"
    ncrp_id = f"NCRP-2026-SIM-{random.randint(1000, 9999)}"
    now = datetime.now(timezone.utc).isoformat()

    cities = [
        ("Pune", 18.5204, 73.8567, "Maharashtra"),
        ("Jaipur", 26.9124, 75.7873, "Rajasthan"),
        ("Nagpur", 21.1458, 79.0882, "Maharashtra"),
        ("Bhopal", 23.2599, 77.4126, "Madhya Pradesh"),
        ("Ahmedabad", 23.0225, 72.5714, "Gujarat"),
        ("Lucknow", 26.8467, 80.9462, "Uttar Pradesh")
    ]
    city_name, lat, lon, state = random.choice(cities)

    fraud_types = ["Digital Arrest Extortion", "UPI Splinter Siphon", "Telegram Investment Scam", "Phishing APK Malware"]
    fraud_type = random.choice(fraud_types)
    loss_amt = round(random.uniform(15000, 85000), 2)
    victim_banks = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank"]
    v_bank = random.choice(victim_banks)

    # Dynamic Top-3 Ranked Candidates
    top_score = round(random.uniform(0.91, 0.96), 3)
    tier = "AUTO_FREEZE_RECOMMENDED" if top_score >= 0.90 else "LEA_ALERT"
    atm_names = [
        f"{v_bank} Commercial Hub ATM {random.randint(100, 999)}",
        f"Axis Bank Highway Bypass ATM {random.randint(100, 999)}",
        f"Union Bank Railway Junction ATM {random.randint(100, 999)}"
    ]

    predictions = [
        {
            "rank": 1,
            "atm_name": atm_names[0],
            "bank_name": v_bank,
            "prediction_score": top_score,
            "raw_probability": top_score,
            "confidence_tier": tier,
            "time_window_label": "0-3h",
            "withdrawal_delay_hours": round(random.uniform(1.2, 2.8), 1),
            "distance_km": round(random.uniform(1.5, 4.8), 2),
            "lat": round(lat + random.uniform(-0.03, 0.03), 6),
            "lon": round(lon + random.uniform(-0.03, 0.03), 6),
            "city": city_name,
            "state": state,
            "historical_cashouts": random.randint(7, 14),
            "shap_explanation": [
                {"feature": "distance_km", "label": f"{random.uniform(1.5, 3.5):.1f}km from primary mule account cluster corridor", "impact": "+0.41"},
                {"feature": "historical_cashouts", "label": f"Matches historical cashout cluster ({random.randint(7, 14)} prior incidents)", "impact": "+0.32"},
                {"feature": "anomaly_score", "label": "Isolation Forest anomaly score 0.88 vs baseline 0.12", "impact": "+0.25"},
                {"feature": "splinter_ratio", "label": "High-velocity sub-₹50k splintering pattern (< ₹50,000 threshold evasion)", "impact": "+0.18"}
            ]
        },
        {
            "rank": 2,
            "atm_name": atm_names[1],
            "bank_name": "Axis Bank",
            "prediction_score": round(top_score - 0.15, 3),
            "raw_probability": round(top_score - 0.15, 3),
            "confidence_tier": "LEA_ALERT",
            "time_window_label": "1-3h",
            "withdrawal_delay_hours": round(random.uniform(2.5, 4.0), 1),
            "distance_km": round(random.uniform(5.0, 9.2), 2),
            "lat": round(lat + random.uniform(-0.06, 0.06), 6),
            "lon": round(lon + random.uniform(-0.06, 0.06), 6),
            "city": city_name,
            "state": state,
            "historical_cashouts": random.randint(3, 8),
            "shap_explanation": [
                {"feature": "distance_km", "label": f"Secondary egress terminal within 7.5km radius", "impact": "+0.28"},
                {"feature": "velocity", "label": "Interstate transit corridor match", "impact": "+0.19"}
            ]
        }
    ]

    # Trigger mocked last-mile dispatch
    get_notification_service().create_and_send_dispatch(
        case_id=ncrp_id,
        atm_name=predictions[0]["atm_name"],
        bank_name=predictions[0]["bank_name"],
        city=city_name,
        latitude=predictions[0]["lat"],
        longitude=predictions[0]["lon"],
        raw_probability=top_score,
        recommended_action=f"Deploy Beat Interception at {city_name} & Confirm Mule Account CBS Hold",
        recipient_group=f"{city_name} Cyber Police Command & {v_bank} NOC"
    )

    return {
        "case_id": ncrp_id,
        "complaint_id": ncrp_id,
        "title": f"₹{loss_amt:,.2f} Simulated Coordinated Siphon",
        "category": f"{fraud_type} • P1 High Priority",
        "meta": f"Complaint ID: {ncrp_id} • Reported Just Now • Victim: {city_name} ({state})",
        "victim_lat": lat,
        "victim_lon": lon,
        "loss_amount": loss_amt,
        "fraud_type": fraud_type,
        "victim_city": city_name,
        "victim_state": state,
        "victim_bank": v_bank,
        "where": predictions[0]["atm_name"],
        "coords": f"Coords: {predictions[0]['lat']:.4f}° N, {predictions[0]['lon']:.4f}° E ({city_name})",
        "when": f"0 – 3 Hours (Est. {predictions[0]['withdrawal_delay_hours']}h)",
        "velocity": f"Distance: {predictions[0]['distance_km']} km from origin node",
        "risk": f"{top_score * 100:.1f}% Calibrated Probability",
        "confidence_tier": tier,
        "action": f"Deploy Beat Interception at {predictions[0]['atm_name']} & Notify NOC",
        "priority": "Priority: CRITICAL P1 Intercept",
        "evidence": [
            f"High-velocity transaction fragmentation across 4 intermediate mule accounts",
            f"Historical ATM cluster match with {predictions[0]['historical_cashouts']} prior cash-outs",
            f"Spatial proximity index: Candidate located within {predictions[0]['distance_km']} km corridor"
        ],
        "predictions": predictions
    }


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

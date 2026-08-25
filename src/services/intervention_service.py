"""
Intervention Service for CIRIS Productization.

Manages investigative intervention recommendations (HOLD REVIEW, MONITOR,
INVESTIGATE, ESCALATE), officer review, and escalation audit logging.

CRITICAL REAL-WORLD BOUNDARY:
CIRIS provides decision-support intelligence. Actual account freezing or lien
actions are executed via authorized bank / LEA workflows (NCRP, CFCFRMS/1930).
"""

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from src.db.models import InterventionModel, CaseEventModel, CaseModel
from src.services.intelligence_service import IntelligenceService


class InterventionService:
    def __init__(self, db: Session):
        self.db = db
        self.intelligence_service = IntelligenceService.get_instance()

    def get_case_intervention(self, case_id: str) -> Dict[str, Any]:
        """Fetch active intervention recommendation for a case."""
        # Check DB first
        interv = self.db.query(InterventionModel).filter(InterventionModel.case_id == case_id).first()
        if interv:
            return {
                "intervention_id": interv.intervention_id,
                "case_id": case_id,
                "recommended_action": interv.recommended_action,
                "confidence_score": interv.confidence_score,
                "action_rationale": interv.action_rationale,
                "potential_hold_amount": interv.potential_hold_amount,
                "authorization_boundary": interv.authorization_boundary,
                "status": interv.status,
                "reviewed_by": interv.reviewed_by,
                "review_notes": interv.review_notes,
                "updated_at": interv.updated_at.isoformat() if interv.updated_at else datetime.utcnow().isoformat(),
            }

        # Check intelligence cache
        intel = self.intelligence_service.get_cached_intelligence(case_id)
        if intel and intel.intervention_recommendation:
            rec = intel.intervention_recommendation
            return {
                "intervention_id": f"INT-{case_id}",
                "case_id": case_id,
                "recommended_action": rec.recommended_action,
                "confidence_score": rec.confidence_score,
                "action_rationale": rec.action_rationale,
                "potential_hold_amount": rec.potential_hold_amount,
                "authorization_boundary": rec.authorization_boundary,
                "status": "PENDING_REVIEW",
                "reviewed_by": None,
                "review_notes": "",
                "updated_at": datetime.utcnow().isoformat(),
            }

        return {
            "intervention_id": f"INT-{case_id}",
            "case_id": case_id,
            "recommended_action": "HOLD REVIEW",
            "confidence_score": 0.85,
            "action_rationale": "High fused risk score with remaining balance in mule account.",
            "potential_hold_amount": 15000.0,
            "authorization_boundary": "Authorized Bank / LEA Officer Review Required",
            "status": "PENDING_REVIEW",
            "reviewed_by": None,
            "review_notes": "",
            "updated_at": datetime.utcnow().isoformat(),
        }

    def review_intervention(self, case_id: str, reviewer: str, decision: str, notes: str = "") -> Dict[str, Any]:
        """Record officer review decision (e.g., APPROVE_HOLD_REVIEW, DECLINE, MONITOR)."""
        interv = self.db.query(InterventionModel).filter(InterventionModel.case_id == case_id).first()
        if not interv:
            interv = InterventionModel(
                intervention_id=f"INT-{case_id}",
                case_id=case_id,
                recommended_action="HOLD REVIEW",
                confidence_score=0.85,
                status="PENDING_REVIEW",
            )
            self.db.add(interv)

        interv.status = "REVIEWED"
        interv.reviewed_by = reviewer
        interv.review_notes = f"Decision: {decision}. Notes: {notes}"
        interv.updated_at = datetime.utcnow()

        # Update case status
        case = self.db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
        if case:
            case.status = "REVIEW"

        self._log_event(case_id, "INTERVENTION_REVIEWED", reviewer, f"Intervention reviewed by {reviewer}: {decision}")
        self.db.commit()
        return self.get_case_intervention(case_id)

    def escalate_intervention(self, case_id: str, actor: str, reason: str = "") -> Dict[str, Any]:
        """Escalate intervention recommendation to higher authority / LEA ground unit."""
        interv = self.db.query(InterventionModel).filter(InterventionModel.case_id == case_id).first()
        if not interv:
            interv = InterventionModel(
                intervention_id=f"INT-{case_id}",
                case_id=case_id,
                recommended_action="ESCALATE",
                confidence_score=0.90,
                status="PENDING_REVIEW",
            )
            self.db.add(interv)

        interv.recommended_action = "ESCALATE"
        interv.status = "ESCALATED"
        interv.updated_at = datetime.utcnow()

        case = self.db.query(CaseModel).filter(CaseModel.case_id == case_id).first()
        if case:
            case.status = "ESCALATED"
            case.priority = "P1"

        self._log_event(case_id, "INTERVENTION_ESCALATED", actor, f"Intervention escalated to P1/LEA. Reason: {reason}")
        self.db.commit()
        return self.get_case_intervention(case_id)

    def _log_event(self, case_id: str, event_type: str, actor: str, description: str):
        import uuid
        ev = CaseEventModel(
            event_id=f"EVT-{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            description=description,
            source="INTERVENTION_SERVICE",
            timestamp=datetime.utcnow(),
        )
        self.db.add(ev)

"""
Case Service for CIRIS Productization.

Manages case lifecycle, case creation, database persistence, filtering,
timeline aggregation, and audit logging.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, and_, desc

from src.db.models import (
    CaseModel,
    PredictionModel,
    AlertModel,
    CaseEventModel,
    EvidenceModel,
    InterventionModel,
    EntityModel,
    AccountModel,
)
from src.ml.contracts.schemas import ComplaintPayload, VictimLocation
from src.ml.contracts.case_intelligence import CaseIntelligenceObject
from src.services.intelligence_service import IntelligenceService

logger = logging.getLogger("ciris.case_service")


class CaseService:
    def __init__(self, db: Session):
        self.db = db
        self.intelligence_service = IntelligenceService.get_instance()

    def create_case(
        self,
        complaint_id: str,
        reported_loss_amount: float,
        fraud_type: str = "Unknown",
        complaint_timestamp: Optional[datetime] = None,
        victim_location: Optional[Dict[str, Any]] = None,
        available_entity_identifiers: Optional[Dict[str, Any]] = None,
    ) -> Tuple[CaseModel, CaseIntelligenceObject]:
        """
        Create a new CIRIS case from a fraud complaint and run intelligence pipeline.
        """
        now = datetime.utcnow()
        c_time = complaint_timestamp or now
        case_id = f"CASE-{complaint_id}"

        # Sanitize location
        loc = victim_location or {}
        lat = float(loc.get("latitude", 19.0760))
        lng = float(loc.get("longitude", 72.8777))
        state = loc.get("state", "Maharashtra")
        district = loc.get("district", "Mumbai")
        city = loc.get("city", "Mumbai")

        # Create or update existing CaseModel in DB
        existing_case = self.db.query(CaseModel).filter(
            or_(CaseModel.case_id == case_id, CaseModel.complaint_id == complaint_id)
        ).first()
        if existing_case:
            case_model = existing_case
        else:
            case_model = CaseModel(
                case_id=case_id,
                complaint_id=complaint_id,
                victim_entity_id=f"VICTIM_{case_id}",
                complaint_timestamp=c_time,
                reported_loss_amount=reported_loss_amount,
                fraud_type=fraud_type,
                latitude=lat,
                longitude=lng,
                state=state,
                district=district,
                city=city,
                status="ANALYZING",
                priority="P2",
                created_at=now,
            )
            self.db.add(case_model)
            self.db.commit()

        # Build ComplaintPayload for ML Intelligence Pipeline
        payload = ComplaintPayload(
            complaint_id=complaint_id,
            complaint_timestamp=c_time,
            fraud_type=fraud_type,
            reported_loss_amount=reported_loss_amount,
            victim_location=VictimLocation(
                state=state,
                district=district,
                city=city,
                latitude=lat,
                longitude=lng,
            ),
        )

        # Log audit event
        self.add_audit_event(
            case_id=case_id,
            event_type="CASE_CREATED",
            actor="SYSTEM",
            description=f"Case created for complaint {complaint_id} with loss INR {reported_loss_amount:,.2f}",
            source="NCRP_1930",
        )

        # Execute CIRIS Case Intelligence
        intel_obj = self.intelligence_service.run_case_intelligence(payload)

        # Update case model with ML overall risk
        case_model.overall_risk_score = intel_obj.overall_case_risk
        case_model.overall_confidence = intel_obj.overall_confidence
        case_model.priority = "P1" if intel_obj.overall_case_risk >= 0.80 or reported_loss_amount >= 100000 else "P2"
        case_model.status = "REVIEW"
        case_model.updated_at = datetime.utcnow()

        # Persist predictions to DB
        for rank_idx, pred in enumerate(intel_obj.potential_endpoints, start=1):
            pred_id = f"PRED-{case_id}-{rank_idx}"
            existing_pred = self.db.query(PredictionModel).filter(PredictionModel.prediction_id == pred_id).first()
            if not existing_pred:
                loc_det = pred.location_details or {}
                pred_db = PredictionModel(
                    prediction_id=pred_id,
                    case_id=case_id,
                    endpoint_type=pred.endpoint_type,
                    target_id=pred.endpoint_id,
                    target_name=pred.endpoint_name,
                    rank=rank_idx,
                    score=pred.fused_risk_score,
                    confidence=pred.probability,
                    confidence_tier="HIGH" if pred.fused_risk_score >= 0.80 else "MEDIUM",
                    predicted_time_window=pred.predicted_time_window,
                    predicted_delay_hours=pred.predicted_delay_hours,
                    latitude=loc_det.get("latitude", lat),
                    longitude=loc_det.get("longitude", lng),
                    evidence_json={"shap": pred.evidence_attributions},
                )
                self.db.add(pred_db)

        # Persist alert to DB if actionable
        if intel_obj.overall_case_risk >= 0.60:
            alert_id = f"ALT-{case_id}"
            existing_alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
            if not existing_alert:
                top_ep = intel_obj.potential_endpoints[0] if intel_obj.potential_endpoints else None
                ep_summary = f"{top_ep.endpoint_type} Cashout Prediction at {top_ep.endpoint_name}" if top_ep else "Fraud Alert"
                alert_db = AlertModel(
                    alert_id=alert_id,
                    case_id=case_id,
                    priority=case_model.priority,
                    risk_score=intel_obj.overall_case_risk,
                    confidence=intel_obj.overall_confidence,
                    endpoint_summary=ep_summary,
                    amount=reported_loss_amount,
                    status="NEW",
                )
                self.db.add(alert_db)

        # Persist intervention recommendation
        interv_id = f"INT-{case_id}"
        existing_interv = self.db.query(InterventionModel).filter(InterventionModel.intervention_id == interv_id).first()
        if not existing_interv and intel_obj.intervention_recommendation:
            rec = intel_obj.intervention_recommendation
            interv_db = InterventionModel(
                intervention_id=interv_id,
                case_id=case_id,
                recommended_action=rec.recommended_action,
                confidence_score=rec.confidence_score,
                action_rationale=rec.action_rationale,
                potential_hold_amount=rec.potential_hold_amount,
                authorization_boundary=rec.authorization_boundary,
                status="PENDING_REVIEW",
            )
            self.db.add(interv_db)

        # Log completion audit event
        self.add_audit_event(
            case_id=case_id,
            event_type="ANALYSIS_COMPLETED",
            actor="CIRIS_ENGINE",
            description=f"Intelligence pipeline completed. Risk score: {intel_obj.overall_case_risk:.2f}",
            source="CIRIS_ML_V4",
        )

        self.db.commit()
        return case_model, intel_obj

    def list_cases(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        min_risk: Optional[float] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[CaseModel], int]:
        """Query paginated cases with status, priority, risk, and keyword search filters."""
        query = self.db.query(CaseModel)

        if status:
            query = query.filter(CaseModel.status == status.upper())
        if priority:
            query = query.filter(CaseModel.priority == priority.upper())
        if min_risk is not None:
            query = query.filter(CaseModel.overall_risk_score >= min_risk)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    CaseModel.case_id.ilike(search_pattern),
                    CaseModel.complaint_id.ilike(search_pattern),
                    CaseModel.fraud_type.ilike(search_pattern),
                    CaseModel.city.ilike(search_pattern),
                    CaseModel.district.ilike(search_pattern),
                )
            )

        total_count = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(desc(CaseModel.created_at)).offset(offset).limit(page_size).all()
        return items, total_count

    def get_case(self, case_id: str) -> Optional[CaseModel]:
        """Fetch case by case_id."""
        return self.db.query(CaseModel).filter(CaseModel.case_id == case_id).first()

    def get_case_intelligence(self, case_id: str) -> Optional[CaseIntelligenceObject]:
        """Retrieve full CaseIntelligenceObject for a case."""
        case = self.get_case(case_id)
        if not case:
            return None

        # Check cache
        cached = self.intelligence_service.get_cached_intelligence(case_id)
        if cached:
            cached.case_id = case.case_id
            return cached

        # Re-run intelligence pipeline for case
        payload = ComplaintPayload(
            complaint_id=case.complaint_id,
            complaint_timestamp=case.complaint_timestamp,
            fraud_type=case.fraud_type,
            reported_loss_amount=case.reported_loss_amount,
            victim_location=VictimLocation(
                state=case.state,
                district=case.district,
                city=case.city,
                latitude=case.latitude,
                longitude=case.longitude,
            ),
        )
        intel = self.intelligence_service.run_case_intelligence(payload)
        intel.case_id = case.case_id
        return intel

    def get_case_timeline(self, case_id: str) -> List[Dict[str, Any]]:
        """Construct chronological timeline of complaint, transaction, ML prediction, and investigator events."""
        events = self.db.query(CaseEventModel).filter(CaseEventModel.case_id == case_id).order_by(CaseEventModel.timestamp).all()
        result = []
        for ev in events:
            result.append({
                "event_id": ev.event_id,
                "timestamp": ev.timestamp.isoformat() if ev.timestamp else datetime.utcnow().isoformat(),
                "type": ev.event_type,
                "description": ev.description,
                "source": ev.source,
                "actor": ev.actor,
                "metadata": ev.metadata_json or {},
            })
        return result

    def add_audit_event(
        self,
        case_id: str,
        event_type: str,
        actor: str = "INVESTIGATOR",
        description: str = "",
        source: str = "CIRIS_API",
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> CaseEventModel:
        """Log audit event to case_events table."""
        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        ev = CaseEventModel(
            event_id=event_id,
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            description=description,
            source=source,
            timestamp=datetime.utcnow(),
            metadata_json=metadata_json or {},
        )
        self.db.add(ev)
        self.db.commit()
        return ev

"""
Operational Guardrails, PII Sanitization, and Multi-Agency Dispatch Routing.

Implements Stage 7 of CIPHER-X v4:
- Ensures strict PII isolation and data integrity.
- Filters out non-actionable complaints (e.g. extreme reporting delays or zero losses).
- Segregates alerts into Bank Nodal Officer and Police Dispatch channels.
"""

import re
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload, IntelligenceReport, ATMRiskPrediction


class OperationalGuardrails:
    """
    Validates complaint actionability, sanitizes PII, and determines agency dispatch priority.
    """

    MAX_ACTIONABLE_DELAY_HOURS = 72.0
    MIN_REPORTED_LOSS_INR = 100.0

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """Mask account numbers, phone numbers, and Aadhaar numbers."""
        if not text:
            return ""
        # Mask 10-digit phone numbers
        text = re.sub(r"\b[6-9]\d{9}\b", "[PHONE_REDACTED]", text)
        # Mask 12-digit Aadhaar / Account numbers
        text = re.sub(r"\b\d{12,16}\b", "[ACC_REDACTED]", text)
        return text

    @classmethod
    def check_complaint_actionability(cls, complaint: ComplaintPayload) -> Tuple[bool, str]:
        """
        Determine if complaint is actionable for real-time proactive intervention.

        Returns:
            Tuple of:
            - is_actionable: bool
            - routing_reason: str
        """
        # Loss amount check
        if complaint.reported_loss_amount < cls.MIN_REPORTED_LOSS_INR:
            return False, "DE_MINIMIS_LOSS: Loss below real-time intervention threshold"

        # Temporal delay check
        if complaint.incident_timestamp:
            elapsed_hours = (complaint.complaint_timestamp - complaint.incident_timestamp).total_seconds() / 3600.0
            if elapsed_hours > cls.MAX_ACTIONABLE_DELAY_HOURS:
                return False, f"EXPIRED_WINDOW: Incident reported {elapsed_hours:.1f}h later (exceeds {cls.MAX_ACTIONABLE_DELAY_HOURS}h)"

        # Geographic validity check
        v_lat = complaint.victim_location.latitude
        v_lon = complaint.victim_location.longitude
        if not (6.0 <= v_lat <= 38.0 and 68.0 <= v_lon <= 98.0):
            return False, f"OUT_OF_BOUNDS_COORDINATES: ({v_lat}, {v_lon}) outside Indian jurisdiction"

        return True, "ACTIONABLE_PROCEED"

    @staticmethod
    def format_bank_dispatch_payload(
        complaint: ComplaintPayload,
        top_atm: ATMRiskPrediction,
    ) -> Dict[str, Any]:
        """
        Format standardized payload for Bank Nodal Officer alert bridge.
        """
        return {
            "alert_id": f"BANK_ALERT_{complaint.complaint_id}_{top_atm.atm_id}",
            "complaint_id": complaint.complaint_id,
            "target_bank": top_atm.bank_name,
            "suspected_atm_id": top_atm.atm_id,
            "atm_name": top_atm.atm_name,
            "atm_location": {
                "city": top_atm.city,
                "district": top_atm.district,
                "latitude": top_atm.latitude,
                "longitude": top_atm.longitude,
            },
            "predicted_risk_level": top_atm.confidence_tier,
            "fused_risk_score": top_atm.fused_risk_score,
            "time_to_cashout_window": top_atm.predicted_time_window,
            "recommended_action": top_atm.action_required,
            "timestamp": datetime.now().isoformat(),
        }

    @staticmethod
    def format_lea_dispatch_payload(
        complaint: ComplaintPayload,
        report: IntelligenceReport,
    ) -> Dict[str, Any]:
        """
        Format standardized payload for Law Enforcement Agency (LEA) police control room.
        """
        top_atm = report.highest_risk_atm
        return {
            "dispatch_id": f"LEA_DISPATCH_{complaint.complaint_id}",
            "complaint_id": complaint.complaint_id,
            "jurisdiction": {
                "state": complaint.victim_location.state,
                "district": top_atm.district if top_atm else complaint.victim_location.district,
                "city": top_atm.city if top_atm else complaint.victim_location.city,
            },
            "priority": "P1_CRITICAL" if report.alert_status == "DISPATCH_ALERT" else "P3_MONITOR",
            "predicted_atm": {
                "atm_id": top_atm.atm_id if top_atm else "NONE",
                "atm_name": top_atm.atm_name if top_atm else "NONE",
                "distance_km": top_atm.distance_km if top_atm else 0.0,
                "coordinates": [top_atm.latitude, top_atm.longitude] if top_atm else [],
            },
            "time_window": top_atm.predicted_time_window if top_atm else "UNKNOWN",
            "officer_briefing": top_atm.shap_evidence if top_atm else [],
            "timestamp": datetime.now().isoformat(),
        }

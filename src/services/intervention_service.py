"""
CIRIS Phase 4 — Intervention Recommendation Policy Service.
Provides transparent decision-support recommendations:
HOLD_REVIEW, MONITOR, INVESTIGATE, ESCALATE.

IMPORTANT: Strictly decision-support. Never performs autonomous fund freezing or arrests.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.db.database import get_db_connection
from src.db.operational_models import (
    InterventionRecommendation,
    InterventionRecord,
    PriorityLevel,
)
from src.services.evidence_service import EvidenceService

logger = logging.getLogger("ciris.services.intervention")

AUTHORIZATION_BOUNDARY_STATEMENT = (
    "DECISION SUPPORT ONLY: Recommendations are generated to assist authorized LEA officers "
    "and bank AML compliance desks. CIRIS does not autonomously freeze accounts, seize funds, "
    "or initiate law enforcement actions without human officer verification."
)


class InterventionService:
    """Intervention Policy Engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.evidence_service = EvidenceService(db_path)

    def generate_recommendation(
        self,
        case_id: str,
        risk_score: float,
        confidence: float,
        amount_at_risk: float,
        time_window_label: Optional[str] = None,
        hop_count: int = 1,
        priority: PriorityLevel = PriorityLevel.P2,
        is_fragmented: bool = False
    ) -> InterventionRecord:
        """
        Evaluate deterministic intervention policy and generate a traceable recommendation.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        evidence_items = self.evidence_service.get_case_evidence(case_id)
        evidence_ids = [e.evidence_id for e in evidence_items]

        # Decision Policy Rules:
        time_win = str(time_window_label or "").lower()
        is_imminent = "0-3" in time_win or (priority == PriorityLevel.P1)
        
        if (risk_score >= 0.70 and is_imminent) or (amount_at_risk >= 100000.0 and confidence >= 0.75):
            recommendation = InterventionRecommendation.HOLD_REVIEW
            reason = (
                f"High-confidence imminent cash-out risk (Risk: {risk_score:.2f}, Window: {time_window_label or 'Imminent'}). "
                f"Recommended immediate review of terminal mule accounts and ATM interception alert dispatch for ₹{amount_at_risk:,.2f}."
            )
        elif priority == PriorityLevel.P1 or (hop_count >= 3 and is_fragmented):
            recommendation = InterventionRecommendation.ESCALATE
            reason = (
                f"Active high-velocity mule network detected across {hop_count} hops. "
                "Recommended escalation to Cyber Cell Supervisor and Bank AML nodal officers."
            )
        elif risk_score >= 0.45 or amount_at_risk >= 25000.0:
            recommendation = InterventionRecommendation.INVESTIGATE
            reason = (
                f"Moderate risk with active money flow (Risk: {risk_score:.2f}, Loss: ₹{amount_at_risk:,.2f}). "
                "Recommended standard investigation and account statement linkage."
            )
        else:
            recommendation = InterventionRecommendation.MONITOR
            reason = (
                f"Low risk profile (Risk: {risk_score:.2f}). "
                "Recommended automated behavioral monitoring and cross-case correlation tracking."
            )

        interv_id = f"INT_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO interventions (
                intervention_id, case_id, recommendation, reason, evidence_ids,
                authorization_boundary, generated_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                interv_id, case_id, recommendation.value, reason,
                ",".join(evidence_ids), AUTHORIZATION_BOUNDARY_STATEMENT,
                now_iso, "PENDING_REVIEW"
            ))

            # Audit record
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_REC_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, "POLICY_ENGINE", "INTERVENTION_RECOMMENDED", now_iso,
                json.dumps({
                    "intervention_id": interv_id,
                    "recommendation": recommendation.value,
                    "reason": reason,
                    "amount_at_risk": amount_at_risk
                })
            ))
            conn.commit()

        return InterventionRecord(
            intervention_id=interv_id,
            case_id=case_id,
            recommendation=recommendation,
            reason=reason,
            evidence_ids=evidence_ids,
            authorization_boundary=AUTHORIZATION_BOUNDARY_STATEMENT,
            generated_at=now_iso,
            status="PENDING_REVIEW"
        )

    def review_intervention(
        self,
        intervention_id: str,
        reviewer: str,
        action: str,  # 'ACCEPT', 'REJECT', 'ESCALATE'
        notes: Optional[str] = None
    ) -> InterventionRecord:
        """Record authorized human review of an intervention recommendation."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT intervention_id, case_id, recommendation, reason, evidence_ids,
                   authorization_boundary, generated_at, status, reviewed_by, reviewed_at, review_notes
            FROM interventions WHERE intervention_id = ?;
            """, (intervention_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Intervention {intervention_id} not found")

            case_id = row["case_id"]
            new_status = f"{action}ED" if not action.endswith("E") else f"{action}D"
            cursor.execute("""
            UPDATE interventions
            SET status = ?, reviewed_by = ?, reviewed_at = ?, review_notes = ?
            WHERE intervention_id = ?;
            """, (new_status, reviewer, now_iso, notes, intervention_id))

            # Audit record
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_INT_REV_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, reviewer, "INTERVENTION_REVIEWED", now_iso,
                json.dumps({"intervention_id": intervention_id, "action": action, "notes": notes})
            ))
            conn.commit()

            return InterventionRecord(
                intervention_id=row["intervention_id"],
                case_id=row["case_id"],
                recommendation=InterventionRecommendation(row["recommendation"]),
                reason=row["reason"],
                evidence_ids=(row["evidence_ids"] or "").split(",") if row["evidence_ids"] else [],
                authorization_boundary=row["authorization_boundary"],
                generated_at=row["generated_at"],
                status=new_status,
                reviewed_by=reviewer,
                reviewed_at=now_iso,
                review_notes=notes
            )

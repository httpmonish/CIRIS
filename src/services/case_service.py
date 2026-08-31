"""
CIRIS Phase 4 — Case Lifecycle Management & Assignment Service.
Handles state transitions, investigator/team assignments, notes, feedback, and SLA ageing.
"""

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.db.database import get_db_connection
from src.db.operational_models import (
    CaseLifecycleRecord,
    CaseNote,
    CaseStatus,
    InvestigatorFeedbackCreateRequest,
    InvestigatorOutcome,
    PriorityLevel,
)
from src.services.audit_service import AuditService

logger = logging.getLogger("ciris.services.case")

ALLOWED_TRANSITIONS = {
    CaseStatus.NEW: [CaseStatus.ACKNOWLEDGED, CaseStatus.ASSIGNED, CaseStatus.INVESTIGATING, CaseStatus.CLOSED],
    CaseStatus.ACKNOWLEDGED: [CaseStatus.ASSIGNED, CaseStatus.INVESTIGATING, CaseStatus.ESCALATED, CaseStatus.CLOSED],
    CaseStatus.ASSIGNED: [CaseStatus.INVESTIGATING, CaseStatus.ESCALATED, CaseStatus.MONITORING, CaseStatus.CLOSED],
    CaseStatus.INVESTIGATING: [CaseStatus.ESCALATED, CaseStatus.MONITORING, CaseStatus.RESOLVED, CaseStatus.CLOSED],
    CaseStatus.ESCALATED: [CaseStatus.INVESTIGATING, CaseStatus.RESOLVED, CaseStatus.CLOSED],
    CaseStatus.MONITORING: [CaseStatus.INVESTIGATING, CaseStatus.RESOLVED, CaseStatus.CLOSED],
    CaseStatus.RESOLVED: [CaseStatus.CLOSED, CaseStatus.INVESTIGATING],  # Allows explicit reopen
    CaseStatus.CLOSED: [CaseStatus.NEW]  # Reopen path requires NEW
}


class CaseService:
    """Case Lifecycle & Workflow Service."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.audit_service = AuditService(db_path)

    def get_or_create_case(
        self,
        complaint_id: str,
        priority: PriorityLevel = PriorityLevel.P2,
        risk_score: float = 0.5,
        amount_at_risk: float = 0.0,
        endpoint_type: str = "ATM",
        predicted_endpoint_id: Optional[str] = None,
        summary: Optional[str] = None
    ) -> CaseLifecycleRecord:
        """Idempotently fetch or create case lifecycle record."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM case_lifecycle WHERE complaint_id = ?", (complaint_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_case_record(row)

            # Check if complaint exists in geo_cases
            cursor.execute("SELECT reported_loss_amount, urgency_score, fraud_type FROM geo_cases WHERE complaint_id = ?", (complaint_id,))
            gcase = cursor.fetchone()
            if gcase:
                amount_at_risk = float(gcase["reported_loss_amount"] or amount_at_risk)
                risk_score = float(gcase["urgency_score"] or risk_score)

            case_id = f"CASE_{complaint_id.replace('CASE_', '')}"
            sla_deadline = (datetime.now(timezone.utc) + timedelta(hours=4 if priority == PriorityLevel.P3 else (1 if priority == PriorityLevel.P2 else 0.25))).isoformat()

            cursor.execute("""
            INSERT INTO case_lifecycle (
                case_id, complaint_id, priority, status, risk_score,
                amount_at_risk, endpoint_type, predicted_endpoint_id,
                summary, created_at, updated_at, sla_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                case_id, complaint_id, priority.value, CaseStatus.NEW.value,
                risk_score, amount_at_risk, endpoint_type, predicted_endpoint_id,
                summary or f"Investigation into {complaint_id}", now_iso, now_iso, sla_deadline
            ))

            # Insert audit record directly on the same connection cursor
            event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case_id, "SYSTEM_REGISTRATION", "CASE_CREATED", now_iso,
                json.dumps({"complaint_id": complaint_id, "priority": priority.value, "amount_at_risk": amount_at_risk})
            ))
            conn.commit()

            cursor.execute("SELECT * FROM case_lifecycle WHERE case_id = ?", (case_id,))
            return self._row_to_case_record(cursor.fetchone())

    def get_case(self, case_id: str) -> Optional[CaseLifecycleRecord]:
        """Fetch case by ID or complaint ID."""
        gcase_data = None
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM case_lifecycle WHERE case_id = ? OR complaint_id = ?", (case_id, case_id))
            row = cursor.fetchone()
            if row:
                return self._row_to_case_record(row)
            
            # Check geo_cases
            cursor.execute("SELECT complaint_id, reported_loss_amount, urgency_score FROM geo_cases WHERE complaint_id = ?", (case_id,))
            gcase = cursor.fetchone()
            if gcase:
                gcase_data = {
                    "complaint_id": gcase["complaint_id"],
                    "loss": float(gcase["reported_loss_amount"] or 0.0),
                    "urgency": float(gcase["urgency_score"] or 0.5)
                }

        if gcase_data:
            return self.get_or_create_case(
                complaint_id=gcase_data["complaint_id"],
                amount_at_risk=gcase_data["loss"],
                risk_score=gcase_data["urgency"]
            )
        return None

    def transition_status(
        self,
        case_id: str,
        target_status: CaseStatus,
        actor: str,
        notes: Optional[str] = None,
        resolution_outcome: Optional[InvestigatorOutcome] = None
    ) -> CaseLifecycleRecord:
        """Perform validated state transition."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        current = case.status
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target_status not in allowed and target_status != current:
            raise ValueError(f"Invalid status transition from {current.value} to {target_status.value}. Allowed: {[s.value for s in allowed]}")

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            updates = ["status = ?", "updated_at = ?"]
            params = [target_status.value, now_iso]

            if target_status == CaseStatus.ACKNOWLEDGED and not case.acknowledged_at:
                updates.append("acknowledged_at = ?")
                params.append(now_iso)
            elif target_status == CaseStatus.INVESTIGATING and not case.first_review_at:
                updates.append("first_review_at = ?")
                params.append(now_iso)
            elif target_status == CaseStatus.RESOLVED:
                updates.append("resolved_at = ?")
                params.append(now_iso)
                if resolution_outcome:
                    updates.append("resolution_outcome = ?")
                    params.append(resolution_outcome.value)
            elif target_status == CaseStatus.CLOSED:
                updates.append("closed_at = ?")
                params.append(now_iso)

            params.append(case.case_id)
            cursor.execute(f"UPDATE case_lifecycle SET {', '.join(updates)} WHERE case_id = ?", params)

            # Audit event directly on same cursor
            action_name = f"CASE_{target_status.value}"
            event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case.case_id, actor, action_name, now_iso,
                json.dumps({"previous_status": current.value, "target_status": target_status.value, "notes": notes})
            ))
            conn.commit()

        return self.get_case(case_id)

    def assign_case(
        self,
        case_id: str,
        owner: str,
        assigned_by: str,
        team: Optional[str] = None,
        notes: Optional[str] = None
    ) -> CaseLifecycleRecord:
        """Assign case to investigator/team."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE case_lifecycle
            SET owner = ?, team = ?, status = ?, assigned_at = ?, updated_at = ?
            WHERE case_id = ?;
            """, (owner, team, CaseStatus.ASSIGNED.value, now_iso, now_iso, case.case_id))

            event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case.case_id, assigned_by, "CASE_ASSIGNED", now_iso,
                json.dumps({"owner": owner, "team": team, "notes": notes})
            ))
            conn.commit()

        return self.get_case(case_id)

    def add_note(self, case_id: str, author: str, content: str, visibility: str = "INTERNAL") -> CaseNote:
        """Add investigator observation note."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        now_iso = datetime.now(timezone.utc).isoformat()
        note_id = f"NOTE_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO case_notes (note_id, case_id, author, created_at, content, visibility)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (note_id, case.case_id, author, now_iso, content, visibility))

            event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case.case_id, author, "NOTE_ADDED", now_iso,
                json.dumps({"note_id": note_id, "visibility": visibility})
            ))
            conn.commit()

        return CaseNote(
            note_id=note_id,
            case_id=case.case_id,
            author=author,
            created_at=now_iso,
            content=content,
            visibility=visibility
        )

    def get_notes(self, case_id: str) -> List[CaseNote]:
        """Fetch all notes for a case."""
        case = self.get_case(case_id)
        if not case:
            return []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT note_id, case_id, author, created_at, content, visibility
            FROM case_notes
            WHERE case_id = ?
            ORDER BY created_at DESC;
            """, (case.case_id,))
            return [
                CaseNote(
                    note_id=r["note_id"],
                    case_id=r["case_id"],
                    author=r["author"],
                    created_at=r["created_at"],
                    content=r["content"],
                    visibility=r["visibility"]
                )
                for r in cursor.fetchall()
            ]

    def record_feedback(self, case_id: str, req: InvestigatorFeedbackCreateRequest) -> Dict[str, Any]:
        """Record post-investigation outcome feedback."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        now_iso = datetime.now(timezone.utc).isoformat()
        fb_id = f"FB_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO investigator_feedback (
                feedback_id, case_id, investigator_id, outcome, notes,
                actual_cashout_atm_id, actual_loss_recovered, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                fb_id, case.case_id, req.investigator_id, req.outcome.value,
                req.notes, req.actual_cashout_atm_id, req.actual_loss_recovered, now_iso
            ))

            # Automatically transition to RESOLVED with outcome
            cursor.execute("""
            UPDATE case_lifecycle
            SET status = ?, resolved_at = ?, resolution_outcome = ?, updated_at = ?
            WHERE case_id = ?;
            """, (CaseStatus.RESOLVED.value, now_iso, req.outcome.value, now_iso, case.case_id))

            event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case.case_id, req.investigator_id, "FEEDBACK_SUBMITTED", now_iso,
                json.dumps({
                    "feedback_id": fb_id,
                    "outcome": req.outcome.value,
                    "actual_loss_recovered": req.actual_loss_recovered
                })
            ))
            conn.commit()

        return {
            "feedback_id": fb_id,
            "case_id": case.case_id,
            "outcome": req.outcome.value,
            "submitted_at": now_iso,
            "status": "RECORDED"
        }

    def _row_to_case_record(self, r: sqlite3.Row) -> CaseLifecycleRecord:
        return CaseLifecycleRecord(
            case_id=r["case_id"],
            complaint_id=r["complaint_id"],
            priority=PriorityLevel(r["priority"]),
            status=CaseStatus(r["status"]),
            owner=r["owner"],
            team=r["team"],
            risk_score=float(r["risk_score"] or 0.0),
            amount_at_risk=float(r["amount_at_risk"] or 0.0),
            endpoint_type=r["endpoint_type"] or "UNKNOWN",
            predicted_endpoint_id=r["predicted_endpoint_id"],
            summary=r["summary"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            sla_deadline=r["sla_deadline"],
            acknowledged_at=r["acknowledged_at"],
            assigned_at=r["assigned_at"],
            first_review_at=r["first_review_at"],
            resolved_at=r["resolved_at"],
            closed_at=r["closed_at"],
            resolution_outcome=InvestigatorOutcome(r["resolution_outcome"]) if r["resolution_outcome"] else None
        )

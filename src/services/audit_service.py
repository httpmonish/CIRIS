"""
CIRIS Phase 4 — Append-Only Audit Trail Service.
Guarantees immutability and complete forensic traceability of all operational actions.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.db.database import get_db_connection
from src.db.operational_models import AuditEvent

logger = logging.getLogger("ciris.services.audit")


class AuditService:
    """Append-Only Audit Engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def log_event(
        self,
        actor: str,
        action: str,
        case_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Append a new forensic audit event."""
        now_iso = datetime.now(timezone.utc).isoformat()
        event_id = f"AUD_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{uuid.uuid4().hex[:6]}"
        meta_json = json.dumps(metadata or {})

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (event_id, case_id, actor, action, now_iso, meta_json))
            conn.commit()

        return AuditEvent(
            event_id=event_id,
            case_id=case_id,
            actor=actor,
            action=action,
            timestamp=now_iso,
            metadata=metadata or {}
        )

    def get_events_for_case(self, case_id: str, limit: int = 100) -> List[AuditEvent]:
        """Retrieve audit history for a specific case."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT event_id, case_id, actor, action, timestamp, metadata_json
            FROM audit_trail
            WHERE case_id = ?
            ORDER BY timestamp DESC
            LIMIT ?;
            """, (case_id, limit))
            rows = cursor.fetchall()

            return [
                AuditEvent(
                    event_id=r["event_id"],
                    case_id=r["case_id"],
                    actor=r["actor"],
                    action=r["action"],
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata_json"] or "{}")
                )
                for r in rows
            ]

    def get_all_events(self, limit: int = 100, offset: int = 0) -> List[AuditEvent]:
        """Retrieve system-wide audit history."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT event_id, case_id, actor, action, timestamp, metadata_json
            FROM audit_trail
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?;
            """, (limit, offset))
            rows = cursor.fetchall()

            return [
                AuditEvent(
                    event_id=r["event_id"],
                    case_id=r["case_id"],
                    actor=r["actor"],
                    action=r["action"],
                    timestamp=r["timestamp"],
                    metadata=json.loads(r["metadata_json"] or "{}")
                )
                for r in rows
            ]

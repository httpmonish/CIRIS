"""
CIRIS Phase 4 — Alert Generation, Prioritization & Lifecycle Service.
Implements deterministic P1-P4 priority scoring, deduplication hashing,
cooldown suppression guardrails, and audit logging.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.db.database import get_db_connection
from src.db.operational_models import (
    Alert,
    AlertType,
    CaseStatus,
    PriorityLevel,
    SeverityLevel,
    UserRole,
)

logger = logging.getLogger("ciris.services.alert")


def calculate_priority_score(
    risk_score: float,
    time_window_label: Optional[str],
    amount_at_risk: float,
    hop_count: int = 1,
    is_fragmented: bool = False,
    is_mule_cluster: bool = False,
    urgency_score: float = 0.5
) -> Tuple[PriorityLevel, SeverityLevel, float]:
    """
    Deterministic calculation of Priority (P1-P4), Severity, and Composite Score.
    Follows docs/phase4_alert_prioritization.md.
    """
    # 1. Imminence score
    time_win = str(time_window_label or "").lower()
    if "0-3" in time_win:
        t_imminence = 1.0
    elif "3-6" in time_win:
        t_imminence = 0.7
    else:
        t_imminence = 0.4

    # 2. Normalized amount at risk
    a_norm = min(1.0, max(0.0, amount_at_risk / 500000.0))

    # 3. Network evidence
    n_evid = 0.0
    if hop_count >= 2:
        n_evid += 0.4
    if is_fragmented:
        n_evid += 0.3
    if is_mule_cluster:
        n_evid += 0.3
    n_evid = min(1.0, n_evid)

    # Composite Score
    score = (
        0.30 * risk_score
        + 0.25 * t_imminence
        + 0.20 * a_norm
        + 0.15 * n_evid
        + 0.10 * urgency_score
    )
    score = round(min(1.0, max(0.0, score)), 4)

    # Priority determination
    if score >= 0.70 or (t_imminence == 1.0 and risk_score >= 0.80) or (amount_at_risk >= 100000.0 and t_imminence == 1.0) or (is_mule_cluster and risk_score >= 0.80):
        priority = PriorityLevel.P1
        severity = SeverityLevel.CRITICAL
    elif score >= 0.50 or (hop_count >= 2 and amount_at_risk >= 50000.0) or risk_score >= 0.65:
        priority = PriorityLevel.P2
        severity = SeverityLevel.HIGH
    elif score >= 0.30:
        priority = PriorityLevel.P3
        severity = SeverityLevel.MEDIUM
    else:
        priority = PriorityLevel.P4
        severity = SeverityLevel.LOW

    return priority, severity, score


def generate_dedup_hash(case_id: str, alert_type: str, endpoint_id: Optional[str], timestamp_iso: str) -> str:
    """Generate deterministic deduplication hash bucketed by 15-minute intervals."""
    try:
        dt = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    
    minute_bucket = (dt.minute // 15) * 15
    bucket_str = f"{dt.year}-{dt.month:02d}-{dt.day:02d}_{dt.hour:02d}:{minute_bucket:02d}"
    raw = f"{case_id}:{alert_type}:{endpoint_id or 'NONE'}:{bucket_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AlertService:
    """Operational Alert Engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def create_alert(
        self,
        case_id: str,
        alert_type: AlertType,
        risk_score: float,
        confidence: float,
        amount_at_risk: float,
        endpoint_type: str = "ATM",
        predicted_endpoint_id: Optional[str] = None,
        time_window_label: Optional[str] = None,
        hop_count: int = 1,
        is_fragmented: bool = False,
        is_mule_cluster: bool = False,
        urgency_score: float = 0.5,
        evidence_summary: Optional[str] = None,
        prediction_timestamp: Optional[str] = None,
        actor: str = "SYSTEM_INTELLIGENCE",
        bypass_dedup: bool = False
    ) -> Optional[Alert]:
        """
        Creates an operational alert if not suppressed by deduplication or cooldown guardrails.
        """
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        pred_ts = prediction_timestamp or now_iso

        priority, severity, composite_score = calculate_priority_score(
            risk_score=risk_score,
            time_window_label=time_window_label,
            amount_at_risk=amount_at_risk,
            hop_count=hop_count,
            is_fragmented=is_fragmented,
            is_mule_cluster=is_mule_cluster,
            urgency_score=urgency_score
        )

        alert_type_val = alert_type.value if hasattr(alert_type, "value") else str(alert_type)
        dedup_hash = generate_dedup_hash(case_id, alert_type_val, predicted_endpoint_id, now_iso)
        if bypass_dedup:
            dedup_hash = f"{dedup_hash}_{int(now.timestamp() * 1000)}"

        # SLA Deadlines based on Priority
        sla_deltas = {
            PriorityLevel.P1: timedelta(minutes=15),
            PriorityLevel.P2: timedelta(hours=1),
            PriorityLevel.P3: timedelta(hours=4),
            PriorityLevel.P4: timedelta(hours=24)
        }
        sla_deadline = (now + sla_deltas[priority]).isoformat()

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            if not bypass_dedup:
                # Guardrail 1: Check for exact dedup hash
                cursor.execute("SELECT alert_id FROM operational_alerts WHERE dedup_hash = ?", (dedup_hash,))
                existing = cursor.fetchone()
                if existing:
                    logger.info("Alert suppressed: duplicate hash %s for case %s", dedup_hash, case_id)
                    return None

                # Guardrail 2: Check 1-hour case cooldown unless new alert has higher priority (e.g. P1)
                cursor.execute("""
                SELECT alert_id, priority, created_at FROM operational_alerts
                WHERE case_id = ? AND status NOT IN ('RESOLVED', 'CLOSED')
                ORDER BY created_at DESC LIMIT 1;
                """, (case_id,))
                recent = cursor.fetchone()
                if recent:
                    recent_prio = recent["priority"]
                    if priority != PriorityLevel.P1 and recent_prio in (PriorityLevel.P1.value, PriorityLevel.P2.value):
                        logger.info("Alert suppressed by case cooldown for case %s", case_id)
                        return None

            # Generate alert_id
            cursor.execute("SELECT COUNT(*) FROM operational_alerts")
            cnt = cursor.fetchone()[0]
            alert_id = f"ALT_{now.strftime('%Y%m%d')}_{cnt + 1:05d}"

            cursor.execute("""
            INSERT INTO operational_alerts (
                alert_id, case_id, created_at, prediction_timestamp, alert_type,
                priority, severity, risk_score, confidence, endpoint_type,
                predicted_endpoint_id, amount_at_risk, status, source,
                evidence_summary, dedup_hash, sla_deadline
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                alert_id, case_id, now_iso, pred_ts, alert_type_val,
                priority.value, severity.value, risk_score, confidence,
                endpoint_type, predicted_endpoint_id, amount_at_risk,
                CaseStatus.NEW.value, "CIRIS_INTELLIGENCE",
                evidence_summary or f"Automated risk alert for {case_id} ({alert_type_val})",
                dedup_hash, sla_deadline
            ))

            # Audit Event
            event_id = f"AUD_{now.strftime('%Y%m%d%H%M%S')}_{cnt + 1:05d}"
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                event_id, case_id, actor, "ALERT_CREATED", now_iso,
                json.dumps({
                    "alert_id": alert_id,
                    "priority": priority.value,
                    "severity": severity.value,
                    "risk_score": risk_score,
                    "amount_at_risk": amount_at_risk
                })
            ))

            conn.commit()

            return Alert(
                alert_id=alert_id,
                case_id=case_id,
                created_at=now_iso,
                prediction_timestamp=pred_ts,
                alert_type=AlertType(alert_type_val),
                priority=priority,
                severity=severity,
                risk_score=risk_score,
                confidence=confidence,
                endpoint_type=endpoint_type,
                predicted_endpoint_id=predicted_endpoint_id,
                amount_at_risk=amount_at_risk,
                status=CaseStatus.NEW,
                source="CIRIS_INTELLIGENCE",
                evidence_summary=evidence_summary,
                dedup_hash=dedup_hash,
                sla_deadline=sla_deadline
            )

    def get_alerts(
        self,
        case_id: Optional[str] = None,
        priority: Optional[PriorityLevel] = None,
        status: Optional[CaseStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Alert]:
        """Fetch alerts with filtering and pagination."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            conditions = []
            params = []

            if case_id:
                conditions.append("case_id = ?")
                params.append(case_id)
            if priority:
                conditions.append("priority = ?")
                params.append(priority.value)
            if status:
                conditions.append("status = ?")
                params.append(status.value)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            query = f"""
            SELECT alert_id, case_id, created_at, prediction_timestamp, alert_type,
                   priority, severity, risk_score, confidence, endpoint_type,
                   predicted_endpoint_id, amount_at_risk, status, assigned_to,
                   assigned_team, source, evidence_summary, dedup_hash, sla_deadline,
                   acknowledged_at, first_reviewed_at, resolved_at, closed_at
            FROM operational_alerts
            {where_clause}
            ORDER BY 
                CASE priority WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 WHEN 'P3' THEN 3 ELSE 4 END,
                created_at DESC
            LIMIT ? OFFSET ?;
            """
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                Alert(
                    alert_id=r["alert_id"],
                    case_id=r["case_id"],
                    created_at=r["created_at"],
                    prediction_timestamp=r["prediction_timestamp"],
                    alert_type=AlertType(r["alert_type"]),
                    priority=PriorityLevel(r["priority"]),
                    severity=SeverityLevel(r["severity"]),
                    risk_score=float(r["risk_score"]),
                    confidence=float(r["confidence"]),
                    endpoint_type=r["endpoint_type"] or "ATM",
                    predicted_endpoint_id=r["predicted_endpoint_id"],
                    amount_at_risk=float(r["amount_at_risk"] or 0.0),
                    status=CaseStatus(r["status"]),
                    assigned_to=r["assigned_to"],
                    assigned_team=r["assigned_team"],
                    source=r["source"] or "CIRIS_INTELLIGENCE",
                    evidence_summary=r["evidence_summary"],
                    dedup_hash=r["dedup_hash"],
                    sla_deadline=r["sla_deadline"],
                    acknowledged_at=r["acknowledged_at"],
                    first_reviewed_at=r["first_reviewed_at"],
                    resolved_at=r["resolved_at"],
                    closed_at=r["closed_at"]
                )
                for r in rows
            ]

    def get_alert_by_id(self, alert_id: str) -> Optional[Alert]:
        """Fetch alert by ID."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT alert_id, case_id, created_at, prediction_timestamp, alert_type,
                   priority, severity, risk_score, confidence, endpoint_type,
                   predicted_endpoint_id, amount_at_risk, status, assigned_to,
                   assigned_team, source, evidence_summary, dedup_hash, sla_deadline,
                   acknowledged_at, first_reviewed_at, resolved_at, closed_at
            FROM operational_alerts WHERE alert_id = ?;
            """, (alert_id,))
            r = cursor.fetchone()
            if not r:
                return None
            return Alert(
                alert_id=r["alert_id"],
                case_id=r["case_id"],
                created_at=r["created_at"],
                prediction_timestamp=r["prediction_timestamp"],
                alert_type=AlertType(r["alert_type"]),
                priority=PriorityLevel(r["priority"]),
                severity=SeverityLevel(r["severity"]),
                risk_score=float(r["risk_score"]),
                confidence=float(r["confidence"]),
                endpoint_type=r["endpoint_type"] or "ATM",
                predicted_endpoint_id=r["predicted_endpoint_id"],
                amount_at_risk=float(r["amount_at_risk"] or 0.0),
                status=CaseStatus(r["status"]),
                assigned_to=r["assigned_to"],
                assigned_team=r["assigned_team"],
                source=r["source"] or "CIRIS_INTELLIGENCE",
                evidence_summary=r["evidence_summary"],
                dedup_hash=r["dedup_hash"],
                sla_deadline=r["sla_deadline"],
                acknowledged_at=r["acknowledged_at"],
                first_reviewed_at=r["first_reviewed_at"],
                resolved_at=r["resolved_at"],
                closed_at=r["closed_at"]
            )

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: Optional[str] = None) -> Alert:
        """Acknowledge alert and transition status to ACKNOWLEDGED."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_id, status FROM operational_alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Alert {alert_id} not found")

            case_id = row["case_id"]
            cursor.execute("""
            UPDATE operational_alerts
            SET status = ?, acknowledged_at = COALESCE(acknowledged_at, ?)
            WHERE alert_id = ?;
            """, (CaseStatus.ACKNOWLEDGED.value, now_iso, alert_id))

            # Audit record
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_ACK_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, acknowledged_by, "ALERT_ACKNOWLEDGED", now_iso,
                json.dumps({"alert_id": alert_id, "notes": notes})
            ))
            conn.commit()

        return self.get_alert_by_id(alert_id)

    def assign_alert(self, alert_id: str, assigned_to: str, assigned_by: str, assigned_team: Optional[str] = None) -> Alert:
        """Assign alert to investigator/team."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_id FROM operational_alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Alert {alert_id} not found")

            case_id = row["case_id"]
            cursor.execute("""
            UPDATE operational_alerts
            SET status = ?, assigned_to = ?, assigned_team = ?
            WHERE alert_id = ?;
            """, (CaseStatus.ASSIGNED.value, assigned_to, assigned_team, alert_id))

            # Audit record
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_ASN_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, assigned_by, "CASE_ASSIGNED", now_iso,
                json.dumps({"alert_id": alert_id, "assigned_to": assigned_to, "assigned_team": assigned_team})
            ))
            conn.commit()

        return self.get_alert_by_id(alert_id)

    def escalate_alert(self, alert_id: str, reason: str, requested_by: str, target_role: UserRole = UserRole.SUPERVISOR) -> Alert:
        """Escalate alert to supervisor or LEA authority."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_id, priority FROM operational_alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Alert {alert_id} not found")

            case_id = row["case_id"]
            cursor.execute("""
            UPDATE operational_alerts
            SET status = ?, priority = 'P1'
            WHERE alert_id = ?;
            """, (CaseStatus.ESCALATED.value, alert_id))

            # Escalation record
            esc_id = f"ESC_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
            cursor.execute("""
            INSERT INTO escalations (
                escalation_id, case_id, reason, priority, requested_by, requested_at, status, target_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (esc_id, case_id, reason, "P1", requested_by, now_iso, "PENDING", target_role.value))

            # Audit record
            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_ESC_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, requested_by, "CASE_ESCALATED", now_iso,
                json.dumps({"alert_id": alert_id, "escalation_id": esc_id, "reason": reason, "target_role": target_role.value})
            ))
            conn.commit()

        return self.get_alert_by_id(alert_id)

    def close_alert(self, alert_id: str, closed_by: str, reason: str) -> Alert:
        """Close an alert."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_id FROM operational_alerts WHERE alert_id = ?", (alert_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Alert {alert_id} not found")

            case_id = row["case_id"]
            cursor.execute("""
            UPDATE operational_alerts
            SET status = ?, closed_at = ?
            WHERE alert_id = ?;
            """, (CaseStatus.CLOSED.value, now_iso, alert_id))

            cursor.execute("""
            INSERT INTO audit_trail (event_id, case_id, actor, action, timestamp, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (
                f"AUD_CLS_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                case_id, closed_by, "CASE_CLOSED", now_iso,
                json.dumps({"alert_id": alert_id, "reason": reason})
            ))
            conn.commit()

        return self.get_alert_by_id(alert_id)

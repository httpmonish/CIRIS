"""
Alert Service for CIRIS Productization.

Manages alert creation, priority assignment (P1-P4), status workflow
(NEW, ACKNOWLEDGED, ASSIGNED, ESCALATED, CLOSED), and officer assignment.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.db.models import AlertModel, CaseEventModel


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def list_alerts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Tuple[List[AlertModel], int]:
        """Query paginated alerts with filters."""
        query = self.db.query(AlertModel)

        if status:
            query = query.filter(AlertModel.status == status.upper())
        if priority:
            query = query.filter(AlertModel.priority == priority.upper())
        if assigned_to:
            query = query.filter(AlertModel.assigned_to == assigned_to)

        total_count = query.count()
        offset = (page - 1) * page_size
        items = query.order_by(desc(AlertModel.created_at)).offset(offset).limit(page_size).all()
        return items, total_count

    def acknowledge_alert(self, alert_id: str, actor: str = "INVESTIGATOR") -> Optional[AlertModel]:
        """Mark alert as ACKNOWLEDGED and add audit log."""
        alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
        if not alert:
            return None

        alert.status = "ACKNOWLEDGED"
        self._log_alert_event(alert.case_id, "ALERT_ACKNOWLEDGED", actor, f"Alert {alert_id} acknowledged by {actor}")
        self.db.commit()
        return alert

    def assign_alert(self, alert_id: str, assigned_to: str, actor: str = "ADMIN") -> Optional[AlertModel]:
        """Assign alert to an investigator or bank analyst."""
        alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
        if not alert:
            return None

        alert.assigned_to = assigned_to
        alert.status = "ASSIGNED"
        self._log_alert_event(alert.case_id, "ALERT_ASSIGNED", actor, f"Alert {alert_id} assigned to {assigned_to}")
        self.db.commit()
        return alert

    def escalate_alert(self, alert_id: str, actor: str = "INVESTIGATOR", reason: str = "") -> Optional[AlertModel]:
        """Escalate alert priority and trigger escalation audit log."""
        alert = self.db.query(AlertModel).filter(AlertModel.alert_id == alert_id).first()
        if not alert:
            return None

        alert.status = "ESCALATED"
        alert.priority = "P1"
        self._log_alert_event(alert.case_id, "ALERT_ESCALATED", actor, f"Alert {alert_id} escalated to P1. Reason: {reason}")
        self.db.commit()
        return alert

    def _log_alert_event(self, case_id: str, event_type: str, actor: str, description: str):
        import uuid
        ev = CaseEventModel(
            event_id=f"EVT-{uuid.uuid4().hex[:8]}",
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            description=description,
            source="ALERT_SERVICE",
            timestamp=datetime.utcnow(),
        )
        self.db.add(ev)

"""
Complaints RBAC API Router.
Enforces Dynamic Row-Level Security:
- Citizens: Can only view & submit their personal complaints.
- Bank Officials: Can only view & manage complaints for their specific bank + escalate to LEA.
- Government Officials: Global oversight over all complaints, banks, and interstate corridors.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from src.db.database import create_connection
from src.security.auth import get_current_user, RequireRole, UserRole, UserSession

logger = logging.getLogger("ciris.api.complaints_rbac")
router = APIRouter(prefix="/complaints", tags=["Complaints & Incident Interception"])


class CreateComplaintRequest(BaseModel):
    target_bank_id: str
    disputed_amount: float = Field(..., gt=0)
    transaction_rrn: str
    fraud_type: str
    victim_city: str
    evidence_notes: Optional[str] = None
    incident_timestamp: Optional[str] = None


class BankActionRequest(BaseModel):
    action_type: str  # ACCOUNT_FROZEN, UNDER_REVIEW, RESOLVED, REJECTED
    notes: Optional[str] = None


class LEAEscalationRequest(BaseModel):
    lea_jurisdiction: str
    escalation_reason: str


# -----------------------------------------------------------------------------
# 1. GET / - Dynamic Row-Level Security Complaints List
# -----------------------------------------------------------------------------
@router.get("/", response_model=List[Dict[str, Any]])
def list_complaints(current_user: UserSession = Depends(get_current_user)):
    """
    Returns complaints based on strict RBAC filtering:
    - CITIZEN: Only complaints filed by the current citizen.
    - BANK_OFFICIAL: Only complaints assigned to the official's specific bank.
    - GOVT_OFFICIAL: Global access to all complaints across India.
    """
    conn = create_connection()
    try:
        cursor = conn.cursor()
        query = """
            SELECT c.id, c.complaint_number, c.citizen_id, c.target_bank_id, c.disputed_amount,
                   c.transaction_rrn, c.fraud_type, c.status, c.victim_city, c.evidence_notes,
                   c.incident_timestamp, c.created_at,
                   u.full_name AS citizen_name, u.email AS citizen_email, u.phone_number AS citizen_phone,
                   b.name AS target_bank_name
            FROM citizen_complaints c
            JOIN auth_users u ON c.citizen_id = u.id
            JOIN auth_banks b ON c.target_bank_id = b.id
        """
        params = []

        if current_user.role == UserRole.CITIZEN:
            query += " WHERE c.citizen_id = ?"
            params.append(current_user.id)
        elif current_user.role == UserRole.BANK_OFFICIAL:
            query += " WHERE c.target_bank_id = ?"
            params.append(current_user.bank_id)
        elif current_user.role == UserRole.GOVT_OFFICIAL:
            # Global view: no where clause constraint
            pass

        query += " ORDER BY c.created_at DESC;"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 2. POST / - Citizen-Only Complaint Submission
# -----------------------------------------------------------------------------
@router.post("/", status_code=status.HTTP_201_CREATED)
def submit_new_complaint(
    payload: CreateComplaintRequest,
    citizen: UserSession = Depends(RequireRole([UserRole.CITIZEN]))
):
    """Allows authenticated citizens to register a new cybercrime financial dispute."""
    conn = create_connection()
    try:
        cursor = conn.cursor()

        # Verify bank exists
        cursor.execute("SELECT name FROM auth_banks WHERE id = ? AND is_active = 1;", (payload.target_bank_id,))
        b_row = cursor.fetchone()
        if not b_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid target_bank_id.")

        complaint_id = f"CMP_{uuid.uuid4().hex[:8].upper()}"
        complaint_num = f"NCRP-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        incident_ts = payload.incident_timestamp or now

        cursor.execute("""
            INSERT INTO citizen_complaints (
                id, complaint_number, citizen_id, target_bank_id, disputed_amount,
                transaction_rrn, fraud_type, status, victim_city, evidence_notes,
                incident_timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?);
        """, (
            complaint_id,
            complaint_num,
            citizen.id,
            payload.target_bank_id,
            payload.disputed_amount,
            payload.transaction_rrn.strip(),
            payload.fraud_type,
            payload.victim_city.strip(),
            payload.evidence_notes,
            incident_ts,
            now
        ))

        # Log initial action
        cursor.execute("""
            INSERT INTO complaint_actions (id, complaint_id, actor_id, actor_role, action_type, notes, timestamp)
            VALUES (?, ?, ?, ?, 'COMPLAINT_FILED', 'Complaint submitted via Citizen Portal', ?);
        """, (f"ACT_{uuid.uuid4().hex[:8]}", complaint_id, citizen.id, citizen.role.value, now))

        conn.commit()

        return {
            "status": "SUCCESS",
            "complaint_id": complaint_id,
            "complaint_number": complaint_num,
            "target_bank": b_row["name"],
            "disputed_amount": payload.disputed_amount,
            "created_at": now
        }
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 3. POST /{id}/action - Bank Official Internal Action
# -----------------------------------------------------------------------------
@router.post("/{complaint_id}/action")
def bank_take_internal_action(
    complaint_id: str,
    payload: BankActionRequest,
    bank_official: UserSession = Depends(RequireRole([UserRole.BANK_OFFICIAL, UserRole.GOVT_OFFICIAL]))
):
    """Allows Bank Officials to take action on complaints belonging strictly to their bank."""
    conn = create_connection()
    try:
        cursor = conn.cursor()

        # Enforce Bank Data Isolation
        if bank_official.role == UserRole.BANK_OFFICIAL:
            cursor.execute("SELECT id, status, target_bank_id FROM citizen_complaints WHERE id = ? AND target_bank_id = ?;", (complaint_id, bank_official.bank_id))
        else:
            cursor.execute("SELECT id, status, target_bank_id FROM citizen_complaints WHERE id = ?;", (complaint_id,))

        complaint = cursor.fetchone()
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found or belongs to another banking institution."
            )

        now = datetime.now(timezone.utc).isoformat()
        new_status = payload.action_type if payload.action_type in ['ACCOUNT_FROZEN', 'UNDER_REVIEW', 'RESOLVED', 'REJECTED'] else 'UNDER_REVIEW'

        cursor.execute("UPDATE citizen_complaints SET status = ? WHERE id = ?;", (new_status, complaint_id))

        # Append to audit history
        cursor.execute("""
            INSERT INTO complaint_actions (id, complaint_id, actor_id, actor_role, action_type, notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (f"ACT_{uuid.uuid4().hex[:8]}", complaint_id, bank_official.id, bank_official.role.value, payload.action_type, payload.notes, now))

        conn.commit()

        return {
            "status": "SUCCESS",
            "complaint_id": complaint_id,
            "updated_status": new_status,
            "action_by": bank_official.full_name,
            "timestamp": now
        }
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 4. POST /{id}/escalate - Bank Official LEA Escalation
# -----------------------------------------------------------------------------
@router.post("/{complaint_id}/escalate")
def escalate_complaint_to_lea(
    complaint_id: str,
    payload: LEAEscalationRequest,
    bank_official: UserSession = Depends(RequireRole([UserRole.BANK_OFFICIAL, UserRole.GOVT_OFFICIAL]))
):
    """Directly escalates a high-risk complaint to Law Enforcement Agencies (LEA / I4C)."""
    conn = create_connection()
    try:
        cursor = conn.cursor()

        if bank_official.role == UserRole.BANK_OFFICIAL:
            cursor.execute("SELECT id, complaint_number, target_bank_id FROM citizen_complaints WHERE id = ? AND target_bank_id = ?;", (complaint_id, bank_official.bank_id))
        else:
            cursor.execute("SELECT id, complaint_number, target_bank_id FROM citizen_complaints WHERE id = ?;", (complaint_id,))

        complaint = cursor.fetchone()
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found or unauthorized."
            )

        now = datetime.now(timezone.utc).isoformat()
        escalation_id = f"LEA_ESC_{uuid.uuid4().hex[:8].upper()}"

        cursor.execute("UPDATE citizen_complaints SET status = 'ESCALATED_LEA' WHERE id = ?;", (complaint_id,))

        cursor.execute("""
            INSERT INTO lea_escalations (id, complaint_id, bank_official_id, lea_jurisdiction, escalation_reason, escalated_at)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (escalation_id, complaint_id, bank_official.id, payload.lea_jurisdiction, payload.escalation_reason, now))

        cursor.execute("""
            INSERT INTO complaint_actions (id, complaint_id, actor_id, actor_role, action_type, notes, timestamp)
            VALUES (?, ?, ?, ?, 'ESCALATED_TO_LEA', ?, ?);
        """, (f"ACT_{uuid.uuid4().hex[:8]}", complaint_id, bank_official.id, bank_official.role.value, f"Escalated to {payload.lea_jurisdiction}: {payload.escalation_reason}", now))

        conn.commit()

        return {
            "status": "ESCALATED_TO_LAW_ENFORCEMENT",
            "escalation_id": escalation_id,
            "complaint_number": complaint["complaint_number"],
            "lea_jurisdiction": payload.lea_jurisdiction,
            "escalated_at": now
        }
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# 5. GET /overview/govt - Government Official Central Metrics
# -----------------------------------------------------------------------------
@router.get("/overview/govt")
def get_govt_central_overview(govt_user: UserSession = Depends(RequireRole([UserRole.GOVT_OFFICIAL]))):
    """Returns nationwide cybercrime complaint metrics for Government Super Admins."""
    conn = create_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) AS total FROM citizen_complaints;")
        total_complaints = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM citizen_complaints WHERE status = 'ESCALATED_LEA';")
        total_escalated = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM citizen_complaints WHERE status = 'ACCOUNT_FROZEN';")
        total_frozen = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM auth_banks WHERE is_active = 1;")
        total_banks = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM auth_users WHERE role = 'CITIZEN';")
        total_citizens = cursor.fetchone()["total"]

        return {
            "officer_name": govt_user.full_name,
            "badge_id": govt_user.govt_badge_id,
            "total_complaints": total_complaints,
            "total_escalated_lea": total_escalated,
            "total_mule_frozen": total_frozen,
            "monitored_banks": total_banks,
            "registered_citizens": total_citizens
        }
    finally:
        conn.close()

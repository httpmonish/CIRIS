"""
CIRIS Phase 4 — Operational Domain Models, Enums & PII Masking Utilities.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class AlertType(str, Enum):
    ATM_CASHOUT_RISK = "ATM_CASHOUT_RISK"
    MULE_NETWORK = "MULE_NETWORK"
    FRAGMENTATION = "FRAGMENTATION"
    HIGH_RISK_MONEY_FLOW = "HIGH_RISK_MONEY_FLOW"
    CROSS_CASE_NETWORK = "CROSS_CASE_NETWORK"
    ENDPOINT_RISK = "ENDPOINT_RISK"
    COMBINED_CASE_RISK = "COMBINED_CASE_RISK"


class PriorityLevel(str, Enum):
    P1 = "P1"  # Immediate / high-risk potential intervention
    P2 = "P2"  # High-risk investigation
    P3 = "P3"  # Requires review
    P4 = "P4"  # Monitor / informational


class SeverityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CaseStatus(str, Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class EvidenceCategory(str, Enum):
    TRANSACTION = "TRANSACTION"
    GRAPH = "GRAPH"
    ENTITY = "ENTITY"
    GEOGRAPHIC = "GEOGRAPHIC"
    HISTORICAL = "HISTORICAL"
    BEHAVIOURAL = "BEHAVIOURAL"
    MODEL = "MODEL"
    CASE = "CASE"


class InterventionRecommendation(str, Enum):
    HOLD_REVIEW = "HOLD_REVIEW"
    MONITOR = "MONITOR"
    INVESTIGATE = "INVESTIGATE"
    ESCALATE = "ESCALATE"


class InvestigatorOutcome(str, Enum):
    CONFIRMED = "CONFIRMED"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    ESCALATED = "ESCALATED"


class UserRole(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"
    SUPERVISOR = "SUPERVISOR"
    BANK_ANALYST = "BANK_ANALYST"
    LEA_OFFICER = "LEA_OFFICER"
    I4C_ANALYST = "I4C_ANALYST"
    ADMIN = "ADMIN"


# ============================================================================
# PII Masking Utilities
# ============================================================================

def mask_account_id(acc_id: Optional[str]) -> str:
    """Mask account identifier e.g., ACC_035263 -> ACC_03••63"""
    if not acc_id:
        return "UNKNOWN_ACCOUNT"
    acc_str = str(acc_id).strip()
    if len(acc_str) <= 6:
        return acc_str[:2] + "••" + acc_str[-2:] if len(acc_str) >= 4 else "••"
    prefix = acc_str[:6]
    suffix = acc_str[-2:]
    return f"{prefix}••{suffix}"


def mask_phone_number(phone: Optional[str]) -> str:
    """Mask phone numbers e.g., 9876543210 -> 98••••••10"""
    if not phone:
        return "••••••••••"
    clean = re.sub(r"\D", "", str(phone))
    if len(clean) >= 10:
        return f"{clean[:2]}••••••{clean[-2:]}"
    return "••••••••••"


def mask_upi_id(upi: Optional[str]) -> str:
    """Mask UPI identifier e.g., user123@okaxis -> u•••3@okaxis"""
    if not upi or "@" not in upi:
        return str(upi) if upi else "UNKNOWN_UPI"
    user, handle = upi.split("@", 1)
    if len(user) <= 2:
        masked_user = "••"
    else:
        masked_user = f"{user[0]}•••{user[-1]}"
    return f"{masked_user}@{handle}"


# ============================================================================
# Alert Models
# ============================================================================

class Alert(BaseModel):
    alert_id: str
    case_id: str
    created_at: str
    prediction_timestamp: Optional[str] = None
    alert_type: AlertType
    priority: PriorityLevel
    severity: SeverityLevel
    risk_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    endpoint_type: str = "ATM"
    predicted_endpoint_id: Optional[str] = None
    amount_at_risk: float = Field(default=0.0, ge=0.0)
    status: CaseStatus = CaseStatus.NEW
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    source: str = "CIRIS_INTELLIGENCE"
    evidence_summary: Optional[str] = None
    dedup_hash: Optional[str] = None
    sla_deadline: Optional[str] = None
    acknowledged_at: Optional[str] = None
    first_reviewed_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(..., description="User ID / badge number")
    notes: Optional[str] = None


class AlertAssignRequest(BaseModel):
    assigned_to: str = Field(..., description="Investigator ID")
    assigned_team: Optional[str] = Field(None, description="LEA unit / Cyber Cell team")
    assigned_by: str = Field(..., description="Supervisor / Dispatcher ID")
    notes: Optional[str] = None


class AlertEscalateRequest(BaseModel):
    reason: str = Field(..., min_length=5)
    target_role: UserRole = UserRole.SUPERVISOR
    requested_by: str = Field(..., description="Investigator ID")
    priority: PriorityLevel = PriorityLevel.P1


# ============================================================================
# Case Lifecycle Models
# ============================================================================

class CaseLifecycleRecord(BaseModel):
    case_id: str
    complaint_id: str
    priority: PriorityLevel
    status: CaseStatus
    owner: Optional[str] = None
    team: Optional[str] = None
    risk_score: float = 0.0
    amount_at_risk: float = 0.0
    endpoint_type: str = "UNKNOWN"
    predicted_endpoint_id: Optional[str] = None
    summary: Optional[str] = None
    created_at: str
    updated_at: str
    sla_deadline: Optional[str] = None
    acknowledged_at: Optional[str] = None
    assigned_at: Optional[str] = None
    first_review_at: Optional[str] = None
    resolved_at: Optional[str] = None
    closed_at: Optional[str] = None
    resolution_outcome: Optional[InvestigatorOutcome] = None


class CaseAssignRequest(BaseModel):
    owner: str = Field(..., description="Investigator ID")
    team: Optional[str] = Field(None, description="LEA Team e.g. 'Mumbai Cyber Crime Cell'")
    assigned_by: str = Field(..., description="Assigner ID")
    notes: Optional[str] = None


class CaseStatusTransitionRequest(BaseModel):
    target_status: CaseStatus
    actor: str
    notes: Optional[str] = None
    resolution_outcome: Optional[InvestigatorOutcome] = None


class CaseNoteCreateRequest(BaseModel):
    author: str
    content: str = Field(..., min_length=2)
    visibility: Literal["INTERNAL", "PUBLIC", "RESTRICTED"] = "INTERNAL"


class CaseNote(BaseModel):
    note_id: str
    case_id: str
    author: str
    created_at: str
    content: str
    visibility: str = "INTERNAL"


class InvestigatorFeedbackCreateRequest(BaseModel):
    investigator_id: str
    outcome: InvestigatorOutcome
    notes: Optional[str] = None
    actual_cashout_atm_id: Optional[str] = None
    actual_loss_recovered: float = Field(default=0.0, ge=0.0)


# ============================================================================
# Evidence Models
# ============================================================================

class EvidenceItem(BaseModel):
    evidence_id: str
    case_id: str
    category: EvidenceCategory
    title: str
    description: str
    source: str
    timestamp: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    reference_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Intervention Models
# ============================================================================

class InterventionRecord(BaseModel):
    intervention_id: str
    case_id: str
    recommendation: InterventionRecommendation
    reason: str
    evidence_ids: List[str]
    authorization_boundary: str
    generated_at: str
    status: str = "PENDING_REVIEW"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None


class InterventionReviewRequest(BaseModel):
    reviewer: str
    action: Literal["ACCEPT", "REJECT", "ESCALATE"]
    notes: Optional[str] = None


# ============================================================================
# Audit Trail Models
# ============================================================================

class AuditEvent(BaseModel):
    event_id: str
    case_id: Optional[str] = None
    actor: str
    action: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Investigation Workspace Aggregate Models
# ============================================================================

class MoneyFlowHop(BaseModel):
    edge_id: str
    from_account: str  # Masked
    to_account: str    # Masked
    amount: float
    channel: str
    timestamp: str
    hop_level: int
    is_cashout_endpoint: bool = False
    source_coordinates: Optional[List[float]] = None  # [lon, lat]
    dest_coordinates: Optional[List[float]] = None    # [lon, lat]


class EntityProfile(BaseModel):
    entity_id: str
    entity_type: str
    masked_name: str
    category: Optional[str] = None
    risk_score: float
    linked_case_count: int
    linked_account_count: int
    total_volume: float
    city: Optional[str] = None
    state: Optional[str] = None


class NetworkInvestigationResponse(BaseModel):
    cluster_id: str
    hop_depth: int
    node_count: int
    edge_count: int
    total_network_volume: float
    active_mule_candidates: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    evidence: List[EvidenceItem]


class CaseInvestigationWorkspace(BaseModel):
    case_id: str
    complaint_id: str
    status: CaseStatus
    priority: PriorityLevel
    risk_score: float
    urgency_score: float
    confidence: float
    amount_at_risk: float
    reported_loss_amount: float
    fraud_type: str
    incident_timestamp: Optional[str] = None
    complaint_timestamp: Optional[str] = None
    victim_location: Dict[str, Any]
    assigned_owner: Optional[str] = None
    assigned_team: Optional[str] = None
    executive_summary: str
    reasons_why: List[str]
    timeline: List[Dict[str, Any]]
    evidence_chain: List[EvidenceItem]
    predicted_endpoints: List[Dict[str, Any]]
    money_flow_network: Dict[str, Any]
    related_entities: List[EntityProfile]
    related_cases: List[Dict[str, Any]]
    intervention_recommendation: InterventionRecord
    active_alerts: List[Alert]
    notes: List[CaseNote]
    audit_events: List[AuditEvent]
    sla_metrics: Dict[str, Any]


class QueueItem(BaseModel):
    case_id: str
    complaint_id: str
    priority: PriorityLevel
    status: CaseStatus
    risk_score: float
    amount_at_risk: float
    fraud_type: str
    endpoint_type: str
    predicted_endpoint: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    age_hours: float
    sla_status: Literal["WITHIN_SLA", "WARNING", "BREACHED"]
    created_at: str
    sla_deadline: Optional[str] = None


class InvestigationQueueResponse(BaseModel):
    total_cases: int
    page: int
    page_size: int
    items: List[QueueItem]


class OperationalSummaryResponse(BaseModel):
    active_cases: int
    critical_cases_p1: int
    high_risk_cases_p2: int
    medium_cases_p3: int
    low_cases_p4: int
    alerts_today: int
    total_amount_at_risk: float
    active_mule_networks: int
    predicted_atm_interceptions: int
    avg_acknowledgement_time_minutes: float
    avg_resolution_time_hours: float
    sla_compliance_percentage: float

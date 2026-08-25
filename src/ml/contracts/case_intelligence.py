"""
Case Intelligence Object and Data Contracts for CIRIS.

Defines the unified Case Intelligence schema encapsulating fraud complaint,
entity resolution, money-flow graph paths, mule candidate risk, amount at risk,
endpoint type predictions, and investigator intervention recommendations.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AmountAtRiskSummary(BaseModel):
    disputed_amount: float = 0.0
    observed_moved_amount: float = 0.0
    observed_remaining_amount: float = 0.0
    unresolved_amount: float = 0.0
    hold_review_recommended_amount: float = 0.0


class MuleEntityCandidate(BaseModel):
    entity_id: str
    account_id: str
    mule_risk_score: float = 0.0
    confidence: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    evidence_tags: List[str] = Field(default_factory=list)
    cluster_size: int = 1
    degree_centrality: int = 0
    rapid_in_out_ratio: float = 0.0
    is_unflagged_related: bool = True


class MoneyFlowPath(BaseModel):
    path_id: str
    nodes: List[str] = Field(default_factory=list)  # e.g., ["ACC_001", "ACC_002", "ATM_0234"]
    total_amount_flow: float = 0.0
    hop_count: int = 1
    flow_duration_minutes: float = 0.0
    endpoint_type: str = "ATM"  # ATM, MERCHANT, TRANSFER


class EndpointPrediction(BaseModel):
    endpoint_type: str = "ATM"  # ATM, MERCHANT, TRANSFER
    endpoint_id: str
    endpoint_name: str = ""
    location_details: Dict[str, Any] = Field(default_factory=dict)
    probability: float = 0.0
    predicted_time_window: str = "3-6h"
    predicted_delay_hours: float = 0.0
    fused_risk_score: float = 0.0
    evidence_attributions: List[Dict[str, Any]] = Field(default_factory=list)


class InterventionRecommendation(BaseModel):
    recommended_action: str = "INVESTIGATE"  # HOLD REVIEW, MONITOR, INVESTIGATE, ESCALATE
    confidence_score: float = 0.0
    action_rationale: str = ""
    potential_hold_amount: float = 0.0
    authorization_boundary: str = "Authorized Bank / LEA Officer Review Required"
    target_accounts_for_review: List[str] = Field(default_factory=list)


class CaseIntelligenceObject(BaseModel):
    case_id: str
    victim_id: str = "UNKNOWN"
    complaint_timestamp: datetime = Field(default_factory=datetime.now)
    disputed_amount: float = 0.0
    fraud_type: str = "Unknown"
    known_suspicious_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    connected_entities: List[Dict[str, Any]] = Field(default_factory=list)
    money_flow_paths: List[MoneyFlowPath] = Field(default_factory=list)
    mule_candidates: List[MuleEntityCandidate] = Field(default_factory=list)
    amount_at_risk: AmountAtRiskSummary = Field(default_factory=AmountAtRiskSummary)
    potential_endpoints: List[EndpointPrediction] = Field(default_factory=list)
    overall_case_risk: float = 0.0
    overall_confidence: float = 0.0
    top_evidence: List[str] = Field(default_factory=list)
    related_cases: List[str] = Field(default_factory=list)
    intervention_recommendation: InterventionRecommendation = Field(default_factory=InterventionRecommendation)
    xai_narrative_briefing: str = ""

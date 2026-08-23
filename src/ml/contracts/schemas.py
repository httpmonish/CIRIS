"""
Data Contracts and Schema Definitions for CIPHER-X v4.

Defines Pydantic schemas and typed data structures for complaints, ATMs,
transactions, graph entities, candidate sets, and intelligence outputs.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class VictimLocation(BaseModel):
    state: str = "Unknown"
    district: str = "Unknown"
    city: str = "Unknown"
    area: str = "Unknown"
    pincode: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    rural_urban: str = "Urban"

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def sanitize_float(cls, v):
        if v is None or v == "":
            return 0.0
        return float(v)

    @field_validator("pincode", mode="before")
    @classmethod
    def sanitize_int(cls, v):
        if v is None or v == "":
            return 0
        return int(float(v))


class ComplaintPayload(BaseModel):
    complaint_id: str
    complaint_timestamp: datetime = Field(default_factory=datetime.now)
    incident_timestamp: Optional[datetime] = None
    fraud_type: str = "Unknown"
    channel: str = "Unknown"
    reported_loss_amount: float = 0.0
    victim_location: VictimLocation
    victim_bank: str = "Unknown"
    device_type: str = "Unknown"
    is_otp_shared: int = 0
    clicked_malicious_link: int = 0
    urgency_score: float = 0.5
    account_age_months: int = 0
    num_transactions: int = 1
    fraud_description_category: str = "Unknown"

    @field_validator("reported_loss_amount", "urgency_score", mode="before")
    @classmethod
    def sanitize_float(cls, v):
        if v is None or v == "":
            return 0.0
        return float(v)

    @field_validator("is_otp_shared", "clicked_malicious_link", "account_age_months", "num_transactions", mode="before")
    @classmethod
    def sanitize_int(cls, v):
        if v is None or v == "":
            return 0
        return int(float(v))

    @field_validator("complaint_timestamp", "incident_timestamp", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str) and v.strip():
            return datetime.fromisoformat(v.strip())
        return datetime.now()


class ATMMasterRecord(BaseModel):
    atm_id: str
    atm_name: str
    bank_name: str
    state: str = "Unknown"
    district: str = "Unknown"
    city: str = "Unknown"
    area: str = "Unknown"
    pincode: int = 0
    latitude: float
    longitude: float
    location_type: str = "Standalone ATM"

    @field_validator("latitude", "longitude", mode="before")
    @classmethod
    def sanitize_float(cls, v):
        return float(v)

    @field_validator("pincode", mode="before")
    @classmethod
    def sanitize_int(cls, v):
        if v is None or v == "":
            return 0
        return int(float(v))


class CandidateATM(BaseModel):
    atm_id: str
    atm_name: str
    bank_name: str
    latitude: float
    longitude: float
    distance_km: float
    location_type: str
    city: str
    district: str
    retrieval_sources: List[str] = Field(default_factory=list)


class FeatureVector(BaseModel):
    complaint_id: str
    atm_id: str
    features: Dict[str, float]


class SubScores(BaseModel):
    location_score: float
    time_score: float
    anomaly_score: float
    historical_score: float


class ATMRiskPrediction(BaseModel):
    rank: int
    atm_id: str
    atm_name: str
    bank_name: str
    city: str
    district: str
    latitude: float
    longitude: float
    distance_km: float
    sub_scores: SubScores
    fused_risk_score: float
    calibrated_probability: float
    predicted_time_window: str
    predicted_delay_hours: float
    confidence_tier: str  # "HIGH", "MEDIUM", "LOW"
    action_required: str
    shap_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    graph_evidence: Dict[str, Any] = Field(default_factory=dict)


class IntelligenceReport(BaseModel):
    complaint_id: str
    prediction_timestamp: datetime
    total_candidates_evaluated: int
    top_candidates: List[ATMRiskPrediction]
    highest_risk_atm: Optional[ATMRiskPrediction]
    alert_status: str  # "DISPATCH_ALERT" or "MONITOR_HOLD"
    connected_entities: Dict[str, Any] = Field(default_factory=dict)

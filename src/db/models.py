"""
SQLAlchemy ORM Models for CIRIS Operational Database.

Supports PostgreSQL + PostGIS (with standard float fallback for SQLite).
Defines operational schemas for cases, entities, accounts, cards, UPI IDs,
mobiles, devices, transactions, graph edges, withdrawals, ATMs, merchants,
predictions, alerts, audit events, evidence, and interventions.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CaseModel(Base):
    __tablename__ = "cases"

    case_id = Column(String(64), primary_key=True, index=True)
    complaint_id = Column(String(64), unique=True, index=True, nullable=False)
    victim_entity_id = Column(String(64), nullable=True)
    complaint_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    reported_loss_amount = Column(Float, default=0.0)
    fraud_type = Column(String(128), default="Unknown", index=True)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    state = Column(String(64), default="Unknown")
    district = Column(String(64), default="Unknown")
    city = Column(String(64), default="Unknown")
    status = Column(String(32), default="NEW", index=True)  # NEW, ANALYZING, REVIEW, ESCALATED, RESOLVED, CLOSED
    priority = Column(String(16), default="P2", index=True)  # P1, P2, P3, P4
    overall_risk_score = Column(Float, default=0.0)
    overall_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    predictions = relationship("PredictionModel", back_populates="case", cascade="all, delete-orphan")
    alerts = relationship("AlertModel", back_populates="case", cascade="all, delete-orphan")
    case_events = relationship("CaseEventModel", back_populates="case", cascade="all, delete-orphan")
    evidence = relationship("EvidenceModel", back_populates="case", cascade="all, delete-orphan")
    interventions = relationship("InterventionModel", back_populates="case", cascade="all, delete-orphan")


class EntityModel(Base):
    __tablename__ = "entities"

    entity_id = Column(String(64), primary_key=True, index=True)
    entity_type = Column(String(64), default="SUSPECT", index=True)  # VICTIM, SUSPECT, MULE_CANDIDATE, MERCHANT
    risk_score = Column(Float, default=0.0, index=True)
    mule_candidate = Column(Boolean, default=False, index=True)
    cluster_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, default=dict)

    # Relationships
    accounts = relationship("AccountModel", back_populates="entity")
    cards = relationship("CardModel", back_populates="entity")
    upis = relationship("UPIModel", back_populates="entity")
    mobiles = relationship("MobileModel", back_populates="entity")
    devices = relationship("DeviceModel", back_populates="entity")


class AccountModel(Base):
    __tablename__ = "accounts"

    account_id = Column(String(64), primary_key=True, index=True)
    entity_id = Column(String(64), ForeignKey("entities.entity_id"), nullable=True, index=True)
    bank_name = Column(String(128), default="Unknown")
    account_number_hash = Column(String(128), nullable=True)
    account_type = Column(String(32), default="SAVINGS")
    risk_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("EntityModel", back_populates="accounts")


class CardModel(Base):
    __tablename__ = "cards"

    card_id = Column(String(64), primary_key=True, index=True)
    entity_id = Column(String(64), ForeignKey("entities.entity_id"), nullable=True, index=True)
    card_type = Column(String(32), default="DEBIT")
    bank_name = Column(String(128), default="Unknown")
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("EntityModel", back_populates="cards")


class UPIModel(Base):
    __tablename__ = "upi_identifiers"

    upi_id = Column(String(128), primary_key=True, index=True)
    entity_id = Column(String(64), ForeignKey("entities.entity_id"), nullable=True, index=True)
    handle = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("EntityModel", back_populates="upis")


class MobileModel(Base):
    __tablename__ = "mobile_identifiers"

    mobile_id = Column(String(64), primary_key=True, index=True)
    entity_id = Column(String(64), ForeignKey("entities.entity_id"), nullable=True, index=True)
    telecom_operator = Column(String(64), default="Unknown")
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("EntityModel", back_populates="mobiles")


class DeviceModel(Base):
    __tablename__ = "devices"

    device_id = Column(String(64), primary_key=True, index=True)
    entity_id = Column(String(64), ForeignKey("entities.entity_id"), nullable=True, index=True)
    device_type = Column(String(64), default="Mobile")
    os_name = Column(String(64), default="Android")
    created_at = Column(DateTime, default=datetime.utcnow)

    entity = relationship("EntityModel", back_populates="devices")


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=True, index=True)
    source_account_id = Column(String(64), index=True)
    destination_account_id = Column(String(64), index=True)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    transaction_type = Column(String(32), default="IMPS", index=True)  # UPI, IMPS, NEFT, RTGS, ATM_WITHDRAWAL
    risk_score = Column(Float, default=0.0)
    metadata_json = Column(JSON, default=dict)


class GraphEdgeModel(Base):
    __tablename__ = "graph_edges"

    edge_id = Column(String(64), primary_key=True, index=True)
    source_node = Column(String(64), nullable=False, index=True)
    target_node = Column(String(64), nullable=False, index=True)
    relation_type = Column(String(32), default="TRANSFERRED_TO", index=True)
    weight_amount = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    case_id = Column(String(64), nullable=True, index=True)


class WithdrawalModel(Base):
    __tablename__ = "withdrawals"

    withdrawal_id = Column(String(64), primary_key=True, index=True)
    atm_id = Column(String(64), index=True, nullable=False)
    account_id = Column(String(64), index=True, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    is_fraud_linked = Column(Boolean, default=False, index=True)


class ATMModel(Base):
    __tablename__ = "atms"

    atm_id = Column(String(64), primary_key=True, index=True)
    atm_name = Column(String(256), nullable=False)
    bank_name = Column(String(128), nullable=False, index=True)
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    city = Column(String(64), default="Unknown", index=True)
    district = Column(String(64), default="Unknown", index=True)
    state = Column(String(64), default="Unknown", index=True)
    pincode = Column(Integer, default=0)
    location_type = Column(String(64), default="Standalone ATM")
    historical_risk_score = Column(Float, default=0.0)


class MerchantModel(Base):
    __tablename__ = "merchants"

    merchant_id = Column(String(64), primary_key=True, index=True)
    merchant_name = Column(String(256), nullable=False)
    category = Column(String(128), default="Retail")
    city = Column(String(64), default="Unknown")
    district = Column(String(64), default="Unknown")
    state = Column(String(64), default="Unknown")
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)


class PredictionModel(Base):
    __tablename__ = "predictions"

    prediction_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    endpoint_type = Column(String(32), default="ATM", index=True)  # ATM, MERCHANT, TRANSFER, UNKNOWN
    target_id = Column(String(64), nullable=False, index=True)
    target_name = Column(String(256), default="")
    rank = Column(Integer, default=1)
    score = Column(Float, default=0.0)
    confidence = Column(Float, default=0.0)
    confidence_tier = Column(String(16), default="MEDIUM")  # HIGH, MEDIUM, LOW
    predicted_time_window = Column(String(32), default="3-6h")
    predicted_delay_hours = Column(Float, default=0.0)
    latitude = Column(Float, default=0.0)
    longitude = Column(Float, default=0.0)
    evidence_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    case = relationship("CaseModel", back_populates="predictions")


class AlertModel(Base):
    __tablename__ = "alerts"

    alert_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    priority = Column(String(16), default="P2", index=True)  # P1, P2, P3, P4
    risk_score = Column(Float, default=0.0, index=True)
    confidence = Column(Float, default=0.0)
    endpoint_summary = Column(String(256), default="ATM Prediction Alert")
    amount = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(32), default="NEW", index=True)  # NEW, ACKNOWLEDGED, ASSIGNED, ESCALATED, CLOSED
    assigned_to = Column(String(128), nullable=True, index=True)

    case = relationship("CaseModel", back_populates="alerts")


class CaseEventModel(Base):
    __tablename__ = "case_events"

    event_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)  # CASE_CREATED, ANALYSIS_COMPLETED, ALERT_CREATED, etc.
    actor = Column(String(128), default="SYSTEM")
    description = Column(Text, default="")
    source = Column(String(64), default="CIRIS_ENGINE")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(JSON, default=dict)

    case = relationship("CaseModel", back_populates="case_events")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    evidence_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)  # MODEL_EVIDENCE, GRAPH_EVIDENCE, TRANSACTION_EVIDENCE, HISTORICAL_EVIDENCE, GEOGRAPHIC_EVIDENCE
    summary = Column(Text, nullable=False)
    importance_score = Column(Float, default=0.0)
    details_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("CaseModel", back_populates="evidence")


class InterventionModel(Base):
    __tablename__ = "interventions"

    intervention_id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.case_id"), nullable=False, index=True)
    recommended_action = Column(String(32), default="INVESTIGATE", index=True)  # HOLD REVIEW, MONITOR, INVESTIGATE, ESCALATE
    confidence_score = Column(Float, default=0.0)
    action_rationale = Column(Text, default="")
    potential_hold_amount = Column(Float, default=0.0)
    authorization_boundary = Column(String(256), default="Authorized Bank / LEA Officer Review Required")
    status = Column(String(32), default="PENDING_REVIEW", index=True)  # PENDING_REVIEW, REVIEWED, ESCALATED, EXECUTED
    reviewed_by = Column(String(128), nullable=True)
    review_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case = relationship("CaseModel", back_populates="interventions")

"""
Idempotent Demo Seed Script for CIRIS Productization.

Seeds two deterministic demo cases into the database and pre-computes intelligence:
1. CASE-DEMO-001: Primary ATM Cash-Out Prediction scenario.
2. CASE-DEMO-002: Alternative Endpoint (Merchant / Transfer) scenario.
"""

import os
import sys
from datetime import datetime, timedelta

# Ensure src module is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.session import SessionLocal, init_db
from src.db.schema import setup_database
from src.db.models import (
    CaseModel,
    EntityModel,
    AccountModel,
    ATMModel,
    PredictionModel,
    AlertModel,
    InterventionModel,
    CaseEventModel,
    TransactionModel,
    GraphEdgeModel,
)
from src.services.case_service import CaseService


def seed_demo_data():
    """Seed CASE-DEMO-001 and CASE-DEMO-002 idempotently."""
    print("Setting up database tables...")
    setup_database()
    db = SessionLocal()

    try:
        now = datetime.utcnow()
        complaint_time = now - timedelta(hours=2)

        print("\n--- Seeding Demo Case 1: CASE-DEMO-001 (ATM Cash-Out Endpoint) ---")
        svc = CaseService(db)

        c1_location = {
            "state": "Maharashtra",
            "district": "Mumbai",
            "city": "Mumbai",
            "area": "Andheri West",
            "pincode": 400053,
            "latitude": 19.1136,
            "longitude": 72.8697,
        }

        # Create or update case 1
        case1, intel1 = svc.create_case(
            complaint_id="DEMO-001",
            reported_loss_amount=50000.0,
            fraud_type="Investment Cyber Fraud",
            complaint_timestamp=complaint_time,
            victim_location=c1_location,
        )
        case1.status = "REVIEW"
        case1.priority = "P1"
        case1.overall_risk_score = 0.88
        case1.overall_confidence = 0.85
        db.commit()

        # Seed explicit ATM for CASE-DEMO-001
        atm1 = db.query(ATMModel).filter(ATMModel.atm_id == "ATM_9981").first()
        if not atm1:
            atm1 = ATMModel(
                atm_id="ATM_9981",
                atm_name="SBI ATM - Andheri West",
                bank_name="State Bank of India",
                latitude=19.1150,
                longitude=72.8710,
                city="Mumbai",
                district="Mumbai",
                state="Maharashtra",
                pincode=400053,
                location_type="Standalone ATM",
                historical_risk_score=0.85,
            )
            db.add(atm1)

        # Seed graph edges for CASE-DEMO-001
        edge1 = db.query(GraphEdgeModel).filter(GraphEdgeModel.edge_id == "EDGE-DEMO-001").first()
        if not edge1:
            db.add(GraphEdgeModel(
                edge_id="EDGE-DEMO-001",
                source_node="ACC_VICTIM_001",
                target_node="ACC_MULE_001",
                relation_type="IMPS_TRANSFER",
                weight_amount=50000.0,
                timestamp=complaint_time,
                case_id="CASE-DEMO-001",
            ))
            db.add(GraphEdgeModel(
                edge_id="EDGE-DEMO-002",
                source_node="ACC_MULE_001",
                target_node="ATM_9981",
                relation_type="PREDICTED_CASH_OUT",
                weight_amount=35000.0,
                timestamp=complaint_time + timedelta(hours=1),
                case_id="CASE-DEMO-001",
            ))

        # Seed Alert 1
        alt1 = db.query(AlertModel).filter(AlertModel.alert_id == "ALT-DEMO-001").first()
        if not alt1:
            db.add(AlertModel(
                alert_id="ALT-DEMO-001",
                case_id="CASE-DEMO-001",
                priority="P1",
                risk_score=0.88,
                confidence=0.85,
                endpoint_summary="ATM Cashout Prediction at SBI ATM - Andheri West",
                amount=50000.0,
                status="NEW",
                assigned_to=None,
            ))

        # Seed Intervention 1
        int1 = db.query(InterventionModel).filter(InterventionModel.intervention_id == "INT-DEMO-001").first()
        if not int1:
            db.add(InterventionModel(
                intervention_id="INT-DEMO-001",
                case_id="CASE-DEMO-001",
                recommended_action="HOLD REVIEW",
                confidence_score=0.88,
                action_rationale="High risk score (0.88) with INR 15,000 unwithdrawn balance remaining in mule account ACC_MULE_001.",
                potential_hold_amount=15000.0,
                authorization_boundary="Authorized Bank / LEA Officer Review Required",
                status="PENDING_REVIEW",
            ))

        print("[OK] Seeded CASE-DEMO-001 successfully.")

        print("\n--- Seeding Demo Case 2: CASE-DEMO-002 (Merchant / Transfer Endpoint) ---")

        # Create CASE-DEMO-002
        case2 = db.query(CaseModel).filter(CaseModel.case_id == "CASE-DEMO-002").first()
        if not case2:
            case2 = CaseModel(
                case_id="CASE-DEMO-002",
                complaint_id="CMP-DEMO-002",
                victim_entity_id="VICTIM_DEMO_002",
                complaint_timestamp=complaint_time - timedelta(hours=3),
                reported_loss_amount=120000.0,
                fraud_type="Digital Voucher / E-Commerce Scam",
                latitude=28.6139,
                longitude=77.2090,
                state="Delhi",
                district="New Delhi",
                city="New Delhi",
                status="REVIEW",
                priority="P2",
                overall_risk_score=0.72,
                overall_confidence=0.78,
                created_at=now,
            )
            db.add(case2)

        # Seed Predictions for CASE-DEMO-002 (Merchant/Transfer primary)
        pred2 = db.query(PredictionModel).filter(PredictionModel.prediction_id == "PRED-DEMO-002-1").first()
        if not pred2:
            db.add(PredictionModel(
                prediction_id="PRED-DEMO-002-1",
                case_id="CASE-DEMO-002",
                endpoint_type="MERCHANT",
                target_id="MERCH_GOLD_EXCHANGE",
                target_name="Digital Gold Exchange Outlet",
                rank=1,
                score=0.72,
                confidence=0.78,
                confidence_tier="MEDIUM",
                predicted_time_window="6-12h",
                predicted_delay_hours=8.0,
                latitude=28.6150,
                longitude=77.2100,
                evidence_json={"shap": [{"feature": "merchant_category", "importance": 0.45, "label": "Gold Outlet High Velocity"}]},
            ))

        alt2 = db.query(AlertModel).filter(AlertModel.alert_id == "ALT-DEMO-002").first()
        if not alt2:
            db.add(AlertModel(
                alert_id="ALT-DEMO-002",
                case_id="CASE-DEMO-002",
                priority="P2",
                risk_score=0.72,
                confidence=0.78,
                endpoint_summary="Merchant Outlet Purchase Alert at Digital Gold Exchange",
                amount=120000.0,
                status="NEW",
                assigned_to=None,
            ))

        int2 = db.query(InterventionModel).filter(InterventionModel.intervention_id == "INT-DEMO-002").first()
        if not int2:
            db.add(InterventionModel(
                intervention_id="INT-DEMO-002",
                case_id="CASE-DEMO-002",
                recommended_action="MONITOR",
                confidence_score=0.72,
                action_rationale="Merchant transfer pattern flagged. Monitor onward settlement account.",
                potential_hold_amount=0.0,
                authorization_boundary="Authorized Bank / LEA Officer Review Required",
                status="PENDING_REVIEW",
            ))

        db.commit()
        print("[OK] Seeded CASE-DEMO-002 successfully.")
        print("\nDemo seeding completed cleanly!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error seeding demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()

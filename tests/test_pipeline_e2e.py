"""
End-to-End System Tests for CIPHER-X v4 Complete Machine Learning Pipeline.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload, IntelligenceReport
from src.ml.pipeline import CIPHERPipeline
from src.ml.routing.guardrails import OperationalGuardrails


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def trained_pipeline(tmp_path_factory):
    pipeline = CIPHERPipeline()
    metrics = pipeline.train(
        dataset_dir=DATASET_DIR,
        n_ranker_estimators=40,
        n_time_estimators=30,
        rank_sample_rows=25000,
    )
    print("\n--- Pipeline Training Complete ---")
    print(f"Ranker NDCG@5: {metrics['ranker_metrics'].get('NDCG@5', 0):.4f}")
    print(f"Time MAE: {metrics['time_metrics'].get('regression_MAE_hours', 0):.2f}h")

    # Save pipeline
    tmp_dir = tmp_path_factory.mktemp("cipher_pipeline")
    save_dir = os.path.join(tmp_dir, "artifacts")
    pipeline.save_pipeline(save_dir)

    # Load into clean pipeline instance to verify complete serialization
    loaded_pipeline = CIPHERPipeline()
    loaded_pipeline.load_pipeline(save_dir)

    return loaded_pipeline


def test_end_to_end_complaint_analysis(trained_pipeline):
    complaint_data = {
        "complaint_id": "CASE_E2E_MUMBAI_001",
        "complaint_timestamp": "2025-06-15 14:30:00",
        "incident_timestamp": "2025-06-15 13:45:00",
        "fraud_type": "UPI Fraud",
        "channel": "UPI",
        "reported_loss_amount": 85000.0,
        "victim_location": {
            "state": "Maharashtra",
            "district": "Mumbai",
            "city": "Mumbai",
            "area": "Andheri East",
            "pincode": 400069,
            "latitude": 19.1136,
            "longitude": 72.8697,
            "rural_urban": "Urban"
        },
        "victim_bank": "State Bank of India",
        "device_type": "Android",
        "is_otp_shared": 1,
        "clicked_malicious_link": 0,
        "urgency_score": 0.95,
        "account_age_months": 36,
        "num_transactions": 3,
        "fraud_description_category": "UPI Fraud",
    }
    complaint = ComplaintPayload(**complaint_data)

    report = trained_pipeline.analyze_complaint(complaint, top_k=5)

    assert isinstance(report, IntelligenceReport)
    assert report.complaint_id == "CASE_E2E_MUMBAI_001"
    assert report.total_candidates_evaluated > 0
    assert len(report.top_candidates) == 5
    assert report.highest_risk_atm is not None

    top_atm = report.highest_risk_atm
    assert top_atm.rank == 1
    assert 0.0 <= top_atm.fused_risk_score <= 1.0
    assert 0.0 <= top_atm.calibrated_probability <= 1.0
    assert top_atm.confidence_tier in ["HIGH", "MEDIUM", "LOW"]
    assert len(top_atm.shap_evidence) > 0
    assert "narrative_briefing" in top_atm.graph_evidence

    print("\n=======================================================")
    print(f"INTELLIGENCE REPORT: {report.complaint_id}")
    print(f"Status: {report.alert_status} | Candidates: {report.total_candidates_evaluated}")
    print(f"Top Suspected Cashout: {top_atm.atm_id} ({top_atm.atm_name})")
    print(f"Bank: {top_atm.bank_name} | City: {top_atm.city} | Dist: {top_atm.distance_km} km")
    print(f"Fused Risk Score: {top_atm.fused_risk_score:.4f} | Confidence: {top_atm.confidence_tier}")
    print(f"Time-to-Cashout: {top_atm.predicted_time_window} (est {top_atm.predicted_delay_hours}h)")
    print(f"Recommended Action: {top_atm.action_required}")
    print("Briefing:")
    print(top_atm.graph_evidence["narrative_briefing"])
    print("=======================================================")

    # Test Multi-Agency dispatch payloads
    bank_payload = OperationalGuardrails.format_bank_dispatch_payload(complaint, top_atm)
    assert bank_payload["suspected_atm_id"] == top_atm.atm_id
    assert bank_payload["target_bank"] == top_atm.bank_name

    lea_payload = OperationalGuardrails.format_lea_dispatch_payload(complaint, report)
    assert lea_payload["complaint_id"] == complaint.complaint_id
    assert "priority" in lea_payload


def test_guardrails_non_actionable_filtering(trained_pipeline):
    # Non-actionable: Reported 100 hours after incident
    stale_complaint = ComplaintPayload(
        complaint_id="CASE_STALE_001",
        complaint_timestamp="2025-06-15 14:00:00",
        incident_timestamp="2025-06-10 10:00:00",  # > 100 hours ago
        reported_loss_amount=50000.0,
        victim_location={"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai"},
    )
    report = trained_pipeline.analyze_complaint(stale_complaint)
    assert report.alert_status == "MONITOR_HOLD"
    assert report.total_candidates_evaluated == 0
    assert report.highest_risk_atm is None
    assert "EXPIRED_WINDOW" in report.connected_entities["routing_reason"]


if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as tmp_d:
        class DummyTmpFactory:
            def mktemp(self, name): return tmp_d
        pipeline = trained_pipeline(DummyTmpFactory())
        test_end_to_end_complaint_analysis(pipeline)
        test_guardrails_non_actionable_filtering(pipeline)
        print("ALL E2E PIPELINE TESTS PASSED!")

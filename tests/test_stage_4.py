"""
Unit and Integration Tests for Stage 4: Unsupervised Anomaly Detection Engine.
"""

import os
import pytest
import pandas as pd

from src.ml.contracts.schemas import ComplaintPayload
from src.ml.models.anomaly_detector import AnomalyDetector


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_anomaly_data():
    train_anom_csv = os.path.join(DATASET_DIR, "train", "anomaly_train.csv")
    assert os.path.exists(train_anom_csv), f"Missing {train_anom_csv}"
    train_df = pd.read_csv(train_anom_csv)
    return train_df


def test_anomaly_detector_training_and_scoring(setup_anomaly_data, tmp_path):
    train_df = setup_anomaly_data

    detector = AnomalyDetector(contamination=0.10, n_estimators=100)
    info = detector.fit(train_df)

    assert detector.is_fitted
    assert "n_samples" in info
    assert info["n_samples"] == len(train_df)

    # Test high-risk anomalous complaint
    high_anom_complaint = ComplaintPayload(
        complaint_id="CASE_HIGH_ANOM",
        complaint_timestamp="2025-06-15 03:30:00",  # Night 3:30 AM
        reported_loss_amount=250000.0,              # Very high loss
        urgency_score=0.98,
        num_transactions=5,
        is_otp_shared=1,
        clicked_malicious_link=1,
        victim_location={"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai"},
    )
    score_high, sub_high = detector.predict_anomaly_score(high_anom_complaint)

    # Test low-risk regular complaint
    low_anom_complaint = ComplaintPayload(
        complaint_id="CASE_LOW_ANOM",
        complaint_timestamp="2025-06-15 14:00:00",  # Daytime 2 PM
        reported_loss_amount=3000.0,                # Small loss
        urgency_score=0.20,
        num_transactions=1,
        is_otp_shared=0,
        clicked_malicious_link=0,
        victim_location={"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai"},
    )
    score_low, sub_low = detector.predict_anomaly_score(low_anom_complaint)

    print(f"\nHigh Anomaly Score: {score_high:.4f} (sub: {sub_high})")
    print(f"Low Anomaly Score: {score_low:.4f} (sub: {sub_low})")

    assert 0.0 <= score_high <= 1.0
    assert 0.0 <= score_low <= 1.0
    assert score_high >= score_low
    assert sub_high["timing_anomaly_score"] > sub_low["timing_anomaly_score"]

    # Test serialization
    save_path = os.path.join(tmp_path, "anomaly_detector.joblib")
    detector.save(save_path)
    assert os.path.exists(save_path)

    loaded = AnomalyDetector()
    loaded.load(save_path)
    assert loaded.is_fitted
    l_score, _ = loaded.predict_anomaly_score(high_anom_complaint)
    assert l_score == pytest.approx(score_high, abs=1e-5)


if __name__ == "__main__":
    train_df = setup_anomaly_data()
    print("Testing Anomaly Detector...")
    test_anomaly_detector_training_and_scoring(train_df, tmp_path="/tmp")
    print("STAGE 4 TESTS PASSED!")

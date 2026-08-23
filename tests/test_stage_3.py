"""
Unit and Integration Tests for Stage 3: Time-to-Cashout Prediction Engine.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload
from src.ml.models.time_predictor import TimeToCashoutPredictor


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_time_data():
    comp_df = pd.read_csv(os.path.join(DATASET_DIR, "complaints.csv"))
    train_time_df = pd.read_csv(os.path.join(DATASET_DIR, "train", "time_train.csv"))
    val_time_df = pd.read_csv(os.path.join(DATASET_DIR, "validation", "time_val.csv"))

    train_comp = comp_df[comp_df["complaint_id"].isin(train_time_df["complaint_id"])].copy()
    val_comp = comp_df[comp_df["complaint_id"].isin(val_time_df["complaint_id"])].copy()

    return train_comp, train_time_df, val_comp, val_time_df


def test_time_predictor_training_and_inference(setup_time_data, tmp_path):
    train_comp, train_time_df, val_comp, val_time_df = setup_time_data

    predictor = TimeToCashoutPredictor(n_estimators=80, learning_rate=0.08)
    metrics = predictor.fit(
        train_complaints_df=train_comp,
        train_time_df=train_time_df,
        val_complaints_df=val_comp,
        val_time_df=val_time_df,
    )

    print("\n--- Validation Time-to-Cashout Metrics ---")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    assert "regression_MAE_hours" in metrics
    assert "classification_Accuracy" in metrics
    assert metrics["regression_MAE_hours"] < 5.0  # Must have reasonable MAE on hours
    assert metrics["classification_Accuracy"] > 0.25  # Better than random 5-class baseline (0.20)

    # Test single complaint inference
    complaint_data = {
        "complaint_id": "TEST_TIME_CASE",
        "complaint_timestamp": "2025-06-15 14:30:00",
        "incident_timestamp": "2025-06-15 13:30:00",
        "fraud_type": "UPI Fraud",
        "channel": "UPI",
        "reported_loss_amount": 95000.0,
        "victim_location": {"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai"},
        "urgency_score": 0.92,
        "num_transactions": 3,
        "account_age_months": 24,
        "is_otp_shared": 1,
    }
    complaint = ComplaintPayload(**complaint_data)

    pred_delay, top_window, probs = predictor.predict(complaint)

    assert pred_delay > 0.0
    assert isinstance(top_window, str)
    assert len(probs) == 5
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
    assert all(0.0 <= p <= 1.0 for p in probs.values())

    # Test serialization
    save_path = os.path.join(tmp_path, "time_predictor.joblib")
    predictor.save(save_path)
    assert os.path.exists(save_path)

    loaded = TimeToCashoutPredictor()
    loaded.load(save_path)
    assert loaded.is_fitted
    l_delay, l_window, l_probs = loaded.predict(complaint)
    assert l_delay == pred_delay
    assert l_window == top_window


if __name__ == "__main__":
    train_comp, train_time_df, val_comp, val_time_df = setup_time_data()
    print("Testing Time-to-Cashout Predictor...")
    test_time_predictor_training_and_inference((train_comp, train_time_df, val_comp, val_time_df), tmp_path="/tmp")
    print("STAGE 3 TESTS PASSED!")

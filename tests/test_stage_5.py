"""
Unit and Integration Tests for Stage 5: Calibration & Multi-Signal Risk Fusion Engine.
"""

import os
import pytest
import numpy as np
import pandas as pd

from src.ml.models.ranker import ATMRanker
from src.ml.models.fusion import ProbabilityCalibrator, MultiSignalRiskFusionEngine


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_ranker_and_val():
    train_df = pd.read_csv(os.path.join(DATASET_DIR, "train", "rank_pairs_train.csv"))
    val_df = pd.read_csv(os.path.join(DATASET_DIR, "validation", "rank_pairs_val.csv"))

    ranker = ATMRanker(n_estimators=60, learning_rate=0.1)
    ranker.fit(train_df, val_df=val_df)

    val_raw_scores = ranker.predict_scores(val_df)
    val_labels = val_df["label"].values

    return ranker, val_df, val_raw_scores, val_labels


def test_probability_calibrator(setup_ranker_and_val):
    _, _, val_raw_scores, val_labels = setup_ranker_and_val

    calibrator = ProbabilityCalibrator(method="platt")
    info = calibrator.fit(val_raw_scores, val_labels)

    assert "brier_score" in info
    assert info["brier_score"] < 0.15

    cal_probs = calibrator.calibrate(val_raw_scores)
    assert (cal_probs >= 0.0).all()
    assert (cal_probs <= 1.0).all()


def test_multi_signal_risk_fusion(setup_ranker_and_val, tmp_path):
    ranker, val_df, val_raw_scores, val_labels = setup_ranker_and_val

    calibrator = ProbabilityCalibrator(method="platt")
    calibrator.fit(val_raw_scores, val_labels)

    fusion_engine = MultiSignalRiskFusionEngine(calibrator=calibrator)

    sample_cid = val_df["complaint_id"].iloc[0]
    sample_candidates = val_df[val_df["complaint_id"] == sample_cid]
    ranked_candidates = ranker.rank_candidates_for_complaint(sample_candidates)

    predictions = fusion_engine.fuse_predictions(
        ranked_candidates_df=ranked_candidates,
        predicted_delay_hours=1.5,
        predicted_time_window_short="1-3h",
        predicted_time_window_full="1 - 3 Hours (HIGH URGENCY)",
        anomaly_score=0.85,
        anomaly_sub_scores={"amount": 0.8, "velocity": 0.9},
    )

    assert len(predictions) == len(ranked_candidates)
    top_pred = predictions[0]

    assert top_pred.rank == 1
    assert 0.0 <= top_pred.fused_risk_score <= 1.0
    assert 0.0 <= top_pred.calibrated_probability <= 1.0
    assert top_pred.confidence_tier in ["HIGH", "MEDIUM", "LOW"]
    assert len(top_pred.action_required) > 0
    assert top_pred.sub_scores.location_score >= 0.0
    assert top_pred.sub_scores.time_score >= 0.0

    print(f"\nTop ATM: {top_pred.atm_id} | Risk: {top_pred.fused_risk_score} | Tier: {top_pred.confidence_tier} | Action: {top_pred.action_required}")

    # Test serialization
    save_path = os.path.join(tmp_path, "fusion_engine.joblib")
    fusion_engine.save(save_path)
    assert os.path.exists(save_path)

    loaded_engine = MultiSignalRiskFusionEngine()
    loaded_engine.load(save_path)
    assert loaded_engine.calibrator.is_fitted


if __name__ == "__main__":
    setup_data = setup_ranker_and_val()
    print("Testing Calibration and Risk Fusion...")
    test_probability_calibrator(setup_data)
    test_multi_signal_risk_fusion(setup_data, tmp_path="/tmp")
    print("STAGE 5 TESTS PASSED!")

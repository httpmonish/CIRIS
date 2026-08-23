"""
Unit and Integration Tests for Stage 2: Supervised Multi-Model ATM Ranker.
"""

import os
import pytest
import pandas as pd

from src.ml.models.ranker import ATMRanker


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_ranker_data():
    train_csv = os.path.join(DATASET_DIR, "train", "rank_pairs_train.csv")
    val_csv = os.path.join(DATASET_DIR, "validation", "rank_pairs_val.csv")

    assert os.path.exists(train_csv), f"Missing {train_csv}"
    assert os.path.exists(val_csv), f"Missing {val_csv}"

    train_df = pd.read_csv(train_csv)
    val_df = pd.read_csv(val_csv)

    return train_df, val_df


def test_ranker_training_and_evaluation(setup_ranker_data, tmp_path):
    train_df, val_df = setup_ranker_data

    ranker = ATMRanker(
        n_estimators=100,
        learning_rate=0.08,
        num_leaves=31,
        random_state=42,
    )

    metrics = ranker.fit(train_df, val_df=val_df, early_stopping_rounds=20)

    # Check metrics
    assert "NDCG@1" in metrics
    assert "NDCG@5" in metrics
    assert "MRR" in metrics
    assert "HitRate@1" in metrics
    assert "HitRate@5" in metrics

    print("\n--- Validation Ranking Metrics ---")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    # Verify performance threshold on development dataset
    assert metrics["NDCG@5"] > 0.20, f"NDCG@5 ({metrics['NDCG@5']}) below minimum benchmark"
    assert metrics["HitRate@10"] > 0.50, f"HitRate@10 ({metrics['HitRate@10']}) below minimum benchmark"
    assert metrics["MRR"] > 0.20, f"MRR ({metrics['MRR']}) below minimum benchmark"

    # Test single complaint ranking
    sample_cid = val_df["complaint_id"].iloc[0]
    sample_complaint_df = val_df[val_df["complaint_id"] == sample_cid]
    ranked_df = ranker.rank_candidates_for_complaint(sample_complaint_df)

    assert len(ranked_df) == len(sample_complaint_df)
    assert "ranking_score" in ranked_df.columns
    assert "rank" in ranked_df.columns
    assert (ranked_df["rank"].values == list(range(1, len(ranked_df) + 1))).all()
    assert ranked_df["ranking_score"].iloc[0] >= ranked_df["ranking_score"].iloc[-1]

    # Test model serialization
    save_path = os.path.join(tmp_path, "atm_ranker.joblib")
    ranker.save(save_path)
    assert os.path.exists(save_path)

    loaded_ranker = ATMRanker()
    loaded_ranker.load(save_path)
    assert loaded_ranker.is_fitted

    loaded_scores = loaded_ranker.predict_scores(sample_complaint_df)
    original_scores = ranker.predict_scores(sample_complaint_df)
    assert (loaded_scores == original_scores).all()


def test_feature_importances(setup_ranker_data):
    train_df, val_df = setup_ranker_data
    ranker = ATMRanker(n_estimators=50, learning_rate=0.1)
    ranker.fit(train_df, val_df=val_df)

    importances = ranker.get_feature_importances()
    assert len(importances) == len(ranker.feature_columns)
    # Top features should have non-zero importance
    top_feature = list(importances.keys())[0]
    assert importances[top_feature] > 0


if __name__ == "__main__":
    train_df, val_df = setup_ranker_data()
    print("Testing ATM Ranker...")
    test_ranker_training_and_evaluation((train_df, val_df), tmp_path="/tmp")
    test_feature_importances((train_df, val_df))
    print("STAGE 2 TESTS PASSED!")

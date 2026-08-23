"""
Unit and Integration Tests for Stage 6: Explainable AI & TreeSHAP Engine.
"""

import os
import pytest
import pandas as pd

from src.ml.models.ranker import ATMRanker
from src.ml.xai.explainer import TreeSHAPExplainer


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_ranker_for_xai():
    train_df = pd.read_csv(os.path.join(DATASET_DIR, "train", "rank_pairs_train.csv"))
    val_df = pd.read_csv(os.path.join(DATASET_DIR, "validation", "rank_pairs_val.csv"))

    ranker = ATMRanker(n_estimators=50, learning_rate=0.1)
    ranker.fit(train_df, val_df=val_df)
    return ranker, val_df


def test_shap_explainer(setup_ranker_for_xai):
    ranker, val_df = setup_ranker_for_xai

    explainer = TreeSHAPExplainer(ranker)

    sample_row = val_df.iloc[[0]]
    top_attrs, narrative = explainer.explain_candidate(sample_row, top_k_features=5)

    assert len(top_attrs) == 5
    for attr in top_attrs:
        assert "feature" in attr
        assert "friendly_name" in attr
        assert "shap_value" in attr
        assert attr["direction"] in ["RISK_INCREASE", "RISK_DECREASE"]

    assert isinstance(narrative, str)
    assert len(narrative) > 20
    assert "•" in narrative

    print("\n--- TreeSHAP Feature Attributions ---")
    for a in top_attrs:
        print(f"  {a['friendly_name']}: val={a['value']:.2f}, impact={a['shap_value']:+.4f} ({a['direction']})")

    print("\n--- Officer Narrative Briefing ---")
    print(narrative)


if __name__ == "__main__":
    ranker, val_df = setup_ranker_for_xai()
    print("Testing TreeSHAP Explainer...")
    test_shap_explainer((ranker, val_df))
    print("STAGE 6 TESTS PASSED!")

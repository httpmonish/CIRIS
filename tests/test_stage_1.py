"""
Unit and Integration Tests for Stage 1: Point-in-Time Feature Engineering.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.candidate_retriever import CandidateRetriever
from src.ml.features.feature_builder import FeatureBuilder


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_pipeline():
    atm_df = pd.read_csv(os.path.join(DATASET_DIR, "atm_master.csv"))
    wds_df = pd.read_csv(os.path.join(DATASET_DIR, "withdrawals.csv"))
    edges_df = pd.read_csv(os.path.join(DATASET_DIR, "graph_edges.csv"))
    case_links_df = pd.read_csv(os.path.join(DATASET_DIR, "case_links.csv"))

    spatial_index = SpatialIndex(atm_df)
    hotspot_cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wds_df)
    graph_engine = TemporalGraphEngine(
        graph_edges_df=edges_df,
        case_links_df=case_links_df,
        withdrawals_df=wds_df
    )

    retriever = CandidateRetriever(
        spatial_index=spatial_index,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
    )

    feature_builder = FeatureBuilder(
        atm_master_df=atm_df,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
        spatial_index=spatial_index,
    )

    return retriever, feature_builder


def test_feature_builder_output(setup_pipeline):
    retriever, feature_builder = setup_pipeline

    complaint_data = {
        "complaint_id": "TEST_CASE_001",
        "complaint_timestamp": "2025-06-15 14:30:00",
        "fraud_type": "UPI Fraud",
        "reported_loss_amount": 80000.0,
        "victim_location": {
            "state": "Maharashtra",
            "city": "Mumbai",
            "pincode": 400001,
            "latitude": 19.0760,
            "longitude": 72.8777,
            "rural_urban": "Urban"
        },
        "urgency_score": 0.85,
        "num_transactions": 2,
    }
    complaint = ComplaintPayload(**complaint_data)

    candidates = retriever.retrieve_candidates(complaint)
    assert len(candidates) > 0

    feat_df = feature_builder.build_features_for_candidates(complaint, candidates)

    assert len(feat_df) == len(candidates)
    assert "complaint_id" in feat_df.columns
    assert "atm_id" in feat_df.columns

    # Verify all 36 feature columns exist and have zero NaN values
    for col in FeatureBuilder.FEATURE_COLUMNS:
        assert col in feat_df.columns, f"Missing feature column: {col}"
        assert not feat_df[col].isna().any(), f"Column {col} has NaN values"

    # Verify data sanity
    assert (feat_df["haversine_distance_km"] >= 0.0).all()
    assert (feat_df["geographic_similarity"] >= 0.0).all()
    assert (feat_df["geographic_similarity"] <= 1.0).all()
    assert (feat_df["historical_cashout_rate_as_of_T"] >= 0.0).all()
    assert (feat_df["historical_cashout_rate_as_of_T"] <= 1.0).all()
    assert (feat_df["hour"] == 14).all()


def test_temporal_leakage_safety(setup_pipeline):
    retriever, feature_builder = setup_pipeline

    complaint = ComplaintPayload(
        complaint_id="CASE_TEMPORAL_CHECK",
        complaint_timestamp=datetime.fromisoformat("2024-06-01 00:00:00"),
        victim_location={"latitude": 19.0760, "longitude": 72.8777, "city": "Mumbai"}
    )
    candidates = retriever.retrieve_candidates(complaint, as_of_T=complaint.complaint_timestamp)
    feat_early = feature_builder.build_features_for_candidates(complaint, candidates, as_of_T=complaint.complaint_timestamp)

    t_late = datetime.fromisoformat("2026-01-01 00:00:00")
    feat_late = feature_builder.build_features_for_candidates(complaint, candidates, as_of_T=t_late)

    # Cashout counts at early T should be <= cashout counts at late T
    assert (feat_early["historical_cashout_count_as_of_T"] <= feat_late["historical_cashout_count_as_of_T"]).all()


if __name__ == "__main__":
    retriever, feature_builder = setup_pipeline()
    print("Testing feature builder...")
    test_feature_builder_output((retriever, feature_builder))
    print("[PASS] Feature matrix creation & schema compliance")
    test_temporal_leakage_safety((retriever, feature_builder))
    print("[PASS] Temporal leakage isolation")
    print("STAGE 1 TESTS PASSED!")

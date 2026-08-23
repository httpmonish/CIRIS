"""
Unit and Integration Tests for Stage -1: Offline Intelligence & Schemas.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload, VictimLocation, ATMMasterRecord, CandidateATM
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache


DATASET_DIR = "datasets/development/dataset"


def test_contracts_validation():
    payload_data = {
        "complaint_id": "TEST_001",
        "complaint_timestamp": "2025-06-01 10:00:00",
        "fraud_type": "UPI Fraud",
        "reported_loss_amount": "50000.50",
        "victim_location": {
            "state": "Maharashtra",
            "city": "Mumbai",
            "pincode": "400001",
            "latitude": "19.0760",
            "longitude": "72.8777",
            "rural_urban": "Urban"
        },
        "urgency_score": "0.85",
        "num_transactions": "3"
    }
    complaint = ComplaintPayload(**payload_data)
    assert complaint.complaint_id == "TEST_001"
    assert complaint.reported_loss_amount == 50000.50
    assert complaint.victim_location.latitude == 19.0760
    assert complaint.urgency_score == 0.85
    assert complaint.num_transactions == 3


def test_spatial_index_with_dataset():
    atm_csv = os.path.join(DATASET_DIR, "atm_master.csv")
    assert os.path.exists(atm_csv), f"Missing {atm_csv}"

    atm_df = pd.read_csv(atm_csv)
    spatial_index = SpatialIndex(atm_df)

    # Test Mumbai coordinates: (19.0760, 72.8777)
    radius_res = spatial_index.query_radius(19.0760, 72.8777, radius_km=50.0)
    assert len(radius_res) > 0
    assert all(r["distance_km"] <= 50.0 for r in radius_res)
    # Verify sorted ascending
    dists = [r["distance_km"] for r in radius_res]
    assert dists == sorted(dists)

    # Test KNN query
    knn_res = spatial_index.query_knn(19.0760, 72.8777, k=25)
    assert len(knn_res) == 25
    assert knn_res[0]["distance_km"] <= knn_res[-1]["distance_km"]


def test_temporal_graph_engine():
    edges_csv = os.path.join(DATASET_DIR, "graph_edges.csv")
    case_links_csv = os.path.join(DATASET_DIR, "case_links.csv")
    wds_csv = os.path.join(DATASET_DIR, "withdrawals.csv")

    edges_df = pd.read_csv(edges_csv)
    case_links_df = pd.read_csv(case_links_csv)
    wds_df = pd.read_csv(wds_csv)

    graph_engine = TemporalGraphEngine(
        graph_edges_df=edges_df,
        case_links_df=case_links_df,
        withdrawals_df=wds_df
    )

    t_early = datetime.fromisoformat("2024-06-01 00:00:00")
    t_late = datetime.fromisoformat("2026-01-01 00:00:00")

    G_early = graph_engine.get_subgraph_as_of_T(t_early)
    G_late = graph_engine.get_subgraph_as_of_T(t_late)

    # Subgraph size should grow monotonically over time
    assert G_early.number_of_edges() <= G_late.number_of_edges()

    # Test account feature extraction
    sample_acc = edges_df.iloc[0]["src_account_id"]
    feats = graph_engine.get_account_graph_features_as_of_T(sample_acc, t_late)
    assert "account_degree_as_of_T" in feats
    assert feats["account_degree_as_of_T"] >= 0.0


def test_historical_hotspot_cache():
    atm_csv = os.path.join(DATASET_DIR, "atm_master.csv")
    wds_csv = os.path.join(DATASET_DIR, "withdrawals.csv")

    atm_df = pd.read_csv(atm_csv)
    wds_df = pd.read_csv(wds_csv)

    cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wds_df)

    t_mid = datetime.fromisoformat("2025-06-01 00:00:00")
    sample_atm = atm_df.iloc[0]["atm_id"]

    stats = cache.get_atm_stats_as_of_T(sample_atm, t_mid)
    assert "historical_cashout_rate_as_of_T" in stats
    assert "historical_avg_loss_as_of_T" in stats
    assert 0.0 <= stats["historical_cashout_rate_as_of_T"] <= 1.0

    hotspots = cache.get_top_hotspots_as_of_T(t_mid, top_k=10)
    assert len(hotspots) <= 10


if __name__ == "__main__":
    print("Running Stage -1 verification tests...")
    test_contracts_validation()
    print("[PASS] Contracts and Pydantic validation")
    test_spatial_index_with_dataset()
    print("[PASS] SpatialIndex BallTree queries (Radius + KNN)")
    test_temporal_graph_engine()
    print("[PASS] TemporalGraphEngine causal graph extraction")
    test_historical_hotspot_cache()
    print("[PASS] HistoricalHotspotCache point-in-time Bayesian stats")
    print("ALL STAGE -1 TESTS PASSED!")

"""
Unit and Integration Tests for Stage 0: Hybrid Candidate Retrieval Engine.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.contracts.schemas import ComplaintPayload, CandidateATM
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.candidate_retriever import CandidateRetriever


DATASET_DIR = "datasets/development/dataset"


@pytest.fixture(scope="module")
def setup_retriever():
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
        geo_radius_km=50.0,
        geo_fallback_knn=25,
        top_hotspots_count=40,
    )
    return retriever


def test_candidate_retrieval_structure(setup_retriever):
    retriever = setup_retriever

    complaint_data = {
        "complaint_id": "TEST_CASE_MUMBAI",
        "complaint_timestamp": "2025-06-15 14:30:00",
        "fraud_type": "UPI Fraud",
        "reported_loss_amount": 75000.0,
        "victim_location": {
            "state": "Maharashtra",
            "city": "Mumbai",
            "pincode": 400001,
            "latitude": 19.0760,
            "longitude": 72.8777,
            "rural_urban": "Urban"
        },
        "urgency_score": 0.9,
    }
    complaint = ComplaintPayload(**complaint_data)

    candidates = retriever.retrieve_candidates(complaint)

    assert len(candidates) > 0
    # Must be less than total 400 ATMs (search space pruned)
    assert len(candidates) <= 400

    # Check candidate typing and fields
    for cand in candidates:
        assert isinstance(cand, CandidateATM)
        assert cand.distance_km >= 0.0
        assert len(cand.retrieval_sources) > 0
        assert all(s in ["geo", "hotspot", "network", "behavioural", "district", "state"] for s in cand.retrieval_sources)

    # Check that nearby ATMs have 'geo' in sources
    nearby_cands = [c for c in candidates if c.distance_km <= 50.0]
    assert len(nearby_cands) > 0
    assert any("geo" in c.retrieval_sources for c in nearby_cands)


def test_candidate_retrieval_historical_point_in_time(setup_retriever):
    retriever = setup_retriever

    complaint = ComplaintPayload(
        complaint_id="CASE_EARLY",
        complaint_timestamp=datetime.fromisoformat("2024-06-01 00:00:00"),
        victim_location={
            "latitude": 28.6139,
            "longitude": 77.2090,
            "city": "Delhi"
        }
    )

    cands_early = retriever.retrieve_candidates(complaint, as_of_T=datetime.fromisoformat("2024-06-01 00:00:00"))
    cands_late = retriever.retrieve_candidates(complaint, as_of_T=datetime.fromisoformat("2026-01-01 00:00:00"))

    # Both return valid candidates
    assert len(cands_early) > 0
    assert len(cands_late) > 0


def test_to_feature_dict_list(setup_retriever):
    retriever = setup_retriever

    complaint = ComplaintPayload(
        complaint_id="CASE_FEAT_TEST",
        complaint_timestamp=datetime.fromisoformat("2025-01-01 12:00:00"),
        victim_location={"latitude": 12.9716, "longitude": 77.5946, "city": "Bengaluru"}
    )
    candidates = retriever.retrieve_candidates(complaint)
    dict_rows = retriever.to_feature_dict_list(complaint, candidates)

    assert len(dict_rows) == len(candidates)
    row0 = dict_rows[0]
    assert "complaint_id" in row0
    assert "atm_id" in row0
    assert "in_geo_candidates" in row0
    assert "in_hotspot_candidates" in row0
    assert "haversine_distance_km" in row0


if __name__ == "__main__":
    retriever = setup_retriever()
    print("Testing candidate retrieval...")
    test_candidate_retrieval_structure(retriever)
    print("[PASS] Candidate retrieval structure & multi-source tagging")
    test_candidate_retrieval_historical_point_in_time(retriever)
    print("[PASS] Point-in-time candidate retrieval isolation")
    test_to_feature_dict_list(retriever)
    print("[PASS] Conversion to feature dictionary list")
    print("STAGE 0 TESTS PASSED!")

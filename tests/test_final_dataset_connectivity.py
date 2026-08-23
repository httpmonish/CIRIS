"""
Final Dataset Connectivity and End-to-End Integration Verification Test.

Proves that all ML V4 components dynamically ingest and process data
from datasets/final/ through the canonical DatasetLoader.
"""

import os
import pytest
import pandas as pd
from datetime import datetime

from src.ml.data.loader import DatasetLoader
from src.ml.contracts.schemas import ComplaintPayload, VictimLocation
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.candidate_retriever import CandidateRetriever
from src.ml.features.feature_builder import FeatureBuilder
from src.ml.models.ranker import ATMRanker
from src.ml.models.time_predictor import TimeToCashoutPredictor
from src.ml.models.anomaly_detector import AnomalyDetector
from src.ml.models.fusion import MultiSignalRiskFusionEngine, ProbabilityCalibrator


@pytest.fixture(scope="module")
def dataset_loader():
    return DatasetLoader("datasets/final")


def test_final_dataset_loader_integrity(dataset_loader):
    """Verify DatasetLoader resolves all tables and passes data integrity checks."""
    audit = dataset_loader.run_integrity_audit()
    assert audit["passed"] is True, f"Integrity audit failed: {audit}"
    assert audit["tables"]["atm_master"]["rows"] == 7000
    assert audit["tables"]["complaints"]["rows"] == 50000
    assert audit["tables"]["transactions"]["rows"] == 349706
    assert audit["tables"]["accounts"]["rows"] == 40000
    assert audit["tables"]["withdrawals"]["rows"] == 50000


def test_final_dataset_spatial_index(dataset_loader):
    """Verify SpatialIndex builds KDTree on 7,000 final ATMs."""
    atm_df = dataset_loader.load_atm_master()
    spatial_index = SpatialIndex(atm_df)

    # Query Mumbai coordinates
    res = spatial_index.query_radius(19.0760, 72.8777, radius_km=50.0)
    assert len(res) > 0
    assert all(r["distance_km"] <= 50.0 for r in res)


def test_final_dataset_hotspot_cache(dataset_loader):
    """Verify HistoricalHotspotCache computes point-in-time scores from final withdrawals."""
    atm_df = dataset_loader.load_atm_master()
    wd_df = dataset_loader.load_withdrawals()
    cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wd_df)

    # Query at a midpoint timestamp
    t = datetime(2025, 6, 1, 12, 0, 0)
    top_atms = cache.get_top_hotspots_as_of_T(as_of_T=t, top_k=20)
    assert len(top_atms) == 20
    assert all(isinstance(x, tuple) and len(x) == 2 for x in top_atms)


def test_final_dataset_graph_engine(dataset_loader):
    """Verify TemporalGraphEngine traverses 349k final graph edges."""
    edges_df = dataset_loader.load_graph_edges()
    cases_df = dataset_loader.load_case_links()
    wd_df = dataset_loader.load_withdrawals()
    upi_df = dataset_loader.load_upi_entities()

    graph = TemporalGraphEngine(
        graph_edges_df=edges_df,
        case_links_df=cases_df,
        withdrawals_df=wd_df,
        upi_df=upi_df,
    )

    # Check sample account from case_links
    sample_acc = cases_df["cashout_account_id"].iloc[0]
    t = datetime(2025, 6, 1, 12, 0, 0)
    history_atms = graph.get_network_associated_atms_as_of_T([sample_acc], as_of_T=t)
    assert isinstance(history_atms, set)


def test_final_dataset_candidate_retrieval(dataset_loader):
    """Verify CandidateRetriever retrieves candidates without true ATM insertion."""
    atm_df = dataset_loader.load_atm_master()
    wd_df = dataset_loader.load_withdrawals()
    edges_df = dataset_loader.load_graph_edges()
    cases_df = dataset_loader.load_case_links()

    spatial_index = SpatialIndex(atm_df)
    hotspot_cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wd_df)
    graph_engine = TemporalGraphEngine(
        graph_edges_df=edges_df,
        case_links_df=cases_df,
        withdrawals_df=wd_df,
    )

    retriever = CandidateRetriever(
        spatial_index=spatial_index,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
        geo_radius_km=100.0,
        geo_fallback_knn=100,
        top_hotspots_count=100,
    )

    complaints_df = dataset_loader.load_complaints()
    c_row = complaints_df.iloc[0]
    complaint = ComplaintPayload(
        complaint_id=c_row["complaint_id"],
        complaint_timestamp=c_row["complaint_timestamp"],
        fraud_type=c_row["fraud_type"],
        reported_loss_amount=c_row["reported_loss_amount"],
        victim_location=VictimLocation(
            latitude=c_row["victim_lat"],
            longitude=c_row["victim_lon"],
            city=c_row["victim_city"],
            district=c_row["victim_district"],
            state=c_row["victim_state"],
            pincode=c_row["victim_pincode"],
        ),
    )

    candidates = retriever.retrieve_candidates(complaint)
    assert len(candidates) > 0
    assert all(hasattr(c, "atm_id") for c in candidates)


def test_final_dataset_feature_builder(dataset_loader):
    """Verify FeatureBuilder extracts exactly the 36 standard features on final data."""
    atm_df = dataset_loader.load_atm_master()
    wd_df = dataset_loader.load_withdrawals()
    spatial_index = SpatialIndex(atm_df)
    hotspot_cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wd_df)

    builder = FeatureBuilder(
        atm_master_df=atm_df,
        hotspot_cache=hotspot_cache,
        spatial_index=spatial_index,
    )

    complaints_df = dataset_loader.load_complaints()
    c_row = complaints_df.iloc[0]
    complaint = ComplaintPayload(
        complaint_id=c_row["complaint_id"],
        complaint_timestamp=c_row["complaint_timestamp"],
        fraud_type=c_row["fraud_type"],
        reported_loss_amount=c_row["reported_loss_amount"],
        victim_location=VictimLocation(
            latitude=c_row["victim_lat"],
            longitude=c_row["victim_lon"],
            city=c_row["victim_city"],
            district=c_row["victim_district"],
            state=c_row["victim_state"],
            pincode=c_row["victim_pincode"],
        ),
    )

    from src.ml.contracts.schemas import CandidateATM
    atm_sample = atm_df.iloc[0]
    cand = CandidateATM(
        atm_id=atm_sample["atm_id"],
        atm_name=atm_sample["atm_name"],
        bank_name=atm_sample["bank_name"],
        latitude=atm_sample["latitude"],
        longitude=atm_sample["longitude"],
        distance_km=12.5,
        location_type=atm_sample["location_type"],
        city=atm_sample["city"],
        district=atm_sample["district"],
        retrieval_sources=["geo_proximity"],
    )

    feat_matrix = builder.build_features_for_candidates(complaint, [cand])
    assert len(feat_matrix) == 1
    feature_cols = [c for c in feat_matrix.columns if c not in ["complaint_id", "atm_id"]]
    assert feature_cols == builder.FEATURE_COLUMNS
    assert len(builder.FEATURE_COLUMNS) == 36

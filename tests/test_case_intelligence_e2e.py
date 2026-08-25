"""
Unit & Integration Test Suite for CIRIS Case Intelligence Engine.

Validates Entity Resolution, Money-Flow Graph, Fragmentation Detection,
Mule Risk Scoring, Amount-at-Risk Accounting, Endpoint Classification,
and Intervention Recommendations.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.ml.contracts.schemas import ComplaintPayload, VictimLocation
from src.ml.contracts.case_intelligence import CaseIntelligenceObject
from src.ml.features.entity_resolution import EntityResolutionEngine
from src.ml.retrieval.money_flow_graph import MoneyFlowGraphEngine
from src.ml.features.fragmentation_detector import TransactionFragmentationDetector
from src.ml.models.mule_network import MuleNetworkIntelligenceEngine
from src.ml.features.amount_at_risk import AmountAtRiskEngine
from src.ml.routing.endpoint_classifier import EndpointTypeClassifier
from src.ml.routing.intervention import InterventionRecommendationEngine


@pytest.fixture
def sample_data():
    t0 = datetime(2026, 1, 15, 10, 0, 0)
    accounts = pd.DataFrame([
        {"account_id": "ACC_000001", "entity_id": "ENTITY_000001", "card_id": "CARD_001", "device_id": "DEV_001"},
        {"account_id": "ACC_000002", "entity_id": "ENTITY_000002", "card_id": "CARD_002", "device_id": "DEV_002"},
        {"account_id": "ACC_000003", "entity_id": "ENTITY_000002", "card_id": "CARD_003", "device_id": "DEV_002"},
    ])

    txns = pd.DataFrame([
        {"source_account": "ACC_000001", "destination_account": "ACC_000002", "amount": 10000.0, "timestamp": t0 - timedelta(minutes=45)},
        {"source_account": "ACC_000002", "destination_account": "ACC_000003", "amount": 5000.0, "timestamp": t0 - timedelta(minutes=30)},
        {"source_account": "ACC_000002", "destination_account": "ACC_000004", "amount": 2000.0, "timestamp": t0 - timedelta(minutes=20)},
        {"source_account": "ACC_000002", "destination_account": "ACC_000005", "amount": 1000.0, "timestamp": t0 - timedelta(minutes=15)},
    ])

    complaint = ComplaintPayload(
        complaint_id="CMP_2026_TEST_001",
        complaint_timestamp=t0,
        reported_loss_amount=10000.0,
        fraud_type="Cyber Scams / Phishing",
        channel="UPI Transfer",
        victim_location=VictimLocation(
            state="Maharashtra",
            district="Mumbai",
            city="Mumbai",
            latitude=19.0760,
            longitude=72.8777,
        )
    )

    return accounts, txns, complaint, t0


def test_entity_resolution(sample_data):
    accounts, txns, _, _ = sample_data
    resolver = EntityResolutionEngine(accounts_df=accounts, transactions_df=txns)

    ent1 = resolver.resolve_account_entity("ACC_000001")
    assert ent1 == "ENTITY_000001"

    profile = resolver.get_account_profile("ACC_000002")
    assert profile["entity_id"] == "ENTITY_000002"
    assert "ACC_000003" in profile["linked_accounts"]


def test_money_flow_graph(sample_data):
    _, txns, _, t0 = sample_data
    graph = MoneyFlowGraphEngine(graph_edges_df=txns)

    subgraph = graph.extract_point_in_time_subgraph(["ACC_000001"], as_of_T=t0, max_hops=2)
    assert "ACC_000001" in subgraph["nodes"]
    assert "ACC_000002" in subgraph["nodes"]
    assert len(subgraph["edges"]) >= 1

    paths = graph.find_money_paths("ACC_000001", as_of_T=t0, max_hops=2)
    assert len(paths) >= 1
    assert paths[0]["nodes"][0] == "ACC_000001"


def test_fragmentation_detector(sample_data):
    _, txns, _, t0 = sample_data
    detector = TransactionFragmentationDetector(transactions_df=txns)

    res = detector.analyze_account_fragmentation("ACC_000002", as_of_T=t0, reported_loss_amount=10000.0)
    assert res["outgoing_txn_count"] == 3
    assert res["unique_destinations"] == 3
    assert res["is_fragmented"] is True


def test_mule_network_intelligence(sample_data):
    accounts, txns, _, t0 = sample_data
    resolver = EntityResolutionEngine(accounts_df=accounts, transactions_df=txns)
    graph = MoneyFlowGraphEngine(graph_edges_df=txns)
    detector = TransactionFragmentationDetector(transactions_df=txns)

    engine = MuleNetworkIntelligenceEngine(
        entity_resolver=resolver,
        graph_engine=graph,
        fragmentation_detector=detector,
    )

    mule_res = engine.evaluate_account_mule_risk("ACC_000002", "CMP_2026_TEST_001", as_of_T=t0)
    assert mule_res.mule_risk_score >= 0.40
    assert "FRAGMENTED_SPLITTING_PATTERN" in mule_res.evidence_tags
    assert mule_res.confidence in ["HIGH", "MEDIUM", "LOW"]


def test_amount_at_risk_engine(sample_data):
    _, txns, _, t0 = sample_data
    graph = MoneyFlowGraphEngine(graph_edges_df=txns)
    engine = AmountAtRiskEngine(graph_engine=graph)

    res = engine.compute_amount_at_risk("ACC_000001", reported_loss_amount=10000.0, as_of_T=t0)
    assert res.disputed_amount == 10000.0
    assert res.observed_moved_amount > 0.0
    assert res.observed_remaining_amount >= 0.0


def test_endpoint_classifier(sample_data):
    _, _, complaint, _ = sample_data
    classifier = EndpointTypeClassifier()

    probs = classifier.classify_endpoint_route(complaint)
    assert "ATM" in probs
    assert "MERCHANT" in probs
    assert "TRANSFER" in probs
    assert abs(sum(probs.values()) - 1.0) < 1e-4

    merchant_pred = classifier.generate_merchant_endpoint_prediction(complaint, probs["MERCHANT"])
    assert merchant_pred.endpoint_type == "MERCHANT"


def test_intervention_recommendation(sample_data):
    engine = InterventionRecommendationEngine()
    from src.ml.contracts.case_intelligence import AmountAtRiskSummary, MuleEntityCandidate

    amount_sum = AmountAtRiskSummary(
        disputed_amount=10000.0,
        observed_moved_amount=7000.0,
        observed_remaining_amount=3000.0,
    )
    mules = [MuleEntityCandidate(entity_id="E1", account_id="ACC_002", mule_risk_score=0.80)]

    rec = engine.generate_recommendation(
        fused_risk_score=0.82,
        amount_summary=amount_sum,
        mule_candidates=mules,
    )

    assert rec.recommended_action == "ESCALATE"
    assert rec.potential_hold_amount == 3000.0
    assert "Authorized Bank / LEA Officer Review Required" in rec.authorization_boundary

"""
Phase 4 Tests: Unified Investigation Workspace & Specialized Investigation Subsystems.
"""

import pytest
from src.services.investigation_service import InvestigationService


@pytest.fixture
def investigation_service():
    return InvestigationService()


def test_unified_investigation_workspace(investigation_service):
    # Test on a real case from dataset
    ws = investigation_service.get_case_investigation("CASE_000001")
    assert ws.case_id == "CASE_000001"
    assert ws.amount_at_risk > 0
    assert len(ws.reasons_why) > 0
    assert len(ws.timeline) > 0
    assert ws.intervention_recommendation is not None
    assert len(ws.predicted_endpoints) > 0
    assert "total_hops" in ws.money_flow_network
    assert "age_hours" in ws.sla_metrics


def test_money_flow_investigation(investigation_service):
    res = investigation_service.get_money_flow_investigation("CASE_000001", hop_limit=5)
    assert res["case_id"] == "CASE_000001"
    assert "hops" in res
    assert len(res["hops"]) > 0
    # Verify account numbers are masked
    first_hop = res["hops"][0]
    assert "••" in first_hop["from_account"] or "ACC" in first_hop["from_account"]


def test_entity_investigation(investigation_service):
    # Test with merchant entity
    res_m = investigation_service.get_entity_investigation("MERCHANT_00001")
    assert res_m["entity_type"] == "SUSPICIOUS_MERCHANT"
    assert "risk_score" in res_m

    # Test with account entity
    res_acc = investigation_service.get_entity_investigation("ACC_035263")
    assert "entity_type" in res_acc
    assert "masked_id" in res_acc


def test_network_investigation(investigation_service):
    res = investigation_service.get_network_investigation("CASE_000001", hop_depth=2)
    assert res.cluster_id == "CASE_000001"
    assert res.hop_depth == 2
    assert len(res.nodes) > 0
    assert len(res.edges) > 0
    assert len(res.evidence) > 0


def test_endpoint_investigation(investigation_service):
    res = investigation_service.get_endpoint_investigation("ATM_000308")
    assert res["endpoint_type"] == "ATM"
    assert "bank" in res
    assert "coordinates" in res


def test_case_search(investigation_service):
    results = investigation_service.search_cases(query="CASE_000001")
    assert len(results) >= 1
    assert results[0]["complaint_id"] == "CASE_000001"

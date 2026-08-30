"""
CIRIS Phase 4 — Specialized Investigation Subsystems & Operational Queue Router.
Endpoints for priority queue, operational summary, money flow paths, entity profiles,
subgraphs, and endpoint profiles.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from src.db.operational_models import (
    CaseStatus,
    InvestigationQueueResponse,
    NetworkInvestigationResponse,
    OperationalSummaryResponse,
    PriorityLevel,
)
from src.services.investigation_service import InvestigationService
from src.services.queue_service import QueueService

router = APIRouter(tags=["Investigation Subsystems & Queue"])


def get_queue_service() -> QueueService:
    return QueueService()


def get_investigation_service() -> InvestigationService:
    return InvestigationService()


# ============================================================================
# Priority Queue & Summary
# ============================================================================
@router.get("/investigation/queue", response_model=InvestigationQueueResponse, summary="Get Prioritized Investigation Queue")
def get_queue(
    priority: Optional[PriorityLevel] = Query(None, description="Filter by priority (P1-P4)"),
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned investigator"),
    endpoint_type: Optional[str] = Query(None, description="Filter by endpoint type"),
    sort_by: str = Query("priority", description="Sort by 'priority', 'risk', or 'age'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QueueService = Depends(get_queue_service)
):
    return service.get_priority_queue(
        priority=priority,
        status=status,
        assigned_to=assigned_to,
        endpoint_type=endpoint_type,
        sort_by=sort_by,
        page=page,
        page_size=page_size
    )


@router.get("/investigation/summary", response_model=OperationalSummaryResponse, summary="Get Operational Investigation Summary")
def get_summary(service: QueueService = Depends(get_queue_service)):
    return service.get_operational_summary()


# ============================================================================
# Deep-Dive Specialized Investigations
# ============================================================================
@router.get("/cases/{case_id}/money-flow/investigation", summary="Money-Flow Graph Investigation")
def get_money_flow_investigation(
    case_id: str,
    hop_limit: int = Query(5, ge=1, le=10),
    risk_only: bool = Query(False, description="Include only high-risk/cashout hops"),
    service: InvestigationService = Depends(get_investigation_service)
):
    try:
        return service.get_money_flow_investigation(case_id=case_id, hop_limit=hop_limit, risk_only=risk_only)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/entities/{entity_id}/investigation", summary="Entity Deep-Dive Investigation")
def get_entity_investigation(
    entity_id: str,
    service: InvestigationService = Depends(get_investigation_service)
):
    return service.get_entity_investigation(entity_id=entity_id)


@router.get("/networks/{cluster_id}/investigation", response_model=NetworkInvestigationResponse, summary="Network Subgraph Investigation")
def get_network_investigation(
    cluster_id: str,
    hop_depth: int = Query(2, ge=1, le=3, description="Bounded subgraph hop depth (1-3)"),
    service: InvestigationService = Depends(get_investigation_service)
):
    return service.get_network_investigation(cluster_id_or_case_id=cluster_id, hop_depth=hop_depth)


@router.get("/endpoints/{endpoint_id}/investigation", summary="Endpoint Deep-Dive Investigation")
def get_endpoint_investigation(
    endpoint_id: str,
    service: InvestigationService = Depends(get_investigation_service)
):
    return service.get_endpoint_investigation(endpoint_id=endpoint_id)

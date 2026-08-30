"""
CIRIS Phase 4 — Append-Only Forensic Audit Trail API Router.
Endpoints for audit trail inspection.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, Depends
from src.db.operational_models import AuditEvent
from src.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Forensic Audit Trail"])


def get_audit_service() -> AuditService:
    return AuditService()


@router.get("", response_model=List[AuditEvent], summary="Get System Audit Events")
def get_audit_events(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: AuditService = Depends(get_audit_service)
):
    return service.get_all_events(limit=limit, offset=offset)


@router.get("/case/{case_id}", response_model=List[AuditEvent], summary="Get Audit Trail for Case")
def get_case_audit_trail(
    case_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: AuditService = Depends(get_audit_service)
):
    return service.get_events_for_case(case_id=case_id, limit=limit)

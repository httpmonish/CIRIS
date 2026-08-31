"""
CIRIS API v1 Router Aggregator.
Aggregates GIS map endpoints and Phase 4 operational action endpoints:
Alerts, Cases, Investigations, Interventions, Audit Trail.
"""

from fastapi import APIRouter
from src.api.v1.map import router as map_router
from src.api.v1.alerts import router as alerts_router
from src.api.v1.cases import router as cases_router
from src.api.v1.investigation import router as investigation_router
from src.api.v1.interventions import router as interventions_router
from src.api.v1.audit import router as audit_router
from src.api.auth_router import router as auth_router
from src.api.complaints_rbac_router import router as complaints_rbac_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount all routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(complaints_rbac_router)
api_v1_router.include_router(map_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(cases_router)
api_v1_router.include_router(investigation_router)
api_v1_router.include_router(interventions_router)
api_v1_router.include_router(audit_router)

__all__ = [
    "api_v1_router",
    "auth_router",
    "complaints_rbac_router",
    "map_router",
    "alerts_router",
    "cases_router",
    "investigation_router",
    "interventions_router",
    "audit_router",
]

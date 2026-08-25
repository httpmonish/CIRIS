"""
System Health & Status Endpoints for CIRIS API v1.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.api.dependencies import get_db_session
from src.services.intelligence_service import IntelligenceService

router = APIRouter(tags=["System Health & Status"])


@router.get("/health")
def get_health(db: Session = Depends(get_db_session)):
    """
    Basic health check for load balancer and uptime monitoring.
    """
    db_healthy = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_healthy = False

    return {
        "status": "HEALTHY" if db_healthy else "DEGRADED",
        "database": "UP" if db_healthy else "DOWN",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/api/v1/system/status")
def get_system_status(db: Session = Depends(get_db_session)):
    """
    Detailed system component health audit (DB, ML Models, Pipeline, Graph Engine, Spatial Index, API).
    """
    from datetime import datetime

    # Check Database
    db_status = "HEALTHY"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    # Check Intelligence Engine Singleton
    intel_svc = IntelligenceService.get_instance()
    ml_ready = intel_svc.is_ready
    pipeline_status = "LOADED_ACTIVE" if ml_ready else "UNINITIALIZED_STANDALONE"
    graph_status = "ACTIVE" if (intel_svc.pipeline and intel_svc.pipeline.graph_engine) else "STANDALONE"
    spatial_status = "ACTIVE" if (intel_svc.pipeline and intel_svc.pipeline.spatial_index) else "STANDALONE"

    return {
        "system": "CIRIS Predictive Cybercrime Intelligence",
        "version": "4.0.0-phase2",
        "status": "OPERATIONAL" if (db_status == "HEALTHY" and ml_ready) else "DEGRADED_STANDALONE",
        "components": {
            "api": "ONLINE",
            "database": db_status,
            "ml_models": "FROZEN_ML_V4_LOADED" if ml_ready else "UNINITIALIZED",
            "case_pipeline": pipeline_status,
            "graph_engine": graph_status,
            "spatial_index": spatial_status,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

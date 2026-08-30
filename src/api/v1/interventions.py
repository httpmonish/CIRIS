"""
CIRIS Phase 4 — Intervention Recommendations API Router.
Endpoints for intervention recommendations and authorized officer review.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from src.db.operational_models import (
    InterventionRecord,
    InterventionReviewRequest,
)
from src.services.intervention_service import InterventionService

router = APIRouter(prefix="/interventions", tags=["Intervention Policy"])


def get_intervention_service() -> InterventionService:
    return InterventionService()


@router.post("/{intervention_id}/review", response_model=InterventionRecord, summary="Review Intervention Recommendation")
def review_intervention(
    intervention_id: str,
    req: InterventionReviewRequest,
    service: InterventionService = Depends(get_intervention_service)
):
    try:
        return service.review_intervention(
            intervention_id=intervention_id,
            reviewer=req.reviewer,
            action=req.action,
            notes=req.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

"""
Entity Resolution Endpoints for CIRIS API v1.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session
from src.services.entity_service import EntityService

router = APIRouter(prefix="/entities", tags=["Entities & Accounts"])


@router.get("/{entity_id}")
def get_entity_by_id(
    entity_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Retrieve profile details, connected accounts, UPI IDs, cards, mobile numbers,
    devices, risk scores, and mule candidate status for an entity.
    """
    svc = EntityService(db)
    profile = svc.get_entity_profile(entity_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found.")
    return profile

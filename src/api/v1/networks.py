"""
Network Graph Endpoints for CIRIS API v1.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session

router = APIRouter(prefix="/networks", tags=["Mule Networks"])


@router.get("/{network_id}")
def get_network_by_id(
    network_id: str,
    hop_depth: int = Query(2, ge=1, le=3),
    db: Session = Depends(get_db_session),
):
    """
    Get multi-hop network cluster details, entities, cases, transactions, and risk score.
    Hop depth limited to 1-3 to prevent giant graph payloads.
    """
    return {
        "network_id": network_id,
        "hop_depth": hop_depth,
        "entities": [
            {"entity_id": "ENT_001", "type": "PRIMARY_MULE", "risk": 0.85},
            {"entity_id": "ENT_002", "type": "SECONDARY_MULE", "risk": 0.72},
        ],
        "cases": ["CASE-DEMO-001"],
        "transactions": [
            {"transaction_id": "TX_1", "source": "ACC_VICTIM", "destination": "ACC_001", "amount": 50000.0},
            {"transaction_id": "TX_2", "source": "ACC_001", "destination": "ATM_9981", "amount": 35000.0},
        ],
        "risk": 0.88,
        "top_entities": ["ENT_001"],
        "evidence": [
            "Network cluster shares common device fingerprint DEV_001",
            "High degree centrality in transfer graph",
        ],
    }

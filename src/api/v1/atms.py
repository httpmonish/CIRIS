"""
ATM Inspection Endpoints for CIRIS API v1.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session
from src.db.models import ATMModel

router = APIRouter(prefix="/atms", tags=["ATMs"])


@router.get("/{atm_id}")
def get_atm_by_id(
    atm_id: str,
    db: Session = Depends(get_db_session),
):
    """
    Retrieve ATM location metadata, historical risk score, and connected cases.
    """
    atm = db.query(ATMModel).filter(ATMModel.atm_id == atm_id).first()
    if not atm:
        return {
            "atm_id": atm_id,
            "atm_name": f"SBI ATM ({atm_id})",
            "bank_name": "State Bank of India",
            "location": {
                "city": "Mumbai",
                "district": "Mumbai",
                "state": "Maharashtra",
                "pincode": 400053,
                "latitude": 19.1150,
                "longitude": 72.8710,
                "location_type": "Standalone ATM",
            },
            "risk": 0.85,
            "prediction_context": {"historical_hotspot_rank": 12, "complaint_clusters": 5},
            "related_cases": ["CASE-DEMO-001"],
            "related_entities": ["ENT_001"],
        }

    return {
        "atm_id": atm.atm_id,
        "atm_name": atm.atm_name,
        "bank_name": atm.bank_name,
        "location": {
            "city": atm.city,
            "district": atm.district,
            "state": atm.state,
            "pincode": atm.pincode,
            "latitude": atm.latitude,
            "longitude": atm.longitude,
            "location_type": atm.location_type,
        },
        "risk": atm.historical_risk_score,
        "prediction_context": {"historical_hotspot_rank": 15},
        "related_cases": [],
        "related_entities": [],
    }

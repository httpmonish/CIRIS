"""
GIS & Map GeoJSON Endpoints for CIRIS API v1.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.api.dependencies import get_db_session
from src.services.gis_service import GISService

router = APIRouter(prefix="/map", tags=["GIS & Maps"])


@router.get("/risk")
def get_risk_map_geojson(
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lng: Optional[float] = Query(None),
    max_lng: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    """
    Get GeoJSON FeatureCollection of high-risk complaint locations with viewport bounding-box filtering.
    """
    svc = GISService(db)
    return svc.get_risk_map_geojson(min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng, limit=limit)


@router.get("/predicted-atms")
def get_predicted_atms_geojson(
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lng: Optional[float] = Query(None),
    max_lng: Optional[float] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    """
    Get GeoJSON FeatureCollection of predicted high-probability ATM cashout locations with viewport filtering.
    """
    svc = GISService(db)
    return svc.get_predicted_atms_geojson(min_lat=min_lat, max_lat=max_lat, min_lng=min_lng, max_lng=max_lng, limit=limit)


@router.get("/networks")
def get_networks_geojson(
    case_id: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """
    Get GeoJSON FeatureCollection of network entity locations.
    """
    svc = GISService(db)
    return svc.get_networks_geojson(case_id=case_id)


@router.get("/cases")
def get_cases_geojson(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db_session),
):
    """
    Get GeoJSON FeatureCollection of active cases.
    """
    svc = GISService(db)
    return svc.get_cases_geojson(limit=limit)

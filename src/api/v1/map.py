"""
CIRIS GIS & Map Data API Endpoints (Phase 3A).
FastAPI router providing GeoJSON endpoints for cases, predicted cashout ATMs,
risk clusters, money flow networks, merchants, nearby spatial queries, and viewport data.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel

from src.db.geo_models import BoundingBox
from src.services.gis_service import GISService

router = APIRouter(prefix="/map", tags=["GIS & Map Engine"])

# Dependency to provide GISService instance
def get_gis_service() -> GISService:
    return GISService()


# ============================================================================
# 1. Cases Map Endpoint
# ============================================================================
@router.get(
    "/cases",
    summary="Get Case Incident Locations (GeoJSON)",
    description="Returns reported cybercrime victim locations as GeoJSON Point features with spatial and attribute filtering."
)
def get_cases(
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Bounding box min latitude"),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Bounding box min longitude"),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Bounding box max latitude"),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Bounding box max longitude"),
    center_lat: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Center latitude for radius query"),
    center_lon: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Center longitude for radius query"),
    radius_km: Optional[float] = Query(None, gt=0.0, le=500.0, description="Search radius in kilometers"),
    fraud_type: Optional[str] = Query(None, description="Filter by fraud type e.g., 'UPI Fraud', 'OTP Fraud'"),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum reported loss amount"),
    max_amount: Optional[float] = Query(None, ge=0.0, description="Maximum reported loss amount"),
    min_urgency: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum urgency score (0.0 - 1.0)"),
    state: Optional[str] = Query(None, description="Victim state filter"),
    city: Optional[str] = Query(None, description="Victim city filter"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum cases to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    cluster: bool = Query(False, description="Enable spatial grid clustering for low zoom levels"),
    zoom: Optional[int] = Query(None, ge=1, le=22, description="Current map zoom level for auto-clustering"),
    gis_service: GISService = Depends(get_gis_service)
):
    bbox = None
    if None not in (min_lat, min_lon, max_lat, max_lon):
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    return gis_service.get_cases_geojson(
        bbox=bbox,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        fraud_type=fraud_type,
        min_amount=min_amount,
        max_amount=max_amount,
        min_urgency=min_urgency,
        state=state,
        city=city,
        limit=limit,
        offset=offset,
        cluster=cluster,
        zoom=zoom
    )


# ============================================================================
# 2. Predicted ATMs Map Endpoint
# ============================================================================
@router.get(
    "/predicted-atms",
    summary="Get Top-10 Ranked Shortlist ATMs (GeoJSON)",
    description="Returns ranked candidate ATMs narrowed down from 7,000 national terminals with confidence tiers, SHAP explainability, and calibrated time windows."
)
def get_predicted_atms(
    complaint_id: Optional[str] = Query(None, description="Filter predictions by specific Complaint ID"),
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    center_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    center_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0.0, le=500.0),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum ML prediction score"),
    top_k: Optional[int] = Query(None, ge=1, le=20, description="Filter to top K ranked ATMs per case"),
    bank: Optional[str] = Query(None, description="Filter by bank name"),
    limit: int = Query(500, ge=1, le=2000),
    gis_service: GISService = Depends(get_gis_service)
):
    bbox = None
    if None not in (min_lat, min_lon, max_lat, max_lon):
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    return gis_service.get_predicted_atms_geojson(
        complaint_id=complaint_id,
        bbox=bbox,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        min_score=min_score,
        top_k=top_k,
        bank=bank,
        limit=limit
    )


# ============================================================================
# 3. Risk Heatmap & Risk Clusters Map Endpoint
# ============================================================================
@router.get(
    "/risk",
    summary="Get Geographic Risk Heatmap & Zones (GeoJSON)",
    description="Returns risk centroid points and risk zone polygons with composite threat scores."
)
def get_risk(
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    center_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    center_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0.0, le=500.0),
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum risk score threshold"),
    grid_resolution: Optional[str] = Query(None, description="Optional grid resolution"),
    gis_service: GISService = Depends(get_gis_service)
):
    bbox = None
    if None not in (min_lat, min_lon, max_lat, max_lon):
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    return gis_service.get_risk_heatmap_geojson(
        bbox=bbox,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        min_risk=min_risk,
        grid_resolution=grid_resolution
    )


# ============================================================================
# 4. Money Flow Networks Map Endpoint
# ============================================================================
@router.get(
    "/networks",
    summary="Get Money Flow Network Trajectories (GeoJSON)",
    description="Returns geographic LineString trajectories representing mule fragmentation hops and Point nodes."
)
def get_networks(
    complaint_id: Optional[str] = Query(None, description="Case ID to trace money flow trajectory"),
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum transaction amount to include"),
    include_nodes: bool = Query(True, description="Include account Point features alongside LineStrings"),
    include_edges: bool = Query(True, description="Include flow LineString features"),
    limit: int = Query(200, ge=1, le=1000),
    gis_service: GISService = Depends(get_gis_service)
):
    bbox = None
    if None not in (min_lat, min_lon, max_lat, max_lon):
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    return gis_service.get_networks_geojson(
        complaint_id=complaint_id,
        bbox=bbox,
        min_amount=min_amount,
        include_nodes=include_nodes,
        include_edges=include_edges,
        limit=limit
    )


# ============================================================================
# 5. Suspicious Merchants Map Endpoint
# ============================================================================
@router.get(
    "/merchants",
    summary="Get Suspicious Merchants & High-Risk POS (GeoJSON)",
    description="Returns crypto P2P desks, bullion dealers, and remittance outlets used for fund dispersion."
)
def get_merchants(
    min_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    min_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    max_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    max_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    center_lat: Optional[float] = Query(None, ge=-90.0, le=90.0),
    center_lon: Optional[float] = Query(None, ge=-180.0, le=180.0),
    radius_km: Optional[float] = Query(None, gt=0.0, le=500.0),
    min_risk: Optional[float] = Query(None, ge=0.0, le=1.0),
    category: Optional[str] = Query(None, description="Merchant category filter"),
    limit: int = Query(500, ge=1, le=2000),
    gis_service: GISService = Depends(get_gis_service)
):
    bbox = None
    if None not in (min_lat, min_lon, max_lat, max_lon):
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)

    return gis_service.get_merchants_geojson(
        bbox=bbox,
        center_lat=center_lat,
        center_lon=center_lon,
        radius_km=radius_km,
        min_risk=min_risk,
        category=category,
        limit=limit
    )


# ============================================================================
# 6. Unified Nearby Entities Endpoint
# ============================================================================
@router.get(
    "/nearby",
    summary="Unified Nearby Entities Search (GeoJSON)",
    description="Finds all cases, predicted ATMs, hotspots, and merchants within radius_km of a selected coordinate, sorted by distance."
)
def get_nearby(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Center latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Center longitude"),
    radius_km: float = Query(5.0, gt=0.0, le=100.0, description="Search radius in kilometers"),
    types: Optional[List[str]] = Query(None, description="Filter entity types: CASES, ATMS, PREDICTED_ATMS, MERCHANTS, HOTSPOTS"),
    limit: int = Query(100, ge=1, le=500),
    gis_service: GISService = Depends(get_gis_service)
):
    return gis_service.get_nearby_entities(
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        entity_types=types,
        limit=limit
    )


# ============================================================================
# 7. Unified Viewport Endpoint
# ============================================================================
@router.get(
    "/viewport",
    summary="Multi-Layer Map Viewport Query",
    description="Returns all active layers within the current map bounding box for unified rendering."
)
def get_viewport(
    min_lat: float = Query(..., ge=-90.0, le=90.0),
    min_lon: float = Query(..., ge=-180.0, le=180.0),
    max_lat: float = Query(..., ge=-90.0, le=90.0),
    max_lon: float = Query(..., ge=-180.0, le=180.0),
    zoom: int = Query(10, ge=1, le=22, description="Current map zoom level"),
    layers: Optional[List[str]] = Query(None, description="Comma-separated or list of layers: cases, predicted_atms, risk, networks, merchants"),
    gis_service: GISService = Depends(get_gis_service)
):
    if min_lat > max_lat or min_lon > max_lon:
        raise HTTPException(status_code=400, detail="Invalid bounding box coordinates (min > max)")

    return gis_service.get_viewport_data(
        min_lat=min_lat,
        min_lon=min_lon,
        max_lat=max_lat,
        max_lon=max_lon,
        zoom=zoom,
        layers=layers
    )


# ============================================================================
# 8. Layer Definitions Metadata Endpoint
# ============================================================================
@router.get(
    "/layers",
    summary="Get Map Layer Definitions & Symbology",
    description="Returns metadata, color schemas, zoom thresholds, and filter fields for all GIS layers."
)
def get_layers():
    return GISService.get_map_layer_definitions()


# ============================================================================
# 9. GIS Summary Stats Endpoint
# ============================================================================
@router.get(
    "/stats",
    summary="Get Geospatial Summary Statistics",
    description="Returns counts of mapped cases, ATMs, predictions, network flows, and the geographic envelope."
)
def get_stats(gis_service: GISService = Depends(get_gis_service)):
    return gis_service.get_gis_stats()

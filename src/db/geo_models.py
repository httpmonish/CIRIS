"""
CIRIS GIS Geospatial Domain & GeoJSON (RFC 7946) Models.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field


# ============================================================================
# Core Coordinate & Bounding Box Models
# ============================================================================

class GeoPoint(BaseModel):
    """Geographic point coordinate (WGS84). Note: GeoJSON ordering is [longitude, latitude]."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")

    def to_geojson_coords(self) -> List[float]:
        """Return [lon, lat] for GeoJSON compliance."""
        return [round(self.longitude, 6), round(self.latitude, 6)]


class BoundingBox(BaseModel):
    """Geographic bounding box for viewport and spatial envelope queries."""
    min_lat: float = Field(..., ge=-90.0, le=90.0, description="Minimum latitude (South)")
    min_lon: float = Field(..., ge=-180.0, le=180.0, description="Minimum longitude (West)")
    max_lat: float = Field(..., ge=-90.0, le=90.0, description="Maximum latitude (North)")
    max_lon: float = Field(..., ge=-180.0, le=180.0, description="Maximum longitude (East)")

    def validate_bounds(self) -> bool:
        return self.min_lat <= self.max_lat and self.min_lon <= self.max_lon

    def to_bbox_array(self) -> List[float]:
        """Return [min_lon, min_lat, max_lon, max_lat] according to RFC 7946."""
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


class RadiusQuery(BaseModel):
    """Geographic center point and search radius."""
    center_lat: float = Field(..., ge=-90.0, le=90.0)
    center_lon: float = Field(..., ge=-180.0, le=180.0)
    radius_km: float = Field(default=5.0, gt=0.0, le=500.0, description="Radius in kilometers")


# ============================================================================
# GeoJSON Specification (RFC 7946) Models
# ============================================================================

class GeoJSONGeometryPoint(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: List[float] = Field(..., description="[longitude, latitude]")


class GeoJSONGeometryLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: List[List[float]] = Field(..., description="List of [longitude, latitude] coordinates")


class GeoJSONGeometryPolygon(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]] = Field(..., description="Linear rings of [longitude, latitude]")


GeoJSONGeometry = Union[GeoJSONGeometryPoint, GeoJSONGeometryLineString, GeoJSONGeometryPolygon]


class GeoJSONFeature(BaseModel):
    """A standard GeoJSON Feature."""
    type: Literal["Feature"] = "Feature"
    id: Optional[Union[str, int]] = None
    geometry: GeoJSONGeometry
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    """A standard GeoJSON FeatureCollection."""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)
    bbox: Optional[List[float]] = Field(None, description="[min_lon, min_lat, max_lon, max_lat]")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ============================================================================
# Domain GIS Entity Models
# ============================================================================

class CaseGeoRecord(BaseModel):
    complaint_id: str
    complaint_timestamp: Optional[str] = None
    incident_timestamp: Optional[str] = None
    fraud_type: str
    channel: Optional[str] = None
    reported_loss_amount: float = 0.0
    victim_state: Optional[str] = None
    victim_district: Optional[str] = None
    victim_city: Optional[str] = None
    victim_area: Optional[str] = None
    victim_pincode: Optional[str] = None
    victim_lat: float
    victim_lon: float
    victim_rural_urban: Optional[str] = None
    victim_bank: Optional[str] = None
    urgency_score: float = 0.0
    fraud_category: Optional[str] = None


class AtmGeoRecord(BaseModel):
    atm_id: str
    atm_name: Optional[str] = None
    bank_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    pincode: Optional[str] = None
    latitude: float
    longitude: float
    location_type: Optional[str] = None
    historical_cashouts: int = 0
    historical_loss: float = 0.0
    hotspot_score: float = 0.0


class PredictedAtmGeoRecord(BaseModel):
    complaint_id: str
    atm_id: str
    atm_name: Optional[str] = None
    bank_name: Optional[str] = None
    prediction_timestamp: Optional[str] = None
    rank_order: int
    prediction_score: float
    confidence_level: str
    time_window_label: Optional[str] = None
    withdrawal_delay_hours: Optional[float] = None
    victim_lat: Optional[float] = None
    victim_lon: Optional[float] = None
    atm_lat: float
    atm_lon: float
    distance_km: Optional[float] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    location_type: Optional[str] = None
    is_ground_truth: bool = False


class MoneyFlowGeoRecord(BaseModel):
    complaint_id: str
    edge_id: Optional[str] = None
    src_account_id: str
    dst_account_id: str
    amount: float
    channel: Optional[str] = None
    timestamp: Optional[str] = None
    hop_level: int = 1
    src_lat: Optional[float] = None
    src_lon: Optional[float] = None
    dst_lat: Optional[float] = None
    dst_lon: Optional[float] = None
    is_cashout_mule: bool = False


class MerchantGeoRecord(BaseModel):
    entity_id: str
    entity_type: str
    name: str
    category: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    latitude: float
    longitude: float
    risk_score: float = 0.0
    linked_case_count: int = 0
    total_suspicious_volume: float = 0.0


class RiskHotspotGeoRecord(BaseModel):
    hotspot_id: str
    name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    center_lat: float
    center_lon: float
    radius_km: float = 5.0
    risk_level: str
    risk_score: float = 0.0
    case_count: int = 0
    total_loss: float = 0.0
    active_mule_accounts: int = 0


# ============================================================================
# Map Layer Metadata Models
# ============================================================================

class MapLayerStyle(BaseModel):
    color: str
    fill_color: Optional[str] = None
    fill_opacity: Optional[float] = None
    stroke_width: Optional[float] = None
    radius: Optional[float] = None
    icon: Optional[str] = None


class MapLayerDefinition(BaseModel):
    id: str
    name: str
    description: str
    geometry_type: Literal["Point", "LineString", "Polygon", "Heatmap"]
    min_zoom: int = 1
    max_zoom: int = 22
    default_visible: bool = True
    style: MapLayerStyle
    filter_properties: List[str]
    source_endpoint: str

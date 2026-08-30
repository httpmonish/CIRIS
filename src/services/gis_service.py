"""
CIRIS GIS Service Engine.
Provides spatial querying, bounding-box viewport filtering, radius queries,
k-nearest-neighbor search, dynamic zoom clustering, and GeoJSON (RFC 7946) generation.
"""

import math
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union
from shapely.geometry import Point, LineString, Polygon, mapping

from src.db.database import get_db_connection, get_db_path, create_connection
from src.db.geo_models import (
    BoundingBox,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    MapLayerDefinition,
    MapLayerStyle,
)

logger = logging.getLogger("ciris.gis.service")


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in kilometers between two coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def create_circle_polygon(center_lat: float, center_lon: float, radius_km: float, num_points: int = 32) -> List[List[float]]:
    """Generate GeoJSON Polygon coordinates approximating a geodesic circle."""
    coords = []
    # Degrees per km approximation
    lat_deg_per_km = 1.0 / 111.0
    lon_deg_per_km = 1.0 / (111.0 * max(0.01, math.cos(math.radians(center_lat))))

    for i in range(num_points):
        angle = (2 * math.pi * i) / num_points
        d_lat = radius_km * lat_deg_per_km * math.sin(angle)
        d_lon = radius_km * lon_deg_per_km * math.cos(angle)
        coords.append([round(center_lon + d_lon, 6), round(center_lat + d_lat, 6)])

    # Close linear ring
    coords.append(coords[0])
    return [coords]


class GISService:
    """High-performance GIS query engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    # =========================================================================
    # 1. Cases / Complaints GIS Queries
    # =========================================================================
    def get_cases_geojson(
        self,
        bbox: Optional[BoundingBox] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        fraud_type: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        min_urgency: Optional[float] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
        cluster: bool = False,
        zoom: Optional[int] = None
    ) -> Dict[str, Any]:
        """Retrieve case incident locations as GeoJSON FeatureCollection with spatial filtering and optional clustering."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []

            # Spatial R*Tree Bounding Box Filter
            if bbox and bbox.validate_bounds():
                cursor.execute("""
                SELECT id FROM rtree_cases_idx
                WHERE min_lon >= ? AND max_lon <= ? AND min_lat >= ? AND max_lat <= ?
                """, (bbox.min_lon, bbox.max_lon, bbox.min_lat, bbox.max_lat))
                matched_ids = [r[0] for r in cursor.fetchall()]
                if not matched_ids:
                    return GeoJSONFeatureCollection(features=[], bbox=bbox.to_bbox_array()).model_dump()
                
                placeholders = ",".join("?" for _ in matched_ids)
                conditions.append(f"c.id IN ({placeholders})")
                params.extend(matched_ids)

            # Attribute Filters
            if fraud_type:
                conditions.append("c.fraud_type = ?")
                params.append(fraud_type)
            if min_amount is not None:
                conditions.append("c.reported_loss_amount >= ?")
                params.append(min_amount)
            if max_amount is not None:
                conditions.append("c.reported_loss_amount <= ?")
                params.append(max_amount)
            if min_urgency is not None:
                conditions.append("c.urgency_score >= ?")
                params.append(min_urgency)
            if state:
                conditions.append("c.victim_state = ?")
                params.append(state)
            if city:
                conditions.append("c.victim_city = ?")
                params.append(city)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # Fetch candidate cases
            query = f"""
            SELECT c.id, c.complaint_id, c.complaint_timestamp, c.incident_timestamp,
                   c.fraud_type, c.channel, c.reported_loss_amount, c.victim_state,
                   c.victim_district, c.victim_city, c.victim_area, c.victim_pincode,
                   c.victim_lat, c.victim_lon, c.victim_rural_urban, c.victim_bank,
                   c.urgency_score, c.fraud_category
            FROM geo_cases c
            {where_clause}
            ORDER BY c.urgency_score DESC, c.reported_loss_amount DESC
            LIMIT ? OFFSET ?;
            """
            params.extend([limit if not radius_km else limit * 5, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()

            features = []
            min_lon, min_lat, max_lon, max_lat = 180.0, 90.0, -180.0, -90.0

            # Filter by radius if requested
            filtered_rows = []
            for row in rows:
                v_lat = float(row["victim_lat"])
                v_lon = float(row["victim_lon"])
                
                if center_lat is not None and center_lon is not None and radius_km is not None:
                    dist = haversine_distance_km(center_lat, center_lon, v_lat, v_lon)
                    if dist > radius_km:
                        continue

                filtered_rows.append(row)
                if len(filtered_rows) >= limit:
                    break

            # Clustering mode check
            should_cluster = cluster or (zoom is not None and zoom <= 11 and len(filtered_rows) > 50)
            if should_cluster and zoom is not None:
                return self._cluster_cases(filtered_rows, zoom=zoom)

            for row in filtered_rows:
                v_lat = float(row["victim_lat"])
                v_lon = float(row["victim_lon"])
                
                min_lon = min(min_lon, v_lon)
                min_lat = min(min_lat, v_lat)
                max_lon = max(max_lon, v_lon)
                max_lat = max(max_lat, v_lat)

                feature = GeoJSONFeature(
                    id=row["complaint_id"],
                    geometry={"type": "Point", "coordinates": [round(v_lon, 6), round(v_lat, 6)]},
                    properties={
                        "complaint_id": row["complaint_id"],
                        "complaint_timestamp": row["complaint_timestamp"],
                        "incident_timestamp": row["incident_timestamp"],
                        "fraud_type": row["fraud_type"],
                        "channel": row["channel"],
                        "reported_loss_amount": float(row["reported_loss_amount"]),
                        "victim_state": row["victim_state"],
                        "victim_district": row["victim_district"],
                        "victim_city": row["victim_city"],
                        "victim_area": row["victim_area"],
                        "victim_pincode": row["victim_pincode"],
                        "victim_bank": row["victim_bank"],
                        "victim_rural_urban": row["victim_rural_urban"],
                        "urgency_score": float(row["urgency_score"]),
                        "fraud_category": row["fraud_category"],
                        "risk_level": "CRITICAL" if row["urgency_score"] >= 0.75 else ("HIGH" if row["urgency_score"] >= 0.5 else "MEDIUM"),
                    }
                )
                features.append(feature)

            bbox_arr = [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)] if features else None
            
            return GeoJSONFeatureCollection(
                features=features,
                bbox=bbox_arr,
                metadata={"total_returned": len(features), "limit": limit, "offset": offset}
            ).model_dump()

    def _cluster_cases(self, rows: List[sqlite3.Row], zoom: int) -> Dict[str, Any]:
        """Perform dynamic spatial grid clustering for cases at low zoom levels."""
        # Grid cell size in degrees based on zoom level
        grid_size = 360.0 / (2 ** zoom * 4.0)
        
        clusters: Dict[Tuple[int, int], Dict[str, Any]] = {}
        
        for row in rows:
            lat = float(row["victim_lat"])
            lon = float(row["victim_lon"])
            loss = float(row["reported_loss_amount"])
            urg = float(row["urgency_score"])

            grid_x = int(math.floor(lon / grid_size))
            grid_y = int(math.floor(lat / grid_size))
            grid_key = (grid_x, grid_y)

            if grid_key not in clusters:
                clusters[grid_key] = {
                    "count": 0,
                    "sum_lat": 0.0,
                    "sum_lon": 0.0,
                    "total_loss": 0.0,
                    "max_urgency": 0.0,
                    "fraud_types": set(),
                    "sample_complaints": []
                }

            c = clusters[grid_key]
            c["count"] += 1
            c["sum_lat"] += lat
            c["sum_lon"] += lon
            c["total_loss"] += loss
            c["max_urgency"] = max(c["max_urgency"], urg)
            c["fraud_types"].add(row["fraud_type"])
            if len(c["sample_complaints"]) < 5:
                c["sample_complaints"].append(row["complaint_id"])

        features = []
        for (gx, gy), data in clusters.items():
            count = data["count"]
            avg_lat = data["sum_lat"] / count
            avg_lon = data["sum_lon"] / count
            
            if count == 1:
                feature = GeoJSONFeature(
                    id=data["sample_complaints"][0],
                    geometry={"type": "Point", "coordinates": [round(avg_lon, 6), round(avg_lat, 6)]},
                    properties={
                        "complaint_id": data["sample_complaints"][0],
                        "cluster": False,
                        "reported_loss_amount": round(data["total_loss"], 2),
                        "urgency_score": round(data["max_urgency"], 3),
                    }
                )
            else:
                feature = GeoJSONFeature(
                    id=f"cluster_{gx}_{gy}",
                    geometry={"type": "Point", "coordinates": [round(avg_lon, 6), round(avg_lat, 6)]},
                    properties={
                        "cluster": True,
                        "cluster_id": f"c_{gx}_{gy}",
                        "point_count": count,
                        "point_count_abbreviated": f"{count // 1000}k" if count >= 1000 else str(count),
                        "total_loss": round(data["total_loss"], 2),
                        "max_urgency": round(data["max_urgency"], 3),
                        "fraud_types": list(data["fraud_types"]),
                        "sample_complaints": data["sample_complaints"],
                    }
                )
            features.append(feature)

        return GeoJSONFeatureCollection(
            features=features,
            metadata={"clustered": True, "zoom": zoom, "cluster_count": len(features)}
        ).model_dump()

    # =========================================================================
    # 2. Predicted ATM Geographic Intelligence
    # =========================================================================
    def get_predicted_atms_geojson(
        self,
        complaint_id: Optional[str] = None,
        bbox: Optional[BoundingBox] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_score: Optional[float] = None,
        top_k: Optional[int] = None,
        bank: Optional[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """Retrieve predicted ATM cash-out targets with ranking, ML confidence, and distance."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []

            if complaint_id:
                conditions.append("p.complaint_id = ?")
                params.append(complaint_id)

            if top_k is not None:
                conditions.append("p.rank_order <= ?")
                params.append(top_k)

            if min_score is not None:
                conditions.append("p.prediction_score >= ?")
                params.append(min_score)

            if bank:
                conditions.append("a.bank_name = ?")
                params.append(bank)

            if bbox and bbox.validate_bounds():
                cursor.execute("""
                SELECT id FROM rtree_predicted_atms_idx
                WHERE min_lon >= ? AND max_lon <= ? AND min_lat >= ? AND max_lat <= ?
                """, (bbox.min_lon, bbox.max_lon, bbox.min_lat, bbox.max_lat))
                matched_ids = [r[0] for r in cursor.fetchall()]
                if not matched_ids:
                    return GeoJSONFeatureCollection(features=[], bbox=bbox.to_bbox_array()).model_dump()
                placeholders = ",".join("?" for _ in matched_ids)
                conditions.append(f"p.id IN ({placeholders})")
                params.extend(matched_ids)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
            SELECT p.id, p.complaint_id, p.atm_id, p.prediction_timestamp,
                   p.rank_order, p.prediction_score, p.confidence_level,
                   p.time_window_label, p.withdrawal_delay_hours,
                   p.victim_lat, p.victim_lon, p.atm_lat, p.atm_lon,
                   p.distance_km, p.is_ground_truth,
                   a.atm_name, a.bank_name, a.state, a.district, a.city, a.area,
                   a.pincode, a.location_type, a.historical_cashouts, a.hotspot_score
            FROM geo_predicted_atms p
            JOIN geo_atms a ON p.atm_id = a.atm_id
            {where_clause}
            ORDER BY p.rank_order ASC, p.prediction_score DESC
            LIMIT ?;
            """
            params.append(limit if not radius_km else limit * 5)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            features = []
            min_lon, min_lat, max_lon, max_lat = 180.0, 90.0, -180.0, -90.0

            for row in rows:
                a_lat = float(row["atm_lat"])
                a_lon = float(row["atm_lon"])

                if center_lat is not None and center_lon is not None and radius_km is not None:
                    dist = haversine_distance_km(center_lat, center_lon, a_lat, a_lon)
                    if dist > radius_km:
                        continue

                min_lon = min(min_lon, a_lon)
                min_lat = min(min_lat, a_lat)
                max_lon = max(max_lon, a_lon)
                max_lat = max(max_lat, a_lat)

                feature = GeoJSONFeature(
                    id=f"pred_{row['complaint_id']}_{row['atm_id']}",
                    geometry={"type": "Point", "coordinates": [round(a_lon, 6), round(a_lat, 6)]},
                    properties={
                        "complaint_id": row["complaint_id"],
                        "atm_id": row["atm_id"],
                        "atm_name": row["atm_name"],
                        "bank_name": row["bank_name"],
                        "rank": int(row["rank_order"]),
                        "prediction_score": float(row["prediction_score"]),
                        "confidence_level": row["confidence_level"],
                        "time_window_label": row["time_window_label"],
                        "withdrawal_delay_hours": float(row["withdrawal_delay_hours"] or 0.0),
                        "distance_km": round(float(row["distance_km"] or 0.0), 2),
                        "city": row["city"],
                        "district": row["district"],
                        "state": row["state"],
                        "area": row["area"],
                        "pincode": row["pincode"],
                        "location_type": row["location_type"],
                        "historical_cashouts": int(row["historical_cashouts"] or 0),
                        "hotspot_score": float(row["hotspot_score"] or 0.0),
                        "is_ground_truth": bool(row["is_ground_truth"]),
                        "priority": "CRITICAL" if row["rank_order"] == 1 else ("HIGH" if row["rank_order"] <= 3 else "STANDARD")
                    }
                )
                features.append(feature)
                if len(features) >= limit:
                    break

            bbox_arr = [round(min_lon, 6), round(min_lat, 6), round(max_lon, 6), round(max_lat, 6)] if features else None

            return GeoJSONFeatureCollection(
                features=features,
                bbox=bbox_arr,
                metadata={"total_predictions": len(features), "complaint_id": complaint_id}
            ).model_dump()

    # =========================================================================
    # 3. Geographic Risk Heatmap & Risk Clusters
    # =========================================================================
    def get_risk_heatmap_geojson(
        self,
        bbox: Optional[BoundingBox] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_risk: Optional[float] = None,
        grid_resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve risk heatmap points and risk zone polygons."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []

            if min_risk is not None:
                conditions.append("h.risk_score >= ?")
                params.append(min_risk)

            if bbox and bbox.validate_bounds():
                cursor.execute("""
                SELECT id FROM rtree_risk_hotspots_idx
                WHERE min_lon >= ? AND max_lon <= ? AND min_lat >= ? AND max_lat <= ?
                """, (bbox.min_lon, bbox.max_lon, bbox.min_lat, bbox.max_lat))
                matched_ids = [r[0] for r in cursor.fetchall()]
                if not matched_ids:
                    return GeoJSONFeatureCollection(features=[], bbox=bbox.to_bbox_array()).model_dump()
                placeholders = ",".join("?" for _ in matched_ids)
                conditions.append(f"h.id IN ({placeholders})")
                params.extend(matched_ids)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
            SELECT h.hotspot_id, h.name, h.state, h.district, h.city,
                   h.center_lat, h.center_lon, h.radius_km, h.risk_level,
                   h.risk_score, h.case_count, h.total_loss, h.active_mule_accounts
            FROM geo_risk_hotspots h
            {where_clause}
            ORDER BY h.risk_score DESC;
            """
            cursor.execute(query, params)
            rows = cursor.fetchall()

            features = []
            for row in rows:
                c_lat = float(row["center_lat"])
                c_lon = float(row["center_lon"])
                r_km = float(row["radius_km"])

                if center_lat is not None and center_lon is not None and radius_km is not None:
                    dist = haversine_distance_km(center_lat, center_lon, c_lat, c_lon)
                    if dist > (radius_km + r_km):
                        continue

                # Point feature for heatmap centroid
                point_feature = GeoJSONFeature(
                    id=f"{row['hotspot_id']}_point",
                    geometry={"type": "Point", "coordinates": [round(c_lon, 6), round(c_lat, 6)]},
                    properties={
                        "hotspot_id": row["hotspot_id"],
                        "name": row["name"],
                        "city": row["city"],
                        "state": row["state"],
                        "risk_score": float(row["risk_score"]),
                        "risk_level": row["risk_level"],
                        "case_count": int(row["case_count"]),
                        "total_loss": float(row["total_loss"]),
                        "active_mule_accounts": int(row["active_mule_accounts"]),
                        "radius_km": r_km,
                        "feature_type": "HOTSPOT_CENTROID"
                    }
                )
                features.append(point_feature)

                # Polygon boundary for the risk zone
                poly_coords = create_circle_polygon(c_lat, c_lon, r_km, num_points=32)
                poly_feature = GeoJSONFeature(
                    id=f"{row['hotspot_id']}_zone",
                    geometry={"type": "Polygon", "coordinates": poly_coords},
                    properties={
                        "hotspot_id": row["hotspot_id"],
                        "name": row["name"],
                        "city": row["city"],
                        "state": row["state"],
                        "risk_score": float(row["risk_score"]),
                        "risk_level": row["risk_level"],
                        "case_count": int(row["case_count"]),
                        "total_loss": float(row["total_loss"]),
                        "radius_km": r_km,
                        "feature_type": "HOTSPOT_POLYGON"
                    }
                )
                features.append(poly_feature)

            return GeoJSONFeatureCollection(
                features=features,
                metadata={"hotspots_count": len(rows), "total_features": len(features)}
            ).model_dump()

    # =========================================================================
    # 4. Money Flow Network Geographic Paths
    # =========================================================================
    def get_networks_geojson(
        self,
        complaint_id: Optional[str] = None,
        bbox: Optional[BoundingBox] = None,
        min_amount: Optional[float] = None,
        include_nodes: bool = True,
        include_edges: bool = True,
        limit: int = 200
    ) -> Dict[str, Any]:
        """Retrieve geographic money flow trajectories (LineStrings) and account nodes (Points)."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []

            if complaint_id:
                conditions.append("n.complaint_id = ?")
                params.append(complaint_id)

            if min_amount is not None:
                conditions.append("n.amount >= ?")
                params.append(min_amount)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
            SELECT n.id, n.complaint_id, n.edge_id, n.src_account_id, n.dst_account_id,
                   n.amount, n.channel, n.timestamp, n.hop_level,
                   n.src_lat, n.src_lon, n.dst_lat, n.dst_lon, n.is_cashout_mule
            FROM geo_network_flows n
            {where_clause}
            ORDER BY n.complaint_id, n.hop_level ASC
            LIMIT ?;
            """
            params.append(limit)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            features = []
            visited_nodes: Dict[str, Tuple[float, float, str, int]] = {}

            for row in rows:
                src_lat = float(row["src_lat"] or 0.0)
                src_lon = float(row["src_lon"] or 0.0)
                dst_lat = float(row["dst_lat"] or 0.0)
                dst_lon = float(row["dst_lon"] or 0.0)
                
                # Check bounding box intersection if bbox is specified
                if bbox and bbox.validate_bounds():
                    in_src = (bbox.min_lat <= src_lat <= bbox.max_lat and bbox.min_lon <= src_lon <= bbox.max_lon)
                    in_dst = (bbox.min_lat <= dst_lat <= bbox.max_lat and bbox.min_lon <= dst_lon <= bbox.max_lon)
                    if not (in_src or in_dst):
                        continue

                # Add LineString Edge Feature
                if include_edges:
                    edge_feature = GeoJSONFeature(
                        id=f"flow_{row['id']}",
                        geometry={
                            "type": "LineString",
                            "coordinates": [
                                [round(src_lon, 6), round(src_lat, 6)],
                                [round(dst_lon, 6), round(dst_lat, 6)]
                            ]
                        },
                        properties={
                            "complaint_id": row["complaint_id"],
                            "edge_id": row["edge_id"],
                            "from_account": row["src_account_id"],
                            "to_account": row["dst_account_id"],
                            "amount": float(row["amount"]),
                            "channel": row["channel"],
                            "timestamp": row["timestamp"],
                            "hop_level": int(row["hop_level"]),
                            "is_cashout_mule": bool(row["is_cashout_mule"]),
                            "feature_type": "MONEY_FLOW_EDGE"
                        }
                    )
                    features.append(edge_feature)

                # Collect Nodes
                if include_nodes:
                    visited_nodes[row["src_account_id"]] = (src_lat, src_lon, "SOURCE_MULE" if row["hop_level"] > 1 else "VICTIM_ACCOUNT", int(row["hop_level"]))
                    dst_role = "CASHOUT_ENDPOINT" if row["is_cashout_mule"] else "INTERMEDIARY_MULE"
                    visited_nodes[row["dst_account_id"]] = (dst_lat, dst_lon, dst_role, int(row["hop_level"]) + 1)

            # Add Node Points
            if include_nodes:
                for acc_id, (n_lat, n_lon, role, hop) in visited_nodes.items():
                    node_feature = GeoJSONFeature(
                        id=f"node_{acc_id}",
                        geometry={"type": "Point", "coordinates": [round(n_lon, 6), round(n_lat, 6)]},
                        properties={
                            "account_id": acc_id,
                            "role": role,
                            "hop_level": hop,
                            "is_cashout": (role == "CASHOUT_ENDPOINT"),
                            "feature_type": "ACCOUNT_NODE"
                        }
                    )
                    features.append(node_feature)

            return GeoJSONFeatureCollection(
                features=features,
                metadata={"edge_count": len(rows), "node_count": len(visited_nodes)}
            ).model_dump()

    # =========================================================================
    # 5. Suspicious Merchants & Points of Sale
    # =========================================================================
    def get_merchants_geojson(
        self,
        bbox: Optional[BoundingBox] = None,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        radius_km: Optional[float] = None,
        min_risk: Optional[float] = None,
        category: Optional[str] = None,
        limit: int = 500
    ) -> Dict[str, Any]:
        """Retrieve suspicious merchants, P2P desks, and high-risk POS outlets."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            conditions = []
            params = []

            if min_risk is not None:
                conditions.append("m.risk_score >= ?")
                params.append(min_risk)

            if category:
                conditions.append("m.category = ?")
                params.append(category)

            if bbox and bbox.validate_bounds():
                cursor.execute("""
                SELECT id FROM rtree_merchants_idx
                WHERE min_lon >= ? AND max_lon <= ? AND min_lat >= ? AND max_lat <= ?
                """, (bbox.min_lon, bbox.max_lon, bbox.min_lat, bbox.max_lat))
                matched_ids = [r[0] for r in cursor.fetchall()]
                if not matched_ids:
                    return GeoJSONFeatureCollection(features=[], bbox=bbox.to_bbox_array()).model_dump()
                placeholders = ",".join("?" for _ in matched_ids)
                conditions.append(f"m.id IN ({placeholders})")
                params.extend(matched_ids)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
            SELECT m.id, m.entity_id, m.entity_type, m.name, m.category,
                   m.state, m.city, m.pincode, m.latitude, m.longitude,
                   m.risk_score, m.linked_case_count, m.total_suspicious_volume
            FROM geo_merchants m
            {where_clause}
            ORDER BY m.risk_score DESC
            LIMIT ?;
            """
            params.append(limit if not radius_km else limit * 5)
            cursor.execute(query, params)
            rows = cursor.fetchall()

            features = []
            for row in rows:
                m_lat = float(row["latitude"])
                m_lon = float(row["longitude"])

                if center_lat is not None and center_lon is not None and radius_km is not None:
                    dist = haversine_distance_km(center_lat, center_lon, m_lat, m_lon)
                    if dist > radius_km:
                        continue

                feature = GeoJSONFeature(
                    id=row["entity_id"],
                    geometry={"type": "Point", "coordinates": [round(m_lon, 6), round(m_lat, 6)]},
                    properties={
                        "entity_id": row["entity_id"],
                        "entity_type": row["entity_type"],
                        "name": row["name"],
                        "category": row["category"],
                        "state": row["state"],
                        "city": row["city"],
                        "pincode": row["pincode"],
                        "risk_score": float(row["risk_score"]),
                        "linked_case_count": int(row["linked_case_count"]),
                        "total_suspicious_volume": float(row["total_suspicious_volume"]),
                        "feature_type": "SUSPICIOUS_MERCHANT"
                    }
                )
                features.append(feature)
                if len(features) >= limit:
                    break

            return GeoJSONFeatureCollection(
                features=features,
                metadata={"total_merchants": len(features)}
            ).model_dump()

    # =========================================================================
    # 6. Unified Nearby Entities Query
    # =========================================================================
    def get_nearby_entities(
        self,
        lat: float,
        lon: float,
        radius_km: float = 5.0,
        entity_types: Optional[List[str]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Unified spatial query around an investigator's selected location.
        Returns cases, ATMs, predicted cash-outs, merchants, and hotspots within radius sorted by distance.
        """
        types = set(t.upper() for t in (entity_types or ["CASES", "ATMS", "PREDICTED_ATMS", "MERCHANTS", "HOTSPOTS"]))
        results = []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Approximate bounding box for R*Tree pre-filtering
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * max(0.01, math.cos(math.radians(lat))))
            min_lat, max_lat = lat - lat_delta, lat + lat_delta
            min_lon, max_lon = lon - lon_delta, lon + lon_delta

            # 1. Nearby Cases
            if "CASES" in types:
                cursor.execute("""
                SELECT c.complaint_id, c.fraud_type, c.reported_loss_amount, c.urgency_score,
                       c.victim_city, c.victim_lat, c.victim_lon
                FROM rtree_cases_idx r
                JOIN geo_cases c ON r.id = c.id
                WHERE r.min_lon >= ? AND r.max_lon <= ? AND r.min_lat >= ? AND r.max_lat <= ?
                LIMIT 500;
                """, (min_lon, max_lon, min_lat, max_lat))
                for row in cursor.fetchall():
                    c_lat, c_lon = float(row["victim_lat"]), float(row["victim_lon"])
                    dist = haversine_distance_km(lat, lon, c_lat, c_lon)
                    if dist <= radius_km:
                        results.append({
                            "type": "CASE",
                            "id": row["complaint_id"],
                            "distance_km": round(dist, 2),
                            "geometry": {"type": "Point", "coordinates": [round(c_lon, 6), round(c_lat, 6)]},
                            "properties": {
                                "complaint_id": row["complaint_id"],
                                "fraud_type": row["fraud_type"],
                                "loss_amount": float(row["reported_loss_amount"]),
                                "urgency_score": float(row["urgency_score"]),
                                "city": row["victim_city"],
                            }
                        })

            # 2. Nearby ATMs
            if "ATMS" in types:
                cursor.execute("""
                SELECT a.atm_id, a.atm_name, a.bank_name, a.city, a.latitude, a.longitude,
                       a.historical_cashouts, a.hotspot_score
                FROM rtree_atms_idx r
                JOIN geo_atms a ON r.id = a.id
                WHERE r.min_lon >= ? AND r.max_lon <= ? AND r.min_lat >= ? AND r.max_lat <= ?
                LIMIT 500;
                """, (min_lon, max_lon, min_lat, max_lat))
                for row in cursor.fetchall():
                    a_lat, a_lon = float(row["latitude"]), float(row["longitude"])
                    dist = haversine_distance_km(lat, lon, a_lat, a_lon)
                    if dist <= radius_km:
                        results.append({
                            "type": "ATM",
                            "id": row["atm_id"],
                            "distance_km": round(dist, 2),
                            "geometry": {"type": "Point", "coordinates": [round(a_lon, 6), round(a_lat, 6)]},
                            "properties": {
                                "atm_id": row["atm_id"],
                                "atm_name": row["atm_name"],
                                "bank_name": row["bank_name"],
                                "city": row["city"],
                                "historical_cashouts": int(row["historical_cashouts"]),
                                "hotspot_score": float(row["hotspot_score"]),
                            }
                        })

            # 3. Nearby Predicted ATMs
            if "PREDICTED_ATMS" in types:
                cursor.execute("""
                SELECT p.complaint_id, p.atm_id, p.rank_order, p.prediction_score,
                       p.confidence_level, p.atm_lat, p.atm_lon, a.atm_name, a.bank_name
                FROM rtree_predicted_atms_idx r
                JOIN geo_predicted_atms p ON r.id = p.id
                JOIN geo_atms a ON p.atm_id = a.atm_id
                WHERE r.min_lon >= ? AND r.max_lon <= ? AND r.min_lat >= ? AND r.max_lat <= ?
                LIMIT 500;
                """, (min_lon, max_lon, min_lat, max_lat))
                for row in cursor.fetchall():
                    p_lat, p_lon = float(row["atm_lat"]), float(row["atm_lon"])
                    dist = haversine_distance_km(lat, lon, p_lat, p_lon)
                    if dist <= radius_km:
                        results.append({
                            "type": "PREDICTED_ATM",
                            "id": f"{row['complaint_id']}_{row['atm_id']}",
                            "distance_km": round(dist, 2),
                            "geometry": {"type": "Point", "coordinates": [round(p_lon, 6), round(p_lat, 6)]},
                            "properties": {
                                "complaint_id": row["complaint_id"],
                                "atm_id": row["atm_id"],
                                "atm_name": row["atm_name"],
                                "bank_name": row["bank_name"],
                                "rank": int(row["rank_order"]),
                                "score": float(row["prediction_score"]),
                                "confidence": row["confidence_level"],
                            }
                        })

            # 4. Nearby Merchants
            if "MERCHANTS" in types:
                cursor.execute("""
                SELECT m.entity_id, m.name, m.category, m.risk_score, m.latitude, m.longitude
                FROM rtree_merchants_idx r
                JOIN geo_merchants m ON r.id = m.id
                WHERE r.min_lon >= ? AND r.max_lon <= ? AND r.min_lat >= ? AND r.max_lat <= ?
                LIMIT 500;
                """, (min_lon, max_lon, min_lat, max_lat))
                for row in cursor.fetchall():
                    m_lat, m_lon = float(row["latitude"]), float(row["longitude"])
                    dist = haversine_distance_km(lat, lon, m_lat, m_lon)
                    if dist <= radius_km:
                        results.append({
                            "type": "MERCHANT",
                            "id": row["entity_id"],
                            "distance_km": round(dist, 2),
                            "geometry": {"type": "Point", "coordinates": [round(m_lon, 6), round(m_lat, 6)]},
                            "properties": {
                                "entity_id": row["entity_id"],
                                "name": row["name"],
                                "category": row["category"],
                                "risk_score": float(row["risk_score"]),
                            }
                        })

            # 5. Nearby Hotspots
            if "HOTSPOTS" in types:
                cursor.execute("""
                SELECT h.hotspot_id, h.name, h.risk_level, h.risk_score, h.case_count,
                       h.radius_km, h.center_lat, h.center_lon
                FROM rtree_risk_hotspots_idx r
                JOIN geo_risk_hotspots h ON r.id = h.id
                WHERE r.min_lon >= ? AND r.max_lon <= ? AND r.min_lat >= ? AND r.max_lat <= ?
                LIMIT 500;
                """, (min_lon, max_lon, min_lat, max_lat))
                for row in cursor.fetchall():
                    h_lat, h_lon = float(row["center_lat"]), float(row["center_lon"])
                    dist = haversine_distance_km(lat, lon, h_lat, h_lon)
                    if dist <= (radius_km + float(row["radius_km"])):
                        results.append({
                            "type": "HOTSPOT",
                            "id": row["hotspot_id"],
                            "distance_km": round(dist, 2),
                            "geometry": {"type": "Point", "coordinates": [round(h_lon, 6), round(h_lat, 6)]},
                            "properties": {
                                "hotspot_id": row["hotspot_id"],
                                "name": row["name"],
                                "risk_level": row["risk_level"],
                                "risk_score": float(row["risk_score"]),
                                "case_count": int(row["case_count"]),
                            }
                        })

        # Sort all findings by distance ascending
        results.sort(key=lambda item: item["distance_km"])
        trimmed = results[:limit]

        # Convert to GeoJSON FeatureCollection
        features = [
            GeoJSONFeature(
                id=item["id"],
                geometry=item["geometry"],
                properties={**item["properties"], "entity_type": item["type"], "distance_km": item["distance_km"]}
            )
            for item in trimmed
        ]

        return GeoJSONFeatureCollection(
            features=features,
            metadata={
                "center": [round(lon, 6), round(lat, 6)],
                "radius_km": radius_km,
                "total_found": len(results),
                "returned_count": len(features)
            }
        ).model_dump()

    # =========================================================================
    # 7. Unified Multi-Layer Viewport Query
    # =========================================================================
    def get_viewport_data(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        zoom: int = 10,
        layers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Unified multi-layer viewport query optimized for high-performance map rendering.
        Returns layered GeoJSON FeatureCollections bounded strictly within the active viewport.
        """
        bbox = BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon)
        target_layers = set(l.lower() for t in (layers or ["cases", "predicted_atms", "risk", "networks", "merchants"]) for l in t.split(","))

        result: Dict[str, Any] = {
            "viewport": {
                "bbox": [min_lon, min_lat, max_lon, max_lat],
                "zoom": zoom
            },
            "layers": {}
        }

        if "cases" in target_layers:
            result["layers"]["cases"] = self.get_cases_geojson(
                bbox=bbox, limit=1000, zoom=zoom, cluster=(zoom <= 11)
            )

        if "predicted_atms" in target_layers or "predicted-atms" in target_layers:
            result["layers"]["predicted_atms"] = self.get_predicted_atms_geojson(
                bbox=bbox, limit=500
            )

        if "risk" in target_layers:
            result["layers"]["risk"] = self.get_risk_heatmap_geojson(
                bbox=bbox
            )

        if "networks" in target_layers:
            result["layers"]["networks"] = self.get_networks_geojson(
                bbox=bbox, limit=150
            )

        if "merchants" in target_layers:
            result["layers"]["merchants"] = self.get_merchants_geojson(
                bbox=bbox, limit=200
            )

        return result

    # =========================================================================
    # 8. Layer Definitions & Metadata
    # =========================================================================
    @staticmethod
    def get_map_layer_definitions() -> List[Dict[str, Any]]:
        """Return full layer definitions, legends, schema attributes, and zoom visibility thresholds."""
        layers = [
            MapLayerDefinition(
                id="cases",
                name="Cybercrime Incidents",
                description="Reported cybercrime victim incident locations with loss amounts and urgency classification.",
                geometry_type="Point",
                min_zoom=3,
                max_zoom=22,
                default_visible=True,
                style=MapLayerStyle(
                    color="#FF4D4F",
                    fill_color="#FF7875",
                    fill_opacity=0.85,
                    radius=6.0,
                    icon="alert-circle"
                ),
                filter_properties=["fraud_type", "urgency_score", "reported_loss_amount", "victim_bank"],
                source_endpoint="/api/v1/map/cases"
            ),
            MapLayerDefinition(
                id="predicted_atms",
                name="Predicted Cash-out ATMs",
                description="AI-predicted ATM withdrawal targets ranked by CIRIS ML with confidence scores and interception time windows.",
                geometry_type="Point",
                min_zoom=4,
                max_zoom=22,
                default_visible=True,
                style=MapLayerStyle(
                    color="#722ED1",
                    fill_color="#B37FEB",
                    fill_opacity=0.9,
                    radius=8.0,
                    icon="atm-pin"
                ),
                filter_properties=["rank", "prediction_score", "confidence_level", "bank_name", "time_window_label"],
                source_endpoint="/api/v1/map/predicted-atms"
            ),
            MapLayerDefinition(
                id="risk",
                name="Risk Heatmap & Clusters",
                description="Geographic risk clusters and density zones calculated across cybercrime hubs.",
                geometry_type="Heatmap",
                min_zoom=1,
                max_zoom=18,
                default_visible=True,
                style=MapLayerStyle(
                    color="#FA8C16",
                    fill_color="#FFA940",
                    fill_opacity=0.35,
                    stroke_width=2.0
                ),
                filter_properties=["risk_level", "risk_score", "case_count", "total_loss"],
                source_endpoint="/api/v1/map/risk"
            ),
            MapLayerDefinition(
                id="networks",
                name="Money Flow Networks",
                description="Geographic trajectories of fund fragmentation across mule accounts leading to cash-out endpoints.",
                geometry_type="LineString",
                min_zoom=5,
                max_zoom=22,
                default_visible=False,
                style=MapLayerStyle(
                    color="#13C2C2",
                    stroke_width=3.0,
                    fill_opacity=0.7
                ),
                filter_properties=["complaint_id", "hop_level", "amount", "channel"],
                source_endpoint="/api/v1/map/networks"
            ),
            MapLayerDefinition(
                id="merchants",
                name="Suspicious Merchants & POS",
                description="High-risk merchant entities, crypto P2P desks, and unauthorized remittance points.",
                geometry_type="Point",
                min_zoom=6,
                max_zoom=22,
                default_visible=False,
                style=MapLayerStyle(
                    color="#EB2F96",
                    fill_color="#F759AB",
                    fill_opacity=0.85,
                    radius=5.0,
                    icon="store"
                ),
                filter_properties=["category", "risk_score", "total_suspicious_volume"],
                source_endpoint="/api/v1/map/merchants"
            )
        ]
        return [layer.model_dump() for layer in layers]

    # =========================================================================
    # 9. GIS Summary Statistics
    # =========================================================================
    def get_gis_stats(self) -> Dict[str, Any]:
        """Compute summary statistics and geographic bounding envelope."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*), SUM(reported_loss_amount), AVG(urgency_score) FROM geo_cases;")
            case_cnt, total_loss, avg_urg = cursor.fetchone()

            cursor.execute("SELECT COUNT(*) FROM geo_atms;")
            atm_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM geo_predicted_atms;")
            pred_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM geo_network_flows;")
            flow_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM geo_merchants;")
            merch_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM geo_risk_hotspots;")
            hotspot_cnt = cursor.fetchone()[0]

            cursor.execute("SELECT MIN(victim_lon), MIN(victim_lat), MAX(victim_lon), MAX(victim_lat) FROM geo_cases;")
            bbox_res = cursor.fetchone()
            bbox = [bbox_res[0], bbox_res[1], bbox_res[2], bbox_res[3]] if bbox_res and bbox_res[0] is not None else None

            return {
                "total_cases_mapped": case_cnt or 0,
                "total_loss_mapped": round(float(total_loss or 0.0), 2),
                "avg_urgency_score": round(float(avg_urg or 0.0), 3),
                "total_atms_indexed": atm_cnt or 0,
                "total_predictions_indexed": pred_cnt or 0,
                "total_network_flows_indexed": flow_cnt or 0,
                "total_merchants_indexed": merch_cnt or 0,
                "total_risk_hotspots": hotspot_cnt or 0,
                "geographic_envelope_bbox": bbox,
                "spatial_index_type": "SQLite R*Tree (WGS84)"
            }

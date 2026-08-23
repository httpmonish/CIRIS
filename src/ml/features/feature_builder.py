"""
Point-in-Time Feature Engineering Pipeline for CIPHER-X v4.

Transforms (ComplaintPayload, CandidateATM) pairs into standardized 36-dimensional
feature matrices for the Multi-Model Ranker, ensuring zero lookahead bias.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.ml.contracts.schemas import ComplaintPayload, CandidateATM
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache


class FeatureBuilder:
    """
    Constructs leak-free feature vectors for (complaint, ATM) candidate pairs.
    """

    LOCATION_TYPE_MAP = {
        "Bank Branch ATM": 0,
        "Hospital ATM": 1,
        "Petrol Station ATM": 2,
        "Market ATM": 3,
        "Standalone Kiosk": 4,
        "Bus Terminal ATM": 5,
        "Railway Station ATM": 6,
        "Residential Complex ATM": 7,
        "Mall ATM": 8,
        "University ATM": 9,
        "Airport ATM": 10,
    }

    ACCOUNT_TYPE_MAP = {
        "mule": 0,
        "suspicious_hub": 1,
        "intermediary": 2,
        "unknown": 0,
    }

    FEATURE_COLUMNS = [
        "haversine_distance_km",
        "same_city",
        "same_district",
        "same_pincode",
        "nearby_atm_count",
        "geographic_similarity",
        "location_type",
        "in_geo_candidates",
        "in_hotspot_candidates",
        "in_network_candidates",
        "in_behavioural_candidates",
        "historical_complaints_as_of_T",
        "historical_cashout_count_as_of_T",
        "historical_cashout_rate_as_of_T",
        "historical_avg_loss_as_of_T",
        "historical_hotspot_score_as_of_T",
        "hour",
        "minute_bucket",
        "day_of_week",
        "is_weekend",
        "holiday_flag",
        "time_since_complaint_h",
        "time_since_last_transaction_h",
        "recent_activity_count",
        "velocity_15m",
        "velocity_30m",
        "velocity_1h",
        "velocity_3h",
        "velocity_6h",
        "velocity_24h",
        "account_degree_as_of_T",
        "cluster_size",
        "fraud_cluster_membership",
        "linked_complaint_count_as_of_T",
        "account_type",
        "is_synthetic_mule",
    ]

    def __init__(
        self,
        atm_master_df: pd.DataFrame,
        hotspot_cache: HistoricalHotspotCache,
        graph_engine: Optional[TemporalGraphEngine] = None,
        spatial_index: Optional[SpatialIndex] = None,
    ):
        self.atm_master_df = atm_master_df.copy().reset_index(drop=True)
        self.hotspot_cache = hotspot_cache
        self.graph_engine = graph_engine
        self.spatial_index = spatial_index or SpatialIndex(self.atm_master_df)

        # Precompute ATM densities (count within 5km)
        self._precompute_atm_densities()

        # Metadata dictionary
        self.atm_lookup: Dict[str, Dict[str, Any]] = {}
        for _, row in self.atm_master_df.iterrows():
            atm_id = str(row["atm_id"]).strip()
            self.atm_lookup[atm_id] = row.to_dict()

    def _precompute_atm_densities(self) -> None:
        """Precompute nearby ATM density within 5km for all ATMs in master."""
        self.atm_densities: Dict[str, int] = {}
        for _, row in self.atm_master_df.iterrows():
            atm_id = str(row["atm_id"]).strip()
            lat, lon = float(row["latitude"]), float(row["longitude"])
            nearby = self.spatial_index.query_radius(lat, lon, radius_km=5.0)
            # Exclude self
            self.atm_densities[atm_id] = max(0, len(nearby) - 1)

    def build_features_for_candidates(
        self,
        complaint: ComplaintPayload,
        candidates: List[CandidateATM],
        as_of_T: Optional[datetime] = None,
        chain_accounts: Optional[List[str]] = None,
        suspect_account_type: str = "mule",
        is_synthetic_mule: int = 1,
    ) -> pd.DataFrame:
        """
        Build feature DataFrame for all candidate ATMs for a given complaint as of time T.
        """
        t_pred = as_of_T or complaint.complaint_timestamp
        v_loc = complaint.victim_location

        # -------------------------------------------------------------
        # Temporal & Velocity Context
        # -------------------------------------------------------------
        hour = t_pred.hour
        minute_bucket = t_pred.minute // 15
        day_of_week = t_pred.weekday()
        is_weekend = int(day_of_week in [5, 6])
        holiday_flag = 0  # Can be augmented with calendar holidays

        # Time elapsed since incident
        if complaint.incident_timestamp:
            time_since_incident_h = max(0.0, (t_pred - complaint.incident_timestamp).total_seconds() / 3600.0)
        else:
            time_since_incident_h = 0.0

        time_since_last_tx_h = max(0.0, time_since_incident_h * 0.8)

        # Activity velocities (simulated from complaint volume / urgency)
        urgency = float(complaint.urgency_score)
        v_15m = int(urgency > 0.8)
        v_30m = int(urgency > 0.6)
        v_1h = int(complaint.num_transactions)
        v_3h = int(complaint.num_transactions * 2)
        v_6h = int(complaint.num_transactions * 3)
        v_24h = int(complaint.num_transactions * 4)
        recent_activity_count = v_1h + v_3h

        # -------------------------------------------------------------
        # Graph & Mule Account Context
        # -------------------------------------------------------------
        graph_feats = {
            "account_degree_as_of_T": 0.0,
            "cluster_size": 1.0,
            "fraud_cluster_membership": 1.0,
            "linked_complaint_count_as_of_T": 0.0,
        }

        if self.graph_engine is not None:
            # Query suspect account from chain
            accs = chain_accounts or self.graph_engine.case_to_chain.get(complaint.complaint_id, [])
            if not accs and complaint.complaint_id in self.graph_engine.case_to_cashout_acc:
                cash_acc = self.graph_engine.case_to_cashout_acc[complaint.complaint_id]
                if cash_acc:
                    accs = [cash_acc]

            if accs:
                primary_acc = accs[0]
                acc_feats = self.graph_engine.get_account_graph_features_as_of_T(primary_acc, as_of_T=t_pred)
                graph_feats["account_degree_as_of_T"] = acc_feats.get("account_degree_as_of_T", 0.0)
                graph_feats["cluster_size"] = acc_feats.get("cluster_size", 1.0)
                graph_feats["linked_complaint_count_as_of_T"] = acc_feats.get("linked_complaint_count_as_of_T", 0.0)
                graph_feats["fraud_cluster_membership"] = 1.0 if complaint.complaint_id in self.graph_engine.case_to_cluster else 0.0

        # -------------------------------------------------------------
        # Construct Rows per Candidate ATM
        # -------------------------------------------------------------
        rows = []
        for cand in candidates:
            atm_id = cand.atm_id
            meta = self.atm_lookup.get(atm_id, {})

            # Spatial & Geographic features
            dist_km = cand.distance_km
            geo_sim = 1.0 / (1.0 + dist_km)
            same_city = int(str(v_loc.city).strip().lower() == str(meta.get("city", "")).strip().lower())
            same_district = int(str(v_loc.district).strip().lower() == str(meta.get("district", "")).strip().lower())
            same_pincode = int(int(v_loc.pincode) == int(meta.get("pincode", -1))) if v_loc.pincode > 0 else 0
            nearby_density = self.atm_densities.get(atm_id, 0)

            # Retrieval indicator flags
            in_geo = int("geo" in cand.retrieval_sources)
            in_hotspot = int("hotspot" in cand.retrieval_sources)
            in_network = int("network" in cand.retrieval_sources)
            in_behavioural = int("behavioural" in cand.retrieval_sources)

            # Historical Hotspot Stats strictly as of T
            h_stats = self.hotspot_cache.get_atm_stats_as_of_T(atm_id, as_of_T=t_pred)

            loc_type_str = str(meta.get("location_type", cand.location_type))
            loc_type_code = self.LOCATION_TYPE_MAP.get(loc_type_str, 0)
            acc_type_code = self.ACCOUNT_TYPE_MAP.get(suspect_account_type.lower(), 0)

            row = {
                "complaint_id": complaint.complaint_id,
                "atm_id": atm_id,
                "haversine_distance_km": float(dist_km),
                "same_city": int(same_city),
                "same_district": int(same_district),
                "same_pincode": int(same_pincode),
                "nearby_atm_count": int(nearby_density),
                "geographic_similarity": float(geo_sim),
                "location_type": loc_type_code,
                "in_geo_candidates": int(in_geo),
                "in_hotspot_candidates": int(in_hotspot),
                "in_network_candidates": int(in_network),
                "in_behavioural_candidates": int(in_behavioural),
                "historical_complaints_as_of_T": int(h_stats["historical_complaints_as_of_T"]),
                "historical_cashout_count_as_of_T": int(h_stats["historical_cashout_count_as_of_T"]),
                "historical_cashout_rate_as_of_T": float(h_stats["historical_cashout_rate_as_of_T"]),
                "historical_avg_loss_as_of_T": float(h_stats["historical_avg_loss_as_of_T"]),
                "historical_hotspot_score_as_of_T": float(h_stats["historical_hotspot_score_as_of_T"]),
                "hour": int(hour),
                "minute_bucket": int(minute_bucket),
                "day_of_week": int(day_of_week),
                "is_weekend": int(is_weekend),
                "holiday_flag": int(holiday_flag),
                "time_since_complaint_h": float(time_since_incident_h),
                "time_since_last_transaction_h": float(time_since_last_tx_h),
                "recent_activity_count": int(recent_activity_count),
                "velocity_15m": int(v_15m),
                "velocity_30m": int(v_30m),
                "velocity_1h": int(v_1h),
                "velocity_3h": int(v_3h),
                "velocity_6h": int(v_6h),
                "velocity_24h": int(v_24h),
                "account_degree_as_of_T": int(graph_feats["account_degree_as_of_T"]),
                "cluster_size": int(graph_feats["cluster_size"]),
                "fraud_cluster_membership": int(graph_feats["fraud_cluster_membership"]),
                "linked_complaint_count_as_of_T": int(graph_feats["linked_complaint_count_as_of_T"]),
                "account_type": acc_type_code,
                "is_synthetic_mule": int(is_synthetic_mule),
            }
            rows.append(row)

        df = pd.DataFrame(rows)
        return df

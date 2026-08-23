"""
Multi-Strategy Hybrid Candidate ATM Retrieval Engine.

Implements Stage 0 of CIPHER-X v4:
Prunes the global ATM search space to a high-recall candidate subset per complaint.

Strategies:
1. Geospatial Proximity: Radius search (R <= 50km) with KNN fallback.
2. Historical Hotspots: Top-N historically active cashout ATMs as-of T.
3. Mule Network Association: ATMs previously used by the suspect's transaction chain as-of T.
4. Behavioral / Temporal: ATMs matching operational temporal windows and high-risk location types.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Set, Optional

from src.ml.contracts.schemas import ComplaintPayload, CandidateATM
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache


class CandidateRetriever:
    """
    Orchestrates multi-channel candidate generation and union aggregation.
    Guarantees strict point-in-time isolation (no lookahead bias).
    """

    def __init__(
        self,
        spatial_index: SpatialIndex,
        hotspot_cache: HistoricalHotspotCache,
        graph_engine: Optional[TemporalGraphEngine] = None,
        geo_radius_km: float = 100.0,
        geo_fallback_knn: int = 100,
        top_hotspots_count: int = 100,
    ):
        self.spatial_index = spatial_index
        self.hotspot_cache = hotspot_cache
        self.graph_engine = graph_engine
        self.geo_radius_km = geo_radius_km
        self.geo_fallback_knn = geo_fallback_knn
        self.top_hotspots_count = top_hotspots_count

        # Quick lookup dictionary for ATM metadata
        self.atm_metadata: Dict[str, Dict[str, Any]] = {}
        for _, row in self.spatial_index.atm_df.iterrows():
            atm_id = str(row["atm_id"]).strip()
            self.atm_metadata[atm_id] = row.to_dict()

    def retrieve_candidates(
        self,
        complaint: ComplaintPayload,
        as_of_T: Optional[datetime] = None,
        chain_accounts: Optional[List[str]] = None,
    ) -> List[CandidateATM]:
        """
        Retrieve union candidate ATM set for an incoming complaint.

        Args:
            complaint: Validated ComplaintPayload object.
            as_of_T: Prediction timestamp (defaults to complaint.complaint_timestamp).
            chain_accounts: Optional list of suspect account IDs in the mule chain.

        Returns:
            List of CandidateATM objects with retrieval source flags and distance.
        """
        t_pred = as_of_T or complaint.complaint_timestamp
        v_lat = complaint.victim_location.latitude
        v_lon = complaint.victim_location.longitude

        candidate_sources: Dict[str, Set[str]] = {}

        # -------------------------------------------------------------
        # 1. Geospatial Candidate Retrieval
        # -------------------------------------------------------------
        geo_results = self.spatial_index.query_radius(v_lat, v_lon, radius_km=self.geo_radius_km)
        if len(geo_results) < self.geo_fallback_knn:
            geo_results = self.spatial_index.query_knn(v_lat, v_lon, k=self.geo_fallback_knn)

        for res in geo_results:
            atm_id = str(res["atm_id"]).strip()
            candidate_sources.setdefault(atm_id, set()).add("geo")

        # -------------------------------------------------------------
        # 2. Historical Hotspot Candidate Retrieval
        # -------------------------------------------------------------
        hotspot_results = self.hotspot_cache.get_top_hotspots_as_of_T(
            as_of_T=t_pred,
            top_k=self.top_hotspots_count
        )
        for atm_id, _ in hotspot_results:
            atm_id = str(atm_id).strip()
            if atm_id in self.atm_metadata:
                candidate_sources.setdefault(atm_id, set()).add("hotspot")

        # -------------------------------------------------------------
        # 3. Mule Network Associated Candidate Retrieval
        # -------------------------------------------------------------
        if self.graph_engine is not None:
            # Check explicit chain accounts or lookup by complaint_id
            accs = chain_accounts or self.graph_engine.case_to_chain.get(complaint.complaint_id, [])
            if not accs and complaint.complaint_id in self.graph_engine.case_to_cashout_acc:
                cash_acc = self.graph_engine.case_to_cashout_acc[complaint.complaint_id]
                if cash_acc:
                    accs = [cash_acc]

            if accs:
                net_atms = self.graph_engine.get_network_associated_atms_as_of_T(accs, as_of_T=t_pred)
                for atm_id in net_atms:
                    atm_id = str(atm_id).strip()
                    if atm_id in self.atm_metadata:
                        candidate_sources.setdefault(atm_id, set()).add("network")

        # -------------------------------------------------------------
        # 4. Behavioral / Temporal Candidate Retrieval
        # -------------------------------------------------------------
        # Match ATMs with high cashout activity during complaint's temporal window (e.g. night/weekend)
        hour = t_pred.hour
        is_night = (hour >= 22 or hour <= 5)
        
        # Behavioral heuristic: In night hours, prioritize Standalone / 24/7 ATM locations in nearby radius
        if is_night:
            knn_night = self.spatial_index.query_knn(v_lat, v_lon, k=min(40, len(self.atm_metadata)))
            for res in knn_night:
                loc_type = str(res.get("location_type", "")).lower()
                if "standalone" in loc_type or "commercial" in loc_type or "hospital" in loc_type:
                    atm_id = str(res["atm_id"]).strip()
                    candidate_sources.setdefault(atm_id, set()).add("behavioural")

        # -------------------------------------------------------------
        # 5. Union Aggregation & Distance Calculation
        # -------------------------------------------------------------
        candidates: List[CandidateATM] = []
        for atm_id, sources in candidate_sources.items():
            meta = self.atm_metadata.get(atm_id)
            if not meta:
                continue

            atm_lat = float(meta["latitude"])
            atm_lon = float(meta["longitude"])
            dist_km = SpatialIndex.haversine_distance(v_lat, v_lon, atm_lat, atm_lon)

            candidates.append(
                CandidateATM(
                    atm_id=atm_id,
                    atm_name=str(meta.get("atm_name", f"ATM {atm_id}")),
                    bank_name=str(meta.get("bank_name", "Unknown")),
                    latitude=atm_lat,
                    longitude=atm_lon,
                    distance_km=float(dist_km),
                    location_type=str(meta.get("location_type", "Standalone ATM")),
                    city=str(meta.get("city", "Unknown")),
                    district=str(meta.get("district", "Unknown")),
                    retrieval_sources=sorted(list(sources)),
                )
            )

        # Sort candidate list primarily by geographic proximity
        candidates.sort(key=lambda c: c.distance_km)
        return candidates

    def to_feature_dict_list(
        self,
        complaint: ComplaintPayload,
        candidates: List[CandidateATM],
    ) -> List[Dict[str, Any]]:
        """
        Convert candidate ATMs into structured dictionary rows for downstream feature builders.
        """
        rows = []
        for cand in candidates:
            rows.append({
                "complaint_id": complaint.complaint_id,
                "atm_id": cand.atm_id,
                "atm_name": cand.atm_name,
                "bank_name": cand.bank_name,
                "atm_lat": cand.latitude,
                "atm_lon": cand.longitude,
                "haversine_distance_km": cand.distance_km,
                "location_type": cand.location_type,
                "atm_city": cand.city,
                "atm_district": cand.district,
                "in_geo_candidates": int("geo" in cand.retrieval_sources),
                "in_hotspot_candidates": int("hotspot" in cand.retrieval_sources),
                "in_network_candidates": int("network" in cand.retrieval_sources),
                "in_behavioural_candidates": int("behavioural" in cand.retrieval_sources),
            })
        return rows

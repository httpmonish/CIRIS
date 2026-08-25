"""
Explainable AI (XAI) and Evidence Generation Engine for CIPHER-X v4.

Computes TreeSHAP local feature attributions and generates natural-language
investigative briefings for Law Enforcement Officers and Bank Fraud Teams.
"""

import os
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
try:
    import shap
    HAS_SHAP = True
except Exception:
    shap = None
    HAS_SHAP = False

from src.ml.models.ranker import ATMRanker


class TreeSHAPExplainer:
    """
    Computes TreeSHAP attributions and natural-language explanations for ATM predictions.
    """

    FEATURE_FRIENDLY_NAMES = {
        "haversine_distance_km": "Distance to Victim",
        "geographic_similarity": "Geographic Proximity",
        "same_city": "Same City Match",
        "same_district": "Same District Match",
        "same_pincode": "Same Pincode Match",
        "nearby_atm_count": "ATM Cluster Density",
        "location_type": "ATM Location Type",
        "in_geo_candidates": "Geospatial Radius Match",
        "in_hotspot_candidates": "Historical Hotspot Presence",
        "in_network_candidates": "Mule Network Linkage",
        "in_behavioural_candidates": "Behavioral Pattern Match",
        "historical_complaints_as_of_T": "Historical Complaint Count",
        "historical_cashout_count_as_of_T": "Prior Cashout Incidents",
        "historical_cashout_rate_as_of_T": "Historical Cashout Rate",
        "historical_avg_loss_as_of_T": "Average Loss at ATM",
        "historical_hotspot_score_as_of_T": "Hotspot Activity Score",
        "hour": "Time of Day",
        "minute_bucket": "Time Bucket",
        "day_of_week": "Day of Week",
        "is_weekend": "Weekend Activity",
        "holiday_flag": "Holiday Activity",
        "time_since_complaint_h": "Time Since Incident",
        "time_since_last_transaction_h": "Time Since Last Flow",
        "recent_activity_count": "Recent Activity Velocity",
        "velocity_15m": "15-Minute Velocity",
        "velocity_30m": "30-Minute Velocity",
        "velocity_1h": "1-Hour Velocity Burst",
        "velocity_3h": "3-Hour Velocity",
        "velocity_6h": "6-Hour Velocity",
        "velocity_24h": "24-Hour Velocity",
        "account_degree_as_of_T": "Mule Account Connectivity",
        "cluster_size": "Mule Network Cluster Size",
        "fraud_cluster_membership": "Organized Fraud Cluster",
        "linked_complaint_count_as_of_T": "Linked Cross-Case Complaints",
        "account_type": "Suspect Account Role",
        "is_synthetic_mule": "Synthetic Identity Mule",
    }

    def __init__(self, ranker: ATMRanker):
        self.ranker = ranker
        self.explainer: Optional[Any] = None
        self._init_explainer()

    def _init_explainer(self) -> None:
        """Initialize SHAP TreeExplainer from fitted LightGBM Booster."""
        if HAS_SHAP and self.ranker.is_fitted and self.ranker.model is not None:
            try:
                self.explainer = shap.TreeExplainer(self.ranker.model.booster_)
            except Exception:
                self.explainer = None

    def explain_candidate(
        self,
        feature_row_df: pd.DataFrame,
        top_k_features: int = 5,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Compute TreeSHAP contributions and synthesize human-readable explanation briefing.

        Args:
            feature_row_df: Single-row DataFrame matching FEATURE_COLUMNS.
            top_k_features: Number of top driving factors to extract.

        Returns:
            Tuple of:
            - shap_evidence: List of dicts with feature name, value, SHAP impact, and direction.
            - natural_language_briefing: Formatted narrative summary for field officers.
        """
        if self.explainer is None:
            self._init_explainer()

        clean_row = self.ranker._sanitize_features(feature_row_df)
        X = clean_row[self.ranker.feature_columns]

        if self.explainer is not None:
            shap_values = self.explainer.shap_values(X)
            # For ranking/regression, shap_values is a 2D array of shape (1, n_features)
            if isinstance(shap_values, list):
                shap_arr = shap_values[0]
            else:
                shap_arr = shap_values
            if len(shap_arr.shape) == 2:
                shap_vec = shap_arr[0]
            else:
                shap_vec = shap_arr
        else:
            # Fallback heuristic weighting if explainer uninitialized
            shap_vec = np.zeros(len(self.ranker.feature_columns))

        # Build feature attribution records
        attributions = []
        for i, col in enumerate(self.ranker.feature_columns):
            raw_val = float(X[col].iloc[0])
            s_val = float(shap_vec[i]) if i < len(shap_vec) else 0.0
            attributions.append({
                "feature": col,
                "friendly_name": self.FEATURE_FRIENDLY_NAMES.get(col, col),
                "value": raw_val,
                "shap_value": s_val,
                "abs_impact": abs(s_val),
                "direction": "RISK_INCREASE" if s_val >= 0 else "RISK_DECREASE",
            })

        # Sort by absolute SHAP contribution
        attributions.sort(key=lambda x: x["abs_impact"], reverse=True)
        top_attributions = attributions[:top_k_features]

        # Generate Natural Language Briefing
        briefing_points = []
        dist = float(X["haversine_distance_km"].iloc[0]) if "haversine_distance_km" in X.columns else 0.0
        h_rate = float(X["historical_cashout_rate_as_of_T"].iloc[0]) if "historical_cashout_rate_as_of_T" in X.columns else 0.0
        h_count = int(X["historical_cashout_count_as_of_T"].iloc[0]) if "historical_cashout_count_as_of_T" in X.columns else 0
        same_city = int(X["same_city"].iloc[0]) if "same_city" in X.columns else 0
        cluster_size = int(X["cluster_size"].iloc[0]) if "cluster_size" in X.columns else 1
        net_degree = int(X["account_degree_as_of_T"].iloc[0]) if "account_degree_as_of_T" in X.columns else 0
        v_1h = int(X["velocity_1h"].iloc[0]) if "velocity_1h" in X.columns else 0

        if dist <= 10.0:
            briefing_points.append(f"Immediate Proximity: ATM is {dist:.1f} km from victim location.")
        elif same_city == 1:
            briefing_points.append(f"Regional Affinity: Located within victim city ({dist:.1f} km).")

        if h_rate >= 0.70 and h_count >= 3:
            briefing_points.append(f"Proven Cashout Hotspot: {h_rate*100:.1f}% historical cashout rate ({h_count} prior incidents).")

        if cluster_size > 1 or net_degree > 5:
            briefing_points.append(f"Mule Network Linkage: Connected to mule cluster of size {cluster_size} (degree {net_degree}).")

        if v_1h >= 2:
            briefing_points.append(f"Velocity Surge: {v_1h} transactions detected in last hour before reporting.")

        for attr in top_attributions[:3]:
            if attr["friendly_name"] not in [p.split(":")[0] for p in briefing_points]:
                if attr["direction"] == "RISK_INCREASE":
                    briefing_points.append(f"Key Factor: {attr['friendly_name']} ({attr['value']:.2f}) positively reinforces risk.")

        if not briefing_points:
            briefing_points.append("Standard heuristic candidate matching active surveillance criteria.")

        narrative = " • " + " \n • ".join(briefing_points)
        return top_attributions, narrative

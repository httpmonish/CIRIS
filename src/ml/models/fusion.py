"""
Probability Calibration and Multi-Signal Risk Fusion Engine for CIPHER-X v4.

Transforms raw LambdaMART ranking margins into calibrated probabilities and fuses
spatial ranking, time urgency, anomaly detection, and graph intelligence into a
unified operational risk score with confidence tiers and actionable intervention guidance.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss

from src.ml.contracts.schemas import SubScores, ATMRiskPrediction


class ProbabilityCalibrator:
    """
    Calibrates unbounded ranking margins to true posterior probabilities using Platt Scaling or Isotonic Regression.
    """

    def __init__(self, method: str = "platt"):
        self.method = method
        self.platt_model: Optional[LogisticRegression] = None
        self.isotonic_model: Optional[IsotonicRegression] = None
        self.is_fitted = False

    def fit(self, val_raw_scores: np.ndarray, val_true_labels: np.ndarray) -> Dict[str, float]:
        """
        Fit calibration model on validation set raw scores.
        """
        y_true = val_true_labels.astype(int)
        X_scores = val_raw_scores.reshape(-1, 1)

        if self.method == "platt":
            self.platt_model = LogisticRegression(C=1.0, solver="lbfgs")
            self.platt_model.fit(X_scores, y_true)
            cal_probs = self.platt_model.predict_proba(X_scores)[:, 1]
        else:
            self.isotonic_model = IsotonicRegression(out_of_bounds="clip")
            self.isotonic_model.fit(val_raw_scores, y_true)
            cal_probs = self.isotonic_model.predict(val_raw_scores)

        self.is_fitted = True

        brier = float(brier_score_loss(y_true, cal_probs))
        return {"brier_score": brier}

    def calibrate(self, raw_scores: np.ndarray) -> np.ndarray:
        """Calibrate array of raw ranking scores to [0.0, 1.0] probabilities."""
        if not self.is_fitted:
            # Fallback to sigmoid
            return 1.0 / (1.0 + np.exp(-raw_scores))

        if self.method == "platt" and self.platt_model is not None:
            X = raw_scores.reshape(-1, 1)
            return self.platt_model.predict_proba(X)[:, 1]
        elif self.isotonic_model is not None:
            return np.clip(self.isotonic_model.predict(raw_scores), 0.0, 1.0)
        else:
            return 1.0 / (1.0 + np.exp(-raw_scores))


class MultiSignalRiskFusionEngine:
    """
    Synthesizes ranking, time urgency, anomaly signals, and graph intelligence.
    """

    TIME_WINDOW_WEIGHTS = {
        "<1h": 1.00,
        "1-3h": 0.85,
        "3-6h": 0.65,
        "6-12h": 0.45,
        ">12h": 0.25,
    }

    def __init__(
        self,
        alpha_rank: float = 0.50,
        beta_time: float = 0.20,
        gamma_anomaly: float = 0.15,
        delta_history: float = 0.15,
        calibrator: Optional[ProbabilityCalibrator] = None,
    ):
        self.alpha_rank = alpha_rank
        self.beta_time = beta_time
        self.gamma_anomaly = gamma_anomaly
        self.delta_history = delta_history
        self.calibrator = calibrator or ProbabilityCalibrator()

    def fuse_predictions(
        self,
        ranked_candidates_df: pd.DataFrame,
        predicted_delay_hours: float,
        predicted_time_window_short: str,
        predicted_time_window_full: str,
        anomaly_score: float,
        anomaly_sub_scores: Dict[str, float],
    ) -> List[ATMRiskPrediction]:
        """
        Combine multi-stage outputs into a list of standardized ATMRiskPrediction objects.
        """
        raw_scores = ranked_candidates_df["ranking_score"].values
        calibrated_probs = self.calibrator.calibrate(raw_scores)

        # Softmax normalization within complaint candidate pool for relative likelihood
        exp_probs = np.exp(calibrated_probs - np.max(calibrated_probs))
        softmax_probs = exp_probs / np.sum(exp_probs)

        time_weight = self.TIME_WINDOW_WEIGHTS.get(predicted_time_window_short, 0.50)

        predictions: List[ATMRiskPrediction] = []

        for rank_idx, (_, row) in enumerate(ranked_candidates_df.iterrows()):
            atm_id = str(row["atm_id"])
            atm_name = str(row.get("atm_name", f"ATM {atm_id}"))
            bank_name = str(row.get("bank_name", "Unknown"))
            city = str(row.get("atm_city", row.get("city", "Unknown")))
            district = str(row.get("atm_district", row.get("district", "Unknown")))
            lat = float(row.get("atm_lat", row.get("latitude", 0.0)))
            lon = float(row.get("atm_lon", row.get("longitude", 0.0)))
            dist_km = float(row.get("haversine_distance_km", 0.0))

            p_cal = float(calibrated_probs[rank_idx])
            p_soft = float(softmax_probs[rank_idx])

            # Location sub-score: Inverse distance + same city bonus
            loc_sim = float(row.get("geographic_similarity", 1.0 / (1.0 + dist_km)))
            same_city = float(row.get("same_city", 0))
            location_score = float(np.clip(0.7 * loc_sim + 0.3 * same_city, 0.0, 1.0))

            # Historical sub-score: Bayesian cashout rate + hotspot score
            h_rate = float(row.get("historical_cashout_rate_as_of_T", 0.10))
            h_score_raw = float(row.get("historical_hotspot_score_as_of_T", 0.0))
            h_norm = float(np.clip(h_score_raw / 5.0, 0.0, 1.0))
            historical_score = float(np.clip(0.6 * h_rate + 0.4 * h_norm, 0.0, 1.0))

            # Time sub-score
            time_score = float(time_weight)

            # Anomaly sub-score
            anom_score = float(anomaly_score)

            # Multi-Signal Fused Risk Score
            # Combines calibrated ranking probability with time urgency, anomaly, and historical hotspot
            fused_score = (
                self.alpha_rank * p_cal
                + self.beta_time * time_score
                + self.gamma_anomaly * anom_score
                + self.delta_history * historical_score
            )
            fused_score = float(np.clip(fused_score, 0.0, 1.0))

            # Confidence Tier Determination
            if rank_idx == 0 and (fused_score >= 0.65 or p_cal >= 0.50 or p_soft >= 0.25):
                confidence_tier = "HIGH"
            elif rank_idx < 3 and (fused_score >= 0.45 or p_soft >= 0.10):
                confidence_tier = "MEDIUM"
            elif fused_score >= 0.35:
                confidence_tier = "MEDIUM"
            else:
                confidence_tier = "LOW"

            # Action Recommendation Determination
            if confidence_tier == "HIGH" and time_weight >= 0.85:
                action_required = "CRITICAL_INTERCEPT_DISPATCH"
            elif confidence_tier == "HIGH":
                action_required = "URGENT_FREEZE_AND_PATROL"
            elif confidence_tier == "MEDIUM" and time_weight >= 0.65:
                action_required = "BANK_ALERT_AND_GEO_MONITOR"
            elif confidence_tier == "MEDIUM":
                action_required = "STANDBY_MONITORING"
            else:
                action_required = "LOG_FOR_NETWORK_ANALYSIS"

            sub_scores = SubScores(
                location_score=round(location_score, 4),
                time_score=round(time_score, 4),
                anomaly_score=round(anom_score, 4),
                historical_score=round(historical_score, 4),
            )

            prediction = ATMRiskPrediction(
                rank=rank_idx + 1,
                atm_id=atm_id,
                atm_name=atm_name,
                bank_name=bank_name,
                city=city,
                district=district,
                latitude=lat,
                longitude=lon,
                distance_km=round(dist_km, 2),
                sub_scores=sub_scores,
                fused_risk_score=round(fused_score, 4),
                calibrated_probability=round(p_cal, 4),
                predicted_time_window=predicted_time_window_full,
                predicted_delay_hours=round(predicted_delay_hours, 2),
                confidence_tier=confidence_tier,
                action_required=action_required,
                shap_evidence=[],
                graph_evidence={},
            )
            predictions.append(prediction)

        return predictions

    def save(self, file_path: str) -> None:
        """Save calibrator and fusion configuration."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        bundle = {
            "calibrator": self.calibrator,
            "weights": {
                "alpha_rank": self.alpha_rank,
                "beta_time": self.beta_time,
                "gamma_anomaly": self.gamma_anomaly,
                "delta_history": self.delta_history,
            },
        }
        joblib.dump(bundle, file_path)

    def load(self, file_path: str) -> None:
        """Load calibrator and fusion configuration."""
        bundle = joblib.load(file_path)
        self.calibrator = bundle["calibrator"]
        w = bundle["weights"]
        self.alpha_rank = w["alpha_rank"]
        self.beta_time = w["beta_time"]
        self.gamma_anomaly = w["gamma_anomaly"]
        self.delta_history = w["delta_history"]

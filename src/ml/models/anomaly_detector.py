"""
Unsupervised Anomaly Detection Engine for CIPHER-X v4.

Detects out-of-pattern transaction velocity bursts, unusual cashout timing,
and high-volume amount anomalies using an Isolation Forest ensemble.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
from sklearn.ensemble import IsolationForest

from src.ml.contracts.schemas import ComplaintPayload


class AnomalyDetector:
    """
    IsolationForest Anomaly Detector for Cybercrime Velocity & Amount Patterns.
    """

    FEATURE_COLUMNS = [
        "amount_deviation_z",
        "transaction_count_deviation",
        "velocity_1h",
        "velocity_24h",
        "unusual_time_of_day",
        "new_beneficiary_anomaly",
        "sudden_degree_change",
        "is_otp_shared",
        "clicked_malicious_link",
        "urgency_score",
    ]

    # Baseline statistics from reference population
    BASELINE_AMOUNT_MEAN = 32500.0
    BASELINE_AMOUNT_STD = 103000.0

    def __init__(
        self,
        contamination: float = 0.10,
        n_estimators: int = 120,
        random_state: int = 42,
    ):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.is_fitted = False

        # Threshold parameters for calibration
        self.score_min = -0.5
        self.score_max = 0.5

    def extract_features_from_payload(self, complaint: ComplaintPayload) -> pd.DataFrame:
        """Extract anomaly feature vector from a ComplaintPayload."""
        t_pred = complaint.complaint_timestamp
        hour = t_pred.hour
        is_unusual_time = int(hour in [23, 0, 1, 2, 3, 4, 5])

        loss_amt = float(complaint.reported_loss_amount)
        amt_z = (loss_amt - self.BASELINE_AMOUNT_MEAN) / max(1.0, self.BASELINE_AMOUNT_STD)

        num_tx = int(complaint.num_transactions)
        tx_deviation = num_tx - 2  # Mean transactions ~ 2-3

        urgency = float(complaint.urgency_score)
        v_1h = int(num_tx) if urgency > 0.5 else 0
        v_24h = int(num_tx * 3)

        new_beneficiary = int(loss_amt > 50000.0 or urgency > 0.8)
        sudden_degree = int(num_tx >= 3 and urgency > 0.7)

        row = {
            "amount_deviation_z": float(amt_z),
            "transaction_count_deviation": int(tx_deviation),
            "velocity_1h": int(v_1h),
            "velocity_24h": int(v_24h),
            "unusual_time_of_day": int(is_unusual_time),
            "new_beneficiary_anomaly": int(new_beneficiary),
            "sudden_degree_change": int(sudden_degree),
            "is_otp_shared": int(complaint.is_otp_shared),
            "clicked_malicious_link": int(complaint.clicked_malicious_link),
            "urgency_score": float(urgency),
        }
        return pd.DataFrame([row])

    def fit(self, train_anomaly_df: pd.DataFrame) -> Dict[str, Any]:
        """Fit Isolation Forest on historical training anomaly feature vectors."""
        X_train = train_anomaly_df[self.FEATURE_COLUMNS].copy()
        # Clean numeric
        for col in self.FEATURE_COLUMNS:
            X_train[col] = pd.to_numeric(X_train[col], errors="coerce").fillna(0.0)

        self.model.fit(X_train)
        self.is_fitted = True

        raw_scores = self.model.decision_function(X_train)
        self.score_min = float(np.percentile(raw_scores, 1))
        self.score_max = float(np.percentile(raw_scores, 99))

        return {
            "n_samples": len(X_train),
            "score_min": self.score_min,
            "score_max": self.score_max,
        }

    def predict_anomaly_score(self, complaint: ComplaintPayload) -> Tuple[float, Dict[str, float]]:
        """
        Compute calibrated [0.0, 1.0] anomaly score and sub-score breakdown.

        Returns:
            Tuple of:
            - overall_anomaly_score: float in [0.0, 1.0] (1.0 = highly anomalous)
            - sub_scores: Dict[str, float]
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("AnomalyDetector is not fitted.")

        X = self.extract_features_from_payload(complaint)
        raw_score = float(self.model.decision_function(X)[0])

        # IsolationForest decision_function: lower (negative) = more anomalous.
        # Calibrate so that 1.0 = high anomaly, 0.0 = normal.
        clipped_score = np.clip(raw_score, self.score_min, self.score_max)
        if self.score_max > self.score_min:
            norm_anomaly = 1.0 - ((clipped_score - self.score_min) / (self.score_max - self.score_min))
        else:
            norm_anomaly = 0.5
        norm_anomaly = float(np.clip(norm_anomaly, 0.0, 1.0))

        # Sub-score components
        amt_score = float(np.clip(1.0 / (1.0 + np.exp(-float(X["amount_deviation_z"].iloc[0]))), 0.0, 1.0))
        vel_score = float(np.clip(float(X["velocity_1h"].iloc[0]) / 5.0, 0.0, 1.0))
        time_score = 0.9 if int(X["unusual_time_of_day"].iloc[0]) == 1 else 0.2
        behavior_score = 0.85 if int(X["is_otp_shared"].iloc[0]) == 1 or int(X["clicked_malicious_link"].iloc[0]) == 1 else 0.3

        sub_scores = {
            "amount_anomaly_score": amt_score,
            "velocity_anomaly_score": vel_score,
            "timing_anomaly_score": time_score,
            "behavior_anomaly_score": behavior_score,
        }

        return norm_anomaly, sub_scores

    def save(self, file_path: str) -> None:
        """Save fitted AnomalyDetector bundle."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        bundle = {
            "model": self.model,
            "score_min": self.score_min,
            "score_max": self.score_max,
            "feature_columns": self.FEATURE_COLUMNS,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(bundle, file_path)

    def load(self, file_path: str) -> None:
        """Load fitted AnomalyDetector bundle."""
        bundle = joblib.load(file_path)
        self.model = bundle["model"]
        self.score_min = bundle["score_min"]
        self.score_max = bundle["score_max"]
        self.FEATURE_COLUMNS = bundle["feature_columns"]
        self.is_fitted = bundle["is_fitted"]

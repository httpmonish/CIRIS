"""
Time-to-Cashout Prediction Engine for CIPHER-X v4.

Dual-head model:
1. Continuous Regressor: Predicts expected hours until withdrawal (withdrawal_delay_hours).
2. Multi-Class Classifier: Predicts probability distribution across 5 operational time windows
   to determine Law Enforcement Agency dispatch urgency.
"""

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, accuracy_score, f1_score

from src.ml.contracts.schemas import ComplaintPayload


class TimeToCashoutPredictor:
    """
    Dual-Head Gradient Boosted Time-to-Cashout Engine.
    """

    WINDOW_NAMES = {
        0: "< 1 Hour (CRITICAL IMMEDIATE)",
        1: "1 - 3 Hours (HIGH URGENCY)",
        2: "3 - 6 Hours (MEDIUM PRIORITY)",
        3: "6 - 12 Hours (STANDARD MONITORING)",
        4: "> 12 Hours (DELAYED CASHOUT)",
    }

    WINDOW_CODE_TO_SHORT = {
        0: "<1h",
        1: "1-3h",
        2: "3-6h",
        3: "6-12h",
        4: ">12h",
    }

    FRAUD_TYPE_MAP = {
        "UPI Fraud": 0,
        "Phishing": 1,
        "Investment Scam": 2,
        "Impersonation (Digital Arrest/Officer)": 3,
        "Remote Access Scam": 4,
        "Card Fraud": 5,
        "OTP Fraud": 6,
        "Fake Customer Care": 7,
        "Marketplace Fraud (OLX/e-commerce)": 8,
        "Loan App Scam": 9,
        "Social Engineering (Romance/Job)": 10,
    }

    CHANNEL_MAP = {
        "UPI": 0,
        "NetBanking": 1,
        "Wallet": 2,
        "Credit Card": 3,
        "Debit Card": 4,
        "AEPS": 5,
    }

    FEATURE_COLUMNS = [
        "reported_loss_amount",
        "urgency_score",
        "account_age_months",
        "num_transactions",
        "is_otp_shared",
        "clicked_malicious_link",
        "fraud_type",
        "channel",
        "hour",
        "minute_bucket",
        "day_of_week",
        "is_weekend",
        "time_since_incident_h",
    ]

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        max_depth: int = 6,
        random_state: int = 42,
    ):
        self.params_reg = {
            "objective": "regression_l1",  # MAE minimization
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "random_state": random_state,
            "verbose": -1,
        }
        self.params_clf = {
            "objective": "multiclass",
            "num_class": 5,
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "random_state": random_state,
            "verbose": -1,
        }
        self.regressor: Optional[lgb.LGBMRegressor] = None
        self.classifier: Optional[lgb.LGBMClassifier] = None
        self.is_fitted = False

    def extract_features_from_complaints(
        self,
        complaints_df: pd.DataFrame,
        time_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Merge and extract feature matrix from complaints and time labels DataFrame.
        """
        df = complaints_df.copy()
        if time_df is not None:
            df = pd.merge(df, time_df, on="complaint_id", how="inner")

        # Temporal columns
        ts = pd.to_datetime(df["complaint_timestamp"], errors="coerce")
        df["hour"] = ts.dt.hour.fillna(12).astype(int)
        df["minute_bucket"] = (ts.dt.minute // 15).fillna(0).astype(int)
        df["day_of_week"] = ts.dt.dayofweek.fillna(0).astype(int)
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

        # Elapsed incident time
        if "incident_timestamp" in df.columns:
            inc_ts = pd.to_datetime(df["incident_timestamp"], errors="coerce")
            diff_h = (ts - inc_ts).dt.total_seconds() / 3600.0
            df["time_since_incident_h"] = diff_h.clip(lower=0.0).fillna(0.0)
        else:
            df["time_since_incident_h"] = 0.0

        # Encode categoricals
        df["fraud_type"] = df["fraud_type"].map(lambda x: self.FRAUD_TYPE_MAP.get(str(x), 0)).fillna(0).astype(int)
        df["channel"] = df["channel"].map(lambda x: self.CHANNEL_MAP.get(str(x), 0)).fillna(0).astype(int)

        # Numeric sanitization
        for col in self.FEATURE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        return df

    def extract_features_from_payload(self, complaint: ComplaintPayload) -> pd.DataFrame:
        """Extract a single-row feature DataFrame from a ComplaintPayload object."""
        t_pred = complaint.complaint_timestamp
        hour = t_pred.hour
        minute_bucket = t_pred.minute // 15
        day_of_week = t_pred.weekday()
        is_weekend = int(day_of_week in [5, 6])

        if complaint.incident_timestamp:
            time_since_incident_h = max(0.0, (t_pred - complaint.incident_timestamp).total_seconds() / 3600.0)
        else:
            time_since_incident_h = 0.0

        row = {
            "reported_loss_amount": float(complaint.reported_loss_amount),
            "urgency_score": float(complaint.urgency_score),
            "account_age_months": int(complaint.account_age_months),
            "num_transactions": int(complaint.num_transactions),
            "is_otp_shared": int(complaint.is_otp_shared),
            "clicked_malicious_link": int(complaint.clicked_malicious_link),
            "fraud_type": self.FRAUD_TYPE_MAP.get(complaint.fraud_type, 0),
            "channel": self.CHANNEL_MAP.get(complaint.channel, 0),
            "hour": int(hour),
            "minute_bucket": int(minute_bucket),
            "day_of_week": int(day_of_week),
            "is_weekend": int(is_weekend),
            "time_since_incident_h": float(time_since_incident_h),
        }
        return pd.DataFrame([row])

    def fit(
        self,
        train_complaints_df: pd.DataFrame,
        train_time_df: pd.DataFrame,
        val_complaints_df: Optional[pd.DataFrame] = None,
        val_time_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Fit dual-head regression and classification models."""
        df_train = self.extract_features_from_complaints(train_complaints_df, train_time_df)
        X_train = df_train[self.FEATURE_COLUMNS]
        y_reg_train = df_train["withdrawal_delay_hours"].values
        y_clf_train = df_train["time_window_label"].values.astype(int)

        # Regressor
        self.regressor = lgb.LGBMRegressor(**self.params_reg)
        self.regressor.fit(X_train, y_reg_train)

        # Classifier
        self.classifier = lgb.LGBMClassifier(**self.params_clf)
        self.classifier.fit(X_train, y_clf_train)

        self.is_fitted = True

        metrics = {}
        if val_complaints_df is not None and val_time_df is not None:
            metrics = self.evaluate(val_complaints_df, val_time_df)

        return metrics

    def predict(self, complaint: ComplaintPayload) -> Tuple[float, str, Dict[str, float]]:
        """
        Predict cashout timing for a single complaint.

        Returns:
            Tuple of:
            - predicted_delay_hours: float
            - predicted_window_name: str
            - window_probabilities: Dict[str, float]
        """
        if not self.is_fitted or self.regressor is None or self.classifier is None:
            raise RuntimeError("Time model is not fitted.")

        X = self.extract_features_from_payload(complaint)
        pred_delay = float(self.regressor.predict(X)[0])
        pred_delay = max(0.1, pred_delay)  # Non-negative delay

        pred_probs = self.classifier.predict_proba(X)[0]
        top_window_code = int(np.argmax(pred_probs))
        top_window_name = self.WINDOW_NAMES.get(top_window_code, "Unknown Window")

        prob_dict = {
            self.WINDOW_CODE_TO_SHORT[k]: float(pred_probs[k])
            for k in range(len(pred_probs))
        }

        return pred_delay, top_window_name, prob_dict

    def evaluate(self, val_complaints_df: pd.DataFrame, val_time_df: pd.DataFrame) -> Dict[str, float]:
        """Evaluate both heads on validation set."""
        df_val = self.extract_features_from_complaints(val_complaints_df, val_time_df)
        X_val = df_val[self.FEATURE_COLUMNS]
        y_reg_val = df_val["withdrawal_delay_hours"].values
        y_clf_val = df_val["time_window_label"].values.astype(int)

        pred_reg = self.regressor.predict(X_val)
        pred_clf = self.classifier.predict(X_val)

        mae = float(mean_absolute_error(y_reg_val, pred_reg))
        rmse = float(root_mean_squared_error(y_reg_val, pred_reg))
        acc = float(accuracy_score(y_clf_val, pred_clf))
        f1 = float(f1_score(y_clf_val, pred_clf, average="macro"))

        return {
            "regression_MAE_hours": mae,
            "regression_RMSE_hours": rmse,
            "classification_Accuracy": acc,
            "classification_Macro_F1": f1,
        }

    def save(self, file_path: str) -> None:
        """Save fitted dual-head models bundle."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        bundle = {
            "regressor": self.regressor,
            "classifier": self.classifier,
            "feature_columns": self.FEATURE_COLUMNS,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(bundle, file_path)

    def load(self_or_cls, file_path: str) -> "TimeToCashoutPredictor":
        """Load fitted dual-head models bundle (supports both instance and class method invocation)."""
        bundle = joblib.load(file_path)
        if isinstance(self_or_cls, type):
            predictor = self_or_cls()
        else:
            predictor = self_or_cls
        predictor.regressor = bundle["regressor"]
        predictor.classifier = bundle["classifier"]
        predictor.FEATURE_COLUMNS = bundle["feature_columns"]
        predictor.is_fitted = bundle["is_fitted"]
        return predictor

"""
Supervised Multi-Model ATM Ranker for CIPHER-X v4.

Trains and evaluates Gradient Boosted Decision Tree Rankers (LightGBM LambdaMART)
on point-in-time candidate feature matrices to rank most likely future cashout locations.
"""

import os
import joblib
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
import lightgbm as lgb
from sklearn.metrics import ndcg_score

from src.ml.features.feature_builder import FeatureBuilder


class ATMRanker:
    """
    LambdaMART ATM Ranker using LightGBM.
    Supports GroupKFold evaluation, NDCG@K, MRR, and HitRate@K metrics.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
    ):
        self.params = {
            "objective": "lambdarank",
            "metric": "ndcg",
            "eval_at": [1, 3, 5, 10],
            "learning_rate": learning_rate,
            "n_estimators": n_estimators,
            "num_leaves": num_leaves,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "verbose": -1,
        }
        self.feature_columns = FeatureBuilder.FEATURE_COLUMNS
        self.model: Optional[lgb.LGBMRanker] = None
        self.is_fitted = False

    LOCATION_TYPE_MAP = FeatureBuilder.LOCATION_TYPE_MAP
    ACCOUNT_TYPE_MAP = FeatureBuilder.ACCOUNT_TYPE_MAP

    def _sanitize_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all feature columns are numeric."""
        df_clean = df.copy()
        if "location_type" in df_clean.columns:
            df_clean["location_type"] = df_clean["location_type"].map(
                lambda x: self.LOCATION_TYPE_MAP.get(str(x), 0) if not isinstance(x, (int, np.integer)) else int(x)
            ).fillna(0).astype(int)

        if "account_type" in df_clean.columns:
            df_clean["account_type"] = df_clean["account_type"].map(
                lambda x: self.ACCOUNT_TYPE_MAP.get(str(x).lower(), 0) if not isinstance(x, (int, np.integer)) else int(x)
            ).fillna(0).astype(int)

        # Ensure all columns in feature_columns are float or int
        for col in self.feature_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce").fillna(0.0)

        return df_clean

    def fit(
        self,
        train_df: pd.DataFrame,
        val_df: Optional[pd.DataFrame] = None,
        early_stopping_rounds: int = 30,
    ) -> Dict[str, Any]:
        """
        Fit the LambdaMART ranker on train_df with optional early stopping on val_df.

        Args:
            train_df: DataFrame containing FEATURE_COLUMNS, 'complaint_id', and 'label'.
            val_df: Optional validation DataFrame.
            early_stopping_rounds: Number of rounds for early stopping.

        Returns:
            Dictionary of training history and evaluation metrics.
        """
        # Sanitize data types
        train_clean = self._sanitize_features(train_df)
        train_sorted = train_clean.sort_values("complaint_id").reset_index(drop=True)
        X_train = train_sorted[self.feature_columns]
        y_train = train_sorted["label"].values.astype(int)
        train_groups = train_sorted.groupby("complaint_id", sort=False).size().values

        self.model = lgb.LGBMRanker(**self.params)

        callbacks = []
        eval_set = None
        eval_group = None

        if val_df is not None and not val_df.empty:
            val_clean = self._sanitize_features(val_df)
            val_sorted = val_clean.sort_values("complaint_id").reset_index(drop=True)
            X_val = val_sorted[self.feature_columns]
            y_val = val_sorted["label"].values.astype(int)
            val_groups = val_sorted.groupby("complaint_id", sort=False).size().values

            eval_set = [(X_val, y_val)]
            eval_group = [val_groups]
            callbacks.append(lgb.early_stopping(stopping_rounds=early_stopping_rounds, verbose=False))

        self.model.fit(
            X_train,
            y_train,
            group=train_groups,
            eval_set=eval_set,
            eval_group=eval_group,
            callbacks=callbacks,
        )
        self.is_fitted = True

        eval_metrics = {}
        if val_df is not None and not val_df.empty:
            eval_metrics = self.evaluate(val_df)

        return eval_metrics

    def predict_scores(self, feature_df: pd.DataFrame) -> np.ndarray:
        """Predict continuous ranking scores for feature rows."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() or load() first.")

        clean_df = self._sanitize_features(feature_df)
        X = clean_df[self.feature_columns]
        return self.model.predict(X)

    def rank_candidates_for_complaint(
        self,
        feature_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Rank candidate ATMs for a single complaint.

        Returns:
            DataFrame sorted by ranking score descending with rank column (1 to K).
        """
        scores = self.predict_scores(feature_df)
        df_out = feature_df.copy()
        df_out["ranking_score"] = scores
        df_out = df_out.sort_values("ranking_score", ascending=False).reset_index(drop=True)
        df_out["rank"] = np.arange(1, len(df_out) + 1)
        return df_out

    def evaluate(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute standard ranking metrics (NDCG@1, 3, 5, 10, MRR, HitRate@1, 3, 5, 10).
        """
        df_eval = df.sort_values("complaint_id").reset_index(drop=True)
        scores = self.predict_scores(df_eval)
        df_eval["score"] = scores

        ndcg_1_list, ndcg_3_list, ndcg_5_list, ndcg_10_list = [], [], [], []
        mrr_list = []
        hit_1_list, hit_3_list, hit_5_list, hit_10_list = [], [], [], []

        for cid, group in df_eval.groupby("complaint_id", sort=False):
            y_true = group["label"].values.astype(float)
            y_pred = group["score"].values

            if sum(y_true) == 0:
                continue

            # Reshape for sklearn ndcg_score
            y_true_2d = np.expand_dims(y_true, axis=0)
            y_pred_2d = np.expand_dims(y_pred, axis=0)

            n_samples = len(y_true)
            ndcg_1_list.append(ndcg_score(y_true_2d, y_pred_2d, k=min(1, n_samples)))
            ndcg_3_list.append(ndcg_score(y_true_2d, y_pred_2d, k=min(3, n_samples)))
            ndcg_5_list.append(ndcg_score(y_true_2d, y_pred_2d, k=min(5, n_samples)))
            ndcg_10_list.append(ndcg_score(y_true_2d, y_pred_2d, k=min(10, n_samples)))

            # Sort by predicted score descending to calculate MRR and Hit Rates
            sorted_indices = np.argsort(-y_pred)
            sorted_labels = y_true[sorted_indices]

            # Find rank of first positive label (1-indexed)
            pos_ranks = np.where(sorted_labels > 0)[0]
            if len(pos_ranks) > 0:
                first_rank = pos_ranks[0] + 1
                mrr_list.append(1.0 / first_rank)
                hit_1_list.append(1.0 if first_rank <= 1 else 0.0)
                hit_3_list.append(1.0 if first_rank <= 3 else 0.0)
                hit_5_list.append(1.0 if first_rank <= 5 else 0.0)
                hit_10_list.append(1.0 if first_rank <= 10 else 0.0)
            else:
                mrr_list.append(0.0)
                hit_1_list.append(0.0)
                hit_3_list.append(0.0)
                hit_5_list.append(0.0)
                hit_10_list.append(0.0)

        metrics = {
            "NDCG@1": float(np.mean(ndcg_1_list)) if ndcg_1_list else 0.0,
            "NDCG@3": float(np.mean(ndcg_3_list)) if ndcg_3_list else 0.0,
            "NDCG@5": float(np.mean(ndcg_5_list)) if ndcg_5_list else 0.0,
            "NDCG@10": float(np.mean(ndcg_10_list)) if ndcg_10_list else 0.0,
            "MRR": float(np.mean(mrr_list)) if mrr_list else 0.0,
            "HitRate@1": float(np.mean(hit_1_list)) if hit_1_list else 0.0,
            "HitRate@3": float(np.mean(hit_3_list)) if hit_3_list else 0.0,
            "HitRate@5": float(np.mean(hit_5_list)) if hit_5_list else 0.0,
            "HitRate@10": float(np.mean(hit_10_list)) if hit_10_list else 0.0,
        }
        return metrics

    def get_feature_importances(self) -> Dict[str, float]:
        """Return feature importance dict sorted by gain/split importance."""
        if not self.is_fitted or self.model is None:
            return {}
        importances = self.model.feature_importances_
        return dict(sorted(zip(self.feature_columns, importances), key=lambda x: x[1], reverse=True))

    def save(self, file_path: str) -> None:
        """Save fitted ranker bundle."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        bundle = {
            "model": self.model,
            "feature_columns": self.feature_columns,
            "params": self.params,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(bundle, file_path)

    def load(self_or_cls, file_path: str) -> "ATMRanker":
        """Load fitted ranker bundle (supports both instance and class method invocation)."""
        bundle = joblib.load(file_path)
        if isinstance(self_or_cls, type):
            ranker = self_or_cls()
        else:
            ranker = self_or_cls
        ranker.model = bundle["model"]
        ranker.feature_columns = bundle["feature_columns"]
        ranker.params = bundle.get("params", getattr(ranker, "params", {}))
        ranker.is_fitted = bundle.get("is_fitted", True)
        return ranker

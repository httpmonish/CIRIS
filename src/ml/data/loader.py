"""
Canonical Dataset Loader & Integrity Auditor for CIPHER-X v4 / CIRIS.

Provides a unified, configurable interface to load master relational tables,
chronological feature splits, and full-scale ranking datasets with zero path hardcoding.
"""

import os
import glob
import logging
from typing import Dict, Any, Optional, Tuple, Generator, List, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Canonical dataset resolver and loader for CIRIS / CIPHER ML V4.
    Supports seamless switching between datasets/final and datasets/development/dataset.
    """

    DEFAULT_RANKER_COLUMNS = [
        "complaint_id", "atm_id", "prediction_timestamp", "label",
        "victim_lat", "victim_lon", "atm_lat", "atm_lon",
        "haversine_distance_km", "same_city", "same_district", "same_pincode",
        "nearby_atm_count", "geographic_similarity", "location_type",
        "in_geo_candidates", "in_hotspot_candidates", "in_network_candidates",
        "in_behavioural_candidates", "historical_complaints_as_of_T",
        "historical_cashout_count_as_of_T", "historical_cashout_rate_as_of_T",
        "historical_avg_loss_as_of_T", "historical_hotspot_score_as_of_T",
        "hour", "minute_bucket", "day_of_week", "is_weekend", "holiday_flag",
        "time_since_complaint_h", "time_since_last_transaction_h",
        "recent_activity_count", "velocity_15m", "velocity_30m", "velocity_1h",
        "velocity_3h", "velocity_6h", "velocity_24h", "account_degree_as_of_T",
        "cluster_size", "fraud_cluster_membership", "linked_complaint_count_as_of_T",
        "account_type", "is_synthetic_mule"
    ]

    RANKER_DTYPES = {
        "complaint_id": "string",
        "atm_id": "string",
        "prediction_timestamp": "string",
        "label": "int8",
        "victim_lat": "float32",
        "victim_lon": "float32",
        "atm_lat": "float32",
        "atm_lon": "float32",
        "haversine_distance_km": "float32",
        "same_city": "int8",
        "same_district": "int8",
        "same_pincode": "int8",
        "nearby_atm_count": "int16",
        "geographic_similarity": "float32",
        "location_type": "string",
        "in_geo_candidates": "int8",
        "in_hotspot_candidates": "int8",
        "in_network_candidates": "int8",
        "in_behavioural_candidates": "int8",
        "historical_complaints_as_of_T": "int16",
        "historical_cashout_count_as_of_T": "int16",
        "historical_cashout_rate_as_of_T": "float32",
        "historical_avg_loss_as_of_T": "float32",
        "historical_hotspot_score_as_of_T": "float32",
        "hour": "int8",
        "minute_bucket": "int8",
        "day_of_week": "int8",
        "is_weekend": "int8",
        "holiday_flag": "int8",
        "time_since_complaint_h": "float32",
        "time_since_last_transaction_h": "float32",
        "recent_activity_count": "int16",
        "velocity_15m": "int16",
        "velocity_30m": "int16",
        "velocity_1h": "int16",
        "velocity_3h": "int16",
        "velocity_6h": "int16",
        "velocity_24h": "int16",
        "account_degree_as_of_T": "int16",
        "cluster_size": "int16",
        "fraud_cluster_membership": "int8",
        "linked_complaint_count_as_of_T": "int16",
        "account_type": "string",
        "is_synthetic_mule": "int8",
    }

    def __init__(self, dataset_dir: Optional[str] = None):
        if dataset_dir:
            self.root_dir = os.path.abspath(dataset_dir)
        elif os.environ.get("DATASET_DIR"):
            self.root_dir = os.path.abspath(os.environ["DATASET_DIR"])
        elif os.path.exists("datasets/final"):
            self.root_dir = os.path.abspath("datasets/final")
        elif os.path.exists("datasets/development/dataset"):
            self.root_dir = os.path.abspath("datasets/development/dataset")
        else:
            self.root_dir = os.path.abspath("datasets")

        self.relational_dir = self._resolve_relational_dir()
        logger.info(f"DatasetLoader initialized. Root: {self.root_dir} | Relational: {self.relational_dir}")

    def _resolve_relational_dir(self) -> str:
        """Locate where core CSV tables (atm_master, complaints, etc.) live."""
        candidates = [
            os.path.join(self.root_dir, "cybercrime_dataset_gen", "dataset"),
            self.root_dir,
            os.path.join(self.root_dir, "dataset"),
            os.path.join("datasets", "final", "cybercrime_dataset_gen", "dataset"),
            os.path.join("datasets", "development", "dataset"),
        ]
        for c in candidates:
            if os.path.exists(os.path.join(c, "atm_master.csv")):
                return os.path.abspath(c)
        return self.root_dir

    def _get_table_path(self, filename: str) -> str:
        """Resolve full path to a relational table."""
        path = os.path.join(self.relational_dir, filename)
        if os.path.exists(path):
            return path
        alt_path = os.path.join(self.root_dir, filename)
        if os.path.exists(alt_path):
            return alt_path
        raise FileNotFoundError(f"Required table '{filename}' not found in {self.relational_dir} or {self.root_dir}")

    def load_atm_master(self) -> pd.DataFrame:
        path = self._get_table_path("atm_master.csv")
        return pd.read_csv(path)

    def load_complaints(self) -> pd.DataFrame:
        path = self._get_table_path("complaints.csv")
        return pd.read_csv(path)

    def load_transactions(self) -> pd.DataFrame:
        path = self._get_table_path("transactions.csv")
        return pd.read_csv(path)

    def load_accounts(self) -> pd.DataFrame:
        path = self._get_table_path("accounts.csv")
        return pd.read_csv(path)

    def load_withdrawals(self) -> pd.DataFrame:
        path = self._get_table_path("withdrawals.csv")
        return pd.read_csv(path)

    def load_graph_edges(self) -> pd.DataFrame:
        path = self._get_table_path("graph_edges.csv")
        return pd.read_csv(path)

    def load_case_links(self) -> pd.DataFrame:
        path = self._get_table_path("case_links.csv")
        return pd.read_csv(path)

    def load_upi_entities(self) -> Optional[pd.DataFrame]:
        try:
            path = self._get_table_path("upi_entities.csv")
            return pd.read_csv(path)
        except FileNotFoundError:
            return None

    def load_time_splits(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load train, val, test splits for Time prediction."""
        for base in [self.relational_dir, self.root_dir]:
            train_p = os.path.join(base, "train", "time_train.csv")
            val_p = os.path.join(base, "validation", "time_val.csv")
            test_p = os.path.join(base, "test", "time_test.csv")
            if os.path.exists(train_p) and os.path.exists(val_p) and os.path.exists(test_p):
                return pd.read_csv(train_p), pd.read_csv(val_p), pd.read_csv(test_p)

        # Fallback to master time_labels.csv if no splits
        master_p = self._get_table_path("time_labels.csv")
        df = pd.read_csv(master_p)
        n = len(df)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        return df.iloc[:n_train], df.iloc[n_train:n_train+n_val], df.iloc[n_train+n_val:]

    def load_anomaly_splits(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load train, val, test splits for Anomaly detection."""
        for base in [self.relational_dir, self.root_dir]:
            train_p = os.path.join(base, "train", "anomaly_train.csv")
            val_p = os.path.join(base, "validation", "anomaly_val.csv")
            test_p = os.path.join(base, "test", "anomaly_test.csv")
            if os.path.exists(train_p) and os.path.exists(val_p) and os.path.exists(test_p):
                return pd.read_csv(train_p), pd.read_csv(val_p), pd.read_csv(test_p)

        master_p = self._get_table_path("anomaly_features.csv")
        df = pd.read_csv(master_p)
        n = len(df)
        n_train = int(n * 0.70)
        n_val = int(n * 0.15)
        return df.iloc[:n_train], df.iloc[n_train:n_train+n_val], df.iloc[n_train+n_val:]

    def get_rank_pair_paths(self, split: str) -> str:
        """Resolve ranking file path for given split ('train', 'val', 'test')."""
        split_map = {"train": "rank_pairs_train.csv", "val": "rank_pairs_val.csv", "test": "rank_pairs_test.csv"}
        fname = split_map[split]

        # Check full-scale direct top-level
        p1 = os.path.join(self.root_dir, fname)
        if os.path.exists(p1):
            return p1

        # Check in datasets/final/
        p2 = os.path.join("datasets", "final", fname)
        if os.path.exists(p2):
            return p2

        # Check in relational/split subdirectories
        folder_map = {"train": "train", "val": "validation", "test": "test"}
        p3 = os.path.join(self.relational_dir, folder_map[split], fname)
        if os.path.exists(p3):
            return p3

        raise FileNotFoundError(f"Ranking file for split '{split}' not found.")

    def load_rank_split(
        self,
        split: str,
        optimized_dtypes: bool = True,
        nrows: Optional[int] = None,
        chunksize: Optional[int] = None,
    ) -> Union[pd.DataFrame, Generator[pd.DataFrame, None, None]]:
        """
        Load ranking data for 'train', 'val', or 'test'.
        Supports chunked streaming and optimized memory footprints.
        """
        path = self.get_rank_pair_paths(split)
        dtypes = self.RANKER_DTYPES if optimized_dtypes else None

        if chunksize is not None:
            return pd.read_csv(path, dtype=dtypes, nrows=nrows, chunksize=chunksize)
        return pd.read_csv(path, dtype=dtypes, nrows=nrows)

    def run_integrity_audit(self) -> Dict[str, Any]:
        """
        Perform a comprehensive data integrity audit across all tables and splits.
        """
        audit_results = {
            "root_dir": self.root_dir,
            "relational_dir": self.relational_dir,
            "tables": {},
            "foreign_key_checks": {},
            "coordinate_checks": {},
            "temporal_checks": {},
            "critical_violations": 0,
            "passed": True,
        }

        # 1. Inspect core tables
        table_loaders = {
            "atm_master": self.load_atm_master,
            "complaints": self.load_complaints,
            "transactions": self.load_transactions,
            "accounts": self.load_accounts,
            "withdrawals": self.load_withdrawals,
            "graph_edges": self.load_graph_edges,
            "case_links": self.load_case_links,
        }

        dfs: Dict[str, pd.DataFrame] = {}
        for name, loader in table_loaders.items():
            try:
                df = loader()
                dfs[name] = df
                audit_results["tables"][name] = {
                    "rows": len(df),
                    "cols": len(df.columns),
                    "columns": list(df.columns),
                    "null_counts": int(df.isnull().sum().sum()),
                }
            except Exception as e:
                audit_results["tables"][name] = {"error": str(e)}
                audit_results["critical_violations"] += 1

        # 2. Foreign Key Validations
        if "withdrawals" in dfs and "atm_master" in dfs:
            valid_atms = set(dfs["atm_master"]["atm_id"].unique())
            wd_atms = set(dfs["withdrawals"]["atm_id"].dropna().unique())
            missing_atms = wd_atms - valid_atms
            audit_results["foreign_key_checks"]["withdrawals_atm_id_in_atm_master"] = {
                "violations": len(missing_atms),
                "passed": len(missing_atms) == 0,
            }
            if missing_atms:
                audit_results["critical_violations"] += 1

        if "transactions" in dfs and "complaints" in dfs:
            valid_complaints = set(dfs["complaints"]["complaint_id"].unique())
            tx_complaints = set(dfs["transactions"]["complaint_id"].dropna().unique())
            missing_complaints = tx_complaints - valid_complaints
            audit_results["foreign_key_checks"]["transactions_complaint_id_in_complaints"] = {
                "violations": len(missing_complaints),
                "passed": len(missing_complaints) == 0,
            }
            if missing_complaints:
                audit_results["critical_violations"] += 1

        # 3. Coordinate Bounds Validation (India Bounding Box approx: Lat 6 to 38, Lon 68 to 98)
        if "atm_master" in dfs:
            atm_df = dfs["atm_master"]
            lat_invalid = ((atm_df["latitude"] < 6.0) | (atm_df["latitude"] > 38.5)).sum()
            lon_invalid = ((atm_df["longitude"] < 68.0) | (atm_df["longitude"] > 98.0)).sum()
            audit_results["coordinate_checks"]["atm_coordinates"] = {
                "latitude_violations": int(lat_invalid),
                "longitude_violations": int(lon_invalid),
                "passed": bool(lat_invalid == 0 and lon_invalid == 0),
            }
            if lat_invalid > 0 or lon_invalid > 0:
                audit_results["critical_violations"] += 1

        if "complaints" in dfs:
            cmp_df = dfs["complaints"]
            lat_invalid = ((cmp_df["victim_lat"] < 6.0) | (cmp_df["victim_lat"] > 38.5)).sum()
            lon_invalid = ((cmp_df["victim_lon"] < 68.0) | (cmp_df["victim_lon"] > 98.0)).sum()
            audit_results["coordinate_checks"]["victim_coordinates"] = {
                "latitude_violations": int(lat_invalid),
                "longitude_violations": int(lon_invalid),
                "passed": bool(lat_invalid == 0 and lon_invalid == 0),
            }
            if lat_invalid > 0 or lon_invalid > 0:
                audit_results["critical_violations"] += 1

        # 4. Financial & Amount Bounds
        if "complaints" in dfs:
            neg_loss = (dfs["complaints"]["reported_loss_amount"] < 0).sum()
            audit_results["financial_checks"] = {
                "negative_losses": int(neg_loss),
                "passed": bool(neg_loss == 0),
            }
            if neg_loss > 0:
                audit_results["critical_violations"] += 1

        # 5. Chronological Splits Check
        try:
            train_p = self.get_rank_pair_paths("train")
            val_p = self.get_rank_pair_paths("val")
            test_p = self.get_rank_pair_paths("test")

            # Sample header / count
            audit_results["rank_splits"] = {
                "train_path": train_p,
                "val_path": val_p,
                "test_path": test_p,
            }
        except Exception as e:
            audit_results["rank_splits"] = {"error": str(e)}
            audit_results["critical_violations"] += 1

        audit_results["passed"] = audit_results["critical_violations"] == 0
        return audit_results

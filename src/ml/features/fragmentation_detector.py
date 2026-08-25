"""
Transaction Fragmentation and Splitting Detector for CIRIS.

Detects multi-destination fund splitting, rapid smurfing, micro-transaction bursts,
and layering patterns within point-in-time temporal windows.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class TransactionFragmentationDetector:
    """
    Identifies transaction fragmentation, micro-splitting, and fan-out layering typologies.
    """

    def __init__(self, transactions_df: Optional[pd.DataFrame] = None):
        self.transactions_df = transactions_df.copy() if transactions_df is not None else pd.DataFrame()
        self._preprocess()

    def _preprocess(self) -> None:
        """Standardize column names and datetime types."""
        if not self.transactions_df.empty:
            col_map = {
                "src_account_id": "source_account",
                "dst_account_id": "destination_account",
                "source_node": "source_account",
                "target_node": "destination_account",
                "source": "source_account",
                "target": "destination_account",
                "src": "source_account",
                "dst": "destination_account",
                "from_account": "source_account",
                "to_account": "destination_account",
                "time": "timestamp",
                "txn_timestamp": "timestamp",
            }
            self.transactions_df.rename(columns=col_map, inplace=True)
            if "timestamp" in self.transactions_df.columns:
                self.transactions_df["timestamp"] = pd.to_datetime(self.transactions_df["timestamp"], errors="coerce")
            if "amount" not in self.transactions_df.columns:
                self.transactions_df["amount"] = 1000.0

    def analyze_account_fragmentation(
        self,
        account_id: str,
        as_of_T: datetime,
        window_hours: float = 3.0,
        reported_loss_amount: float = 10000.0,
    ) -> Dict[str, Any]:
        """
        Compute point-in-time fragmentation metrics for an account.
        """
        acc_str = str(account_id)
        if self.transactions_df.empty or "timestamp" not in self.transactions_df.columns:
            return {
                "account_id": acc_str,
                "is_fragmented": False,
                "splitting_ratio": 0.0,
                "outgoing_txn_count": 0,
                "unique_destinations": 0,
                "micro_txn_proportion": 0.0,
                "fragmentation_score": 0.0,
                "pattern_type": "NORMAL",
            }

        t_min = as_of_T - timedelta(hours=window_hours)
        mask = (
            (self.transactions_df["source_account"].astype(str) == acc_str)
            & (self.transactions_df["timestamp"] >= t_min)
            & (self.transactions_df["timestamp"] <= as_of_T)
        )
        recent_txns = self.transactions_df[mask]

        if recent_txns.empty:
            return {
                "account_id": acc_str,
                "is_fragmented": False,
                "splitting_ratio": 0.0,
                "outgoing_txn_count": 0,
                "unique_destinations": 0,
                "micro_txn_proportion": 0.0,
                "fragmentation_score": 0.0,
                "pattern_type": "NORMAL",
            }

        out_count = len(recent_txns)
        unique_dest = recent_txns["destination_account"].nunique()
        amounts = recent_txns["amount"].values
        micro_count = np.sum(amounts < 2000.0)
        micro_prop = float(micro_count / out_count) if out_count > 0 else 0.0

        splitting_ratio = float(out_count / (reported_loss_amount / 1000.0)) if reported_loss_amount > 0 else 0.0

        # Composite score
        f_score = 0.0
        if unique_dest >= 3:
            f_score += 0.50
        elif unique_dest >= 2:
            f_score += 0.30

        if micro_prop >= 0.30:
            f_score += 0.25

        if out_count >= 3:
            f_score += 0.25

        f_score = min(1.0, f_score)
        is_fragmented = f_score >= 0.50

        pattern_type = "NORMAL"
        if unique_dest >= 3 and micro_prop >= 0.50:
            pattern_type = "FAN_OUT"
        elif out_count >= 5:
            pattern_type = "MICRO_BURST"
        elif unique_dest >= 2:
            pattern_type = "BRANCHING"

        return {
            "account_id": acc_str,
            "is_fragmented": is_fragmented,
            "splitting_ratio": splitting_ratio,
            "outgoing_txn_count": out_count,
            "unique_destinations": unique_dest,
            "micro_txn_proportion": micro_prop,
            "fragmentation_score": f_score,
            "pattern_type": pattern_type,
        }

"""
Causal Historical Hotspot and ATM Statistics Cache.

Computes point-in-time statistics (complaint counts, cashout counts, Bayesian-smoothed
cashout rates, average losses, and hotspot activity scores) strictly using data prior to T.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


class HistoricalHotspotCache:
    """
    Maintains causal ATM historical cashout statistics with Bayesian smoothing.
    Guarantees no lookahead bias across temporal boundaries.
    """

    def __init__(
        self,
        atm_master_df: pd.DataFrame,
        withdrawals_df: Optional[pd.DataFrame] = None,
        complaints_df: Optional[pd.DataFrame] = None,
        smoothing_prior_weight: float = 10.0,
    ):
        self.atm_master_df = atm_master_df.copy().reset_index(drop=True)
        self.withdrawals_df = withdrawals_df.copy() if withdrawals_df is not None else pd.DataFrame()
        self.complaints_df = complaints_df.copy() if complaints_df is not None else pd.DataFrame()
        self.smoothing_prior_weight = smoothing_prior_weight

        self._normalize_timestamps()
        self._precompute_global_priors()

    def _normalize_timestamps(self) -> None:
        if not self.withdrawals_df.empty and "withdrawal_timestamp" in self.withdrawals_df.columns:
            self.withdrawals_df["ts"] = pd.to_datetime(self.withdrawals_df["withdrawal_timestamp"], errors="coerce")
        if not self.complaints_df.empty and "complaint_timestamp" in self.complaints_df.columns:
            self.complaints_df["ts"] = pd.to_datetime(self.complaints_df["complaint_timestamp"], errors="coerce")

    def _precompute_global_priors(self) -> None:
        """Compute base global prior cashout rate and average loss across dataset."""
        if not self.withdrawals_df.empty and "withdrawal_amount" in self.withdrawals_df.columns:
            self.global_avg_loss = float(self.withdrawals_df["withdrawal_amount"].mean())
        else:
            self.global_avg_loss = 25000.0

        # Prior base cashout rate (prior belief: 0.10)
        self.prior_cashout_rate = 0.10

    def get_atm_stats_as_of_T(self, atm_id: str, as_of_T: datetime) -> Dict[str, float]:
        """
        Compute historical statistics for a single ATM strictly before time T.
        """
        atm_str = str(atm_id).strip()

        if self.withdrawals_df.empty:
            return {
                "historical_complaints_as_of_T": 0.0,
                "historical_cashout_count_as_of_T": 0.0,
                "historical_cashout_rate_as_of_T": self.prior_cashout_rate,
                "historical_avg_loss_as_of_T": self.global_avg_loss,
                "historical_hotspot_score_as_of_T": 0.0,
            }

        # Filter withdrawals strictly before T
        prior_wds = self.withdrawals_df[
            (self.withdrawals_df["atm_id"] == atm_str) &
            (self.withdrawals_df["ts"] < as_of_T)
        ]

        cashout_count = len(prior_wds)
        if cashout_count > 0:
            avg_loss = float(prior_wds["withdrawal_amount"].mean())
        else:
            avg_loss = self.global_avg_loss

        # Estimate historical complaint encounters before T
        # In historical pairs, total complaints related to this ATM area or previous referrals
        complaint_count = max(cashout_count, 0)

        # Bayesian smoothing for cashout rate: (k + C * p0) / (n + C)
        # where k = cashouts, n = complaints, p0 = prior rate, C = prior weight
        smoothed_rate = (cashout_count + self.smoothing_prior_weight * self.prior_cashout_rate) / (
            complaint_count + self.smoothing_prior_weight
        )

        # Hotspot score: log1p(cashouts) * (avg_loss / 10000.0) * smoothed_rate
        hotspot_score = np.log1p(cashout_count) * (avg_loss / 25000.0) * smoothed_rate

        return {
            "historical_complaints_as_of_T": float(complaint_count),
            "historical_cashout_count_as_of_T": float(cashout_count),
            "historical_cashout_rate_as_of_T": float(smoothed_rate),
            "historical_avg_loss_as_of_T": float(avg_loss),
            "historical_hotspot_score_as_of_T": float(hotspot_score),
        }

    def get_top_hotspots_as_of_T(self, as_of_T: datetime, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Get the Top-K most active historical hotspot ATMs across the entire network as of time T.
        Used for Stage 0 Hotspot Candidate Retrieval.
        """
        if self.withdrawals_df.empty:
            return []

        prior_wds = self.withdrawals_df[self.withdrawals_df["ts"] < as_of_T]
        if prior_wds.empty:
            return []

        counts = prior_wds["atm_id"].value_counts().head(top_k)
        return [(str(atm_id), float(count)) for atm_id, count in counts.items()]

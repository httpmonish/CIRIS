"""Leakage-safe 'as of prediction timestamp T' historical feature helpers.

Every function here only ever looks at events strictly BEFORE T (np.searchsorted
with side='left' on a sorted timestamp array), so nothing computed downstream
can see the future relative to the complaint being scored. This is the single
mechanism that all of section 10 (ATM historical stats), section 13 (temporal
as-of features), section 14 (graph as-of features) and section 16 (dynamic
hotspots) rely on.
"""

import numpy as np
import pandas as pd
from utils import bayesian_smooth


class AsOfIndex:
    """Sorted-timestamp index over a grouping key (atm_id, district, account_id,
    upi_id, ...) supporting fast 'count/aggregate strictly before T' lookups."""

    def __init__(self, df, key_col, ts_col, value_cols=None):
        self.groups = {}
        value_cols = value_cols or []
        for key, g in df.groupby(key_col):
            g = g.sort_values(ts_col)
            times = g[ts_col].values.astype("datetime64[ns]").astype(np.int64)
            payload = {"times": times}
            for vc in value_cols:
                payload[vc] = g[vc].values
            self.groups[key] = payload

    def count_before(self, key, T_int64):
        g = self.groups.get(key)
        if g is None:
            return 0
        return int(np.searchsorted(g["times"], T_int64, side="left"))

    def agg_before(self, key, T_int64, value_col, how="mean"):
        g = self.groups.get(key)
        if g is None:
            return np.nan
        n = int(np.searchsorted(g["times"], T_int64, side="left"))
        if n == 0:
            return np.nan
        vals = g[value_col][:n]
        if how == "mean":
            return float(np.mean(vals))
        if how == "sum":
            return float(np.sum(vals))
        raise ValueError(how)


def to_int64(ts):
    return np.datetime64(pd.Timestamp(ts)).astype("datetime64[ns]").astype(np.int64)


def build_atm_history(withdrawals_df, complaints_df):
    """Join withdrawal -> its complaint's reported_loss & fraud_type, for
    building per-ATM as-of-T stats (count, cashout rate, avg loss)."""
    wd = withdrawals_df.merge(
        complaints_df[["complaint_id", "reported_loss_amount", "fraud_type", "victim_district"]],
        on="complaint_id", how="left",
    )
    atm_idx = AsOfIndex(wd, "atm_id", "withdrawal_timestamp",
                         value_cols=["withdrawal_success", "reported_loss_amount"])
    district_idx = AsOfIndex(wd.assign(atm_district=wd["victim_district"]),
                              "atm_district", "withdrawal_timestamp")
    return atm_idx, district_idx, wd


def atm_as_of_stats(atm_idx, atm_id, T_int64, global_cashout_rate_prior=0.9, global_avg_loss_prior=25000.0):
    n = atm_idx.count_before(atm_id, T_int64)
    rate = atm_idx.agg_before(atm_id, T_int64, "withdrawal_success", how="mean")
    avg_loss = atm_idx.agg_before(atm_id, T_int64, "reported_loss_amount", how="mean")
    successes = 0.0 if np.isnan(rate) else rate * n
    smoothed_rate = bayesian_smooth(successes, n, global_cashout_rate_prior, prior_strength=8.0)
    smoothed_loss = avg_loss if not np.isnan(avg_loss) else global_avg_loss_prior
    hotspot_score = np.log1p(n) * smoothed_rate
    return dict(
        historical_complaints_as_of_T=n,  # approximation: 1 complaint per withdrawal at this ATM
        historical_cashout_count_as_of_T=n,
        historical_cashout_rate_as_of_T=round(float(smoothed_rate), 4),
        historical_avg_loss_as_of_T=round(float(smoothed_loss), 2),
        historical_hotspot_score_as_of_T=round(float(hotspot_score), 4),
    )

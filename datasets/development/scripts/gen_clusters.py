"""Build reusable 'fraud cluster' infrastructure: groups of mule/intermediary/
hub accounts plus a set of ATMs they habitually cash out at. Clusters are
shared across many complaints (Pattern C — recurring fraud infrastructure),
and each cluster has its own geographic/behavioural signature so that
withdrawal location is NOT simply "nearest ATM to victim" (Patterns A/B/D/E).
"""

import numpy as np
import pandas as pd
from config import CITIES, N_ACCOUNTS
from utils import haversine_km


def build_clusters(rng, accounts_df, atms_df, n_clusters=None):
    mule_pool = accounts_df[accounts_df["account_type"].isin(
        ["mule", "intermediary", "suspicious_hub"]
    )].reset_index(drop=True)

    if n_clusters is None:
        # Roughly one cluster per 12-20 mule/intermediary accounts
        n_clusters = max(20, len(mule_pool) // 15)

    cluster_records = []
    # Shuffle mule pool and distribute into clusters of size 2-6
    idx = rng.permutation(len(mule_pool))
    ptr = 0
    for c in range(n_clusters):
        if ptr >= len(idx):
            break
        size = rng.integers(2, 7)
        members_idx = idx[ptr: ptr + size]
        ptr += size
        if len(members_idx) == 0:
            continue
        members = mule_pool.iloc[members_idx]["account_id"].tolist()

        # Pick a "home" city for the cluster's cashout ATMs — often different
        # from any single victim's city (district-shift / long-distance realism)
        home_city = CITIES[rng.integers(0, len(CITIES))]
        home_lat, home_lon = home_city[3], home_city[4]
        dists = haversine_km(atms_df["latitude"].values, atms_df["longitude"].values, home_lat, home_lon)
        near_mask = dists < rng.choice([15, 25, 40])
        candidate_atms = atms_df[near_mask]
        if len(candidate_atms) < 3:
            candidate_atms = atms_df.sample(min(8, len(atms_df)), random_state=int(rng.integers(0, 1e6)))
        pref_atms = candidate_atms.sample(
            min(len(candidate_atms), rng.integers(3, 9)),
            random_state=int(rng.integers(0, 1e6)),
        )["atm_id"].tolist()

        # Behavioural signature: typical withdrawal delay (Pattern D)
        delay_profile = rng.choice(["fast", "medium", "slow"], p=[0.35, 0.45, 0.20])
        pattern_weights = _pattern_weights(rng)

        cluster_records.append({
            "cluster_id": f"CLUSTER_{c+1:04d}",
            "member_accounts": members,
            "home_city": home_city[0],
            "preferred_atms": pref_atms,
            "delay_profile": delay_profile,
            "pattern_weights": pattern_weights,  # dict A/B/C/D/E -> weight
        })

    return cluster_records


def _pattern_weights(rng):
    base = rng.dirichlet(np.array([3, 2, 4, 2, 1]))  # A, B, C(reuse handled structurally), D, E
    w = np.array([base[0], base[1], base[3], base[4]])
    w = w / w.sum()
    return {"A": float(w[0]), "B": float(w[1]), "D": float(w[2]), "E": float(w[3])}


def assign_clusters_to_complaints(rng, complaints_df, clusters):
    """Assign each complaint to a cluster with skew so some clusters recur far
    more than others (realistic fraud-ring reuse)."""
    n = len(complaints_df)
    n_clusters = len(clusters)
    # Zipf-like skew: a few clusters handle many cases, most handle few
    raw_weights = rng.power(a=0.35, size=n_clusters) + 0.01
    probs = raw_weights / raw_weights.sum()
    chosen_idx = rng.choice(n_clusters, size=n, p=probs)
    return chosen_idx

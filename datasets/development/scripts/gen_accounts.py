"""Generate accounts.csv and upi_entities.csv.

Account roles are assigned so that a minority form reusable "fraud
infrastructure" (mule / intermediary / hub accounts) that recur across many
cases — this is what the graph-intelligence features are meant to pick up on.
Most accounts still look ordinary; suspicious accounts are NOT trivially
flagged (mule_role / is_synthetic_mule exist as ground truth for evaluation,
but everyday features like prior_complaint_count are noisy, not a giveaway).
"""

import numpy as np
import pandas as pd
from config import CITIES, BANKS, ACCOUNT_TYPES, MULE_ROLES, N_ACCOUNTS, SIM_START, SIM_END
from utils import weighted_choice, id_series, random_timestamps


ROLE_WEIGHTS = {
    "victim": 38, "ordinary_recipient": 34, "mule": 14,
    "intermediary": 8, "high_volume": 4, "suspicious_hub": 2,
}


def generate_accounts(rng):
    city_w = [c[5] for c in CITIES]
    chosen_cities = weighted_choice(rng, CITIES, city_w, N_ACCOUNTS)

    types = weighted_choice(rng, list(ROLE_WEIGHTS.keys()), list(ROLE_WEIGHTS.values()), N_ACCOUNTS)
    mule_role = []
    is_mule = []
    for t in types:
        if t == "mule":
            mule_role.append(rng.choice(["first_hop_mule", "cashout_mule"], p=[0.55, 0.45]))
            is_mule.append(1)
        elif t == "intermediary":
            mule_role.append("intermediary_mule")
            is_mule.append(1)
        elif t == "suspicious_hub":
            mule_role.append("hub_account")
            is_mule.append(1)
        else:
            mule_role.append("none")
            is_mule.append(0)

    first_seen = random_timestamps(rng, SIM_START, SIM_END, N_ACCOUNTS)
    # last_activity is after first_seen, bounded by SIM_END
    max_extra_days = (pd.Timestamp(SIM_END) - first_seen).total_seconds() / 86400.0
    extra_days = rng.uniform(0, np.maximum(max_extra_days.values, 0))
    last_activity = first_seen + pd.to_timedelta(extra_days, unit="D")

    prior_complaints = np.where(
        np.isin(types, ["mule", "intermediary", "suspicious_hub"]),
        rng.poisson(2.2, size=N_ACCOUNTS),
        rng.poisson(0.15, size=N_ACCOUNTS),
    )
    prior_withdrawals = np.where(
        np.isin(types, ["mule", "suspicious_hub"]),
        rng.poisson(3.0, size=N_ACCOUNTS),
        rng.poisson(0.4, size=N_ACCOUNTS),
    )
    linked_accounts = np.where(
        types == np.array("suspicious_hub"),
        rng.poisson(9, size=N_ACCOUNTS),
        rng.poisson(1.5, size=N_ACCOUNTS),
    )
    linked_upi = np.maximum(1, (linked_accounts * rng.uniform(0.5, 1.3, size=N_ACCOUNTS)).astype(int))

    risk_history = rng.choice(
        ["none", "prior_flagged", "prior_confirmed_fraud"], size=N_ACCOUNTS, p=[0.86, 0.10, 0.04]
    )

    df = pd.DataFrame({
        "account_id": id_series("ACC", N_ACCOUNTS),
        "account_type": types,
        "bank_name": rng.choice(BANKS, size=N_ACCOUNTS),
        "account_age_months": rng.integers(1, 260, size=N_ACCOUNTS),
        "city": [c[0] for c in chosen_cities],
        "state": [c[1] for c in chosen_cities],
        "risk_history": risk_history,
        "prior_complaint_count": prior_complaints,
        "prior_withdrawal_count": prior_withdrawals,
        "linked_account_count": linked_accounts,
        "linked_upi_count": linked_upi,
        "is_synthetic_mule": is_mule,
        "mule_role": mule_role,
        "first_seen_timestamp": first_seen,
        "last_activity_timestamp": last_activity,
    })
    return df


def generate_upi_entities(rng, accounts_df, n_per_account_max=2):
    """Each account has 1-2 UPI IDs; mule/hub accounts reuse UPI IDs across
    more cases (populated later once case_links are known), so here we just
    create the UPI universe and initialize counters to 0 (filled in later)."""
    rows = []
    upi_counter = 1
    for acc_id, acc_type, first_seen, last_seen in zip(
        accounts_df["account_id"], accounts_df["account_type"],
        accounts_df["first_seen_timestamp"], accounts_df["last_activity_timestamp"],
    ):
        n_upi = 2 if acc_type in ("mule", "suspicious_hub", "intermediary") and rng.random() < 0.4 else 1
        for _ in range(n_upi):
            rows.append({
                "upi_id": f"UPI_{upi_counter:06d}",
                "account_id": acc_id,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "linked_case_count": 0,     # filled in gen_graph.py from case_links
                "linked_account_count": 0,  # filled in gen_graph.py
            })
            upi_counter += 1
    return pd.DataFrame(rows)

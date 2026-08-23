"""For every complaint: build the victim->mule->...->cashout transaction chain,
the resulting withdrawal event(s), the case_links row, and raw graph edges.

Implements the required behavioural patterns:
  A - nearby withdrawal (cluster ATM close to victim)
  B - district shift (victim area -> mule area -> withdrawal elsewhere)
  C - recurring fraud infrastructure (handled by cluster reuse upstream)
  D - time behaviour (cluster delay_profile: fast/medium/slow)
  E - long-distance withdrawal
Also injects fragmentation, consolidation, repeated beneficiaries and bursts.
"""

import numpy as np
import pandas as pd
from utils import haversine_km, id_series

CHANNELS_FLOW = ["UPI", "IMPS", "NEFT", "Net Banking"]


def _delay_hours(rng, profile):
    if profile == "fast":
        return rng.gamma(1.5, 1.2)      # ~0-6h, cashout soon after fraud
    if profile == "slow":
        return rng.gamma(3.0, 6.0)      # spread over ~1-3 days (clipped later)
    return rng.gamma(2.0, 3.0)          # medium


def generate_flow_for_complaints(rng, complaints_df, accounts_df, atms_df, clusters, cluster_assign):
    acc_lookup = accounts_df.set_index("account_id")
    victim_accounts = accounts_df[accounts_df["account_type"] == "victim"]["account_id"].to_numpy(dtype=object)
    rng.shuffle(victim_accounts)

    transactions = []
    withdrawals = []
    case_links = []
    graph_edges = []
    tx_counter = 1
    wd_counter = 1

    n = len(complaints_df)
    victim_acc_choice = rng.choice(victim_accounts, size=n)

    for i, row in enumerate(complaints_df.itertuples(index=False)):
        cluster = clusters[cluster_assign[i]]
        members = cluster["member_accounts"]
        victim_acc = victim_acc_choice[i]

        # Chain length 3-6 hops through cluster members (no immediate repeats,
        # so no from==to self-loop transactions). Longer than a minimal 2-hop
        # chain both for realism (multi-hop layering) and to land the total
        # transaction count in the spec's 250k-500k range across 50k cases.
        hop_count = min(rng.integers(3, 9), max(1, len(members)))
        chain = []
        last = victim_acc
        pool = list(members)
        for _ in range(hop_count):
            choices = [m for m in pool if m != last] or pool
            nxt = choices[int(rng.integers(0, len(choices)))]
            chain.append(nxt)
            last = nxt
        full_chain = [victim_acc] + chain

        t = pd.Timestamp(row.incident_timestamp) + pd.Timedelta(minutes=int(rng.integers(2, 45)))
        amount_remaining = float(row.reported_loss_amount)
        prev_ts = None
        seq = 1

        for hop_i in range(len(full_chain) - 1):
            frm, to = full_chain[hop_i], full_chain[hop_i + 1]
            # Fragmentation can occur at any hop (not just the first) --
            # mules routinely re-split funds at each layer to evade limits.
            frag_this_hop = rng.random() < 0.45
            n_splits = int(rng.integers(2, 5)) if frag_this_hop else 1
            hop_amount_total = amount_remaining * rng.uniform(0.55, 0.95) if hop_i < len(full_chain) - 2 else amount_remaining
            splits = np.diff(np.concatenate([[0], np.sort(rng.uniform(0, 1, n_splits - 1)), [1]])) if n_splits > 1 else np.array([1.0])
            for s in splits:
                amt = round(max(50.0, hop_amount_total * s), 2)
                burst_gap_min = rng.exponential(4) if n_splits > 1 else rng.exponential(25)
                t = t + pd.Timedelta(minutes=float(burst_gap_min) + 1)
                tsp = None if prev_ts is None else (t - prev_ts).total_seconds() / 60.0
                transactions.append({
                    "transaction_id": f"TXN_{tx_counter:07d}",
                    "complaint_id": row.complaint_id,
                    "timestamp": t,
                    "from_account_id": frm,
                    "to_account_id": to,
                    "amount": amt,
                    "channel": rng.choice(CHANNELS_FLOW, p=[0.55, 0.22, 0.13, 0.10]),
                    "transaction_type": "fragmentation" if n_splits > 1 else (
                        "victim_debit" if hop_i == 0 else "mule_transfer"),
                    "bank": acc_lookup.loc[to, "bank_name"] if to in acc_lookup.index else "Unknown",
                    "upi_id": "",  # linked later in gen_graph via upi_entities mapping
                    "device_type": rng.choice(["Android", "iOS", "Desktop"], p=[0.6, 0.3, 0.1]),
                    "geo_lat": row.victim_lat if hop_i == 0 else np.nan,
                    "geo_lon": row.victim_lon if hop_i == 0 else np.nan,
                    "time_since_previous_transaction": tsp,
                    "transaction_sequence_number": seq,
                })
                graph_edges.append({
                    "src_account_id": frm, "dst_account_id": to,
                    "complaint_id": row.complaint_id, "timestamp": t, "amount": amt,
                })
                tx_counter += 1
                seq += 1
                prev_ts = t
            amount_remaining = hop_amount_total

        cashout_acc = full_chain[-1]

        # ---- choose withdrawal ATM according to cluster pattern weights ----
        pattern = rng.choice(list(cluster["pattern_weights"].keys()),
                              p=np.array(list(cluster["pattern_weights"].values())))
        atm_row = _pick_atm(rng, pattern, row, atms_df, cluster)

        delay_h = _delay_hours(rng, cluster["delay_profile"])
        delay_h = float(np.clip(delay_h, 0.1, 30.0))
        withdrawal_ts = prev_ts + pd.Timedelta(hours=delay_h)
        time_since_fraud = (withdrawal_ts - pd.Timestamp(row.incident_timestamp)).total_seconds() / 3600.0
        time_since_last_transfer = (withdrawal_ts - prev_ts).total_seconds() / 3600.0

        wd_amount = round(amount_remaining * rng.uniform(0.4, 1.0), 2)
        withdrawals.append({
            "withdrawal_id": f"WD_{wd_counter:06d}",
            "complaint_id": row.complaint_id,
            "account_id": cashout_acc,
            "atm_id": atm_row["atm_id"],
            "withdrawal_timestamp": withdrawal_ts,
            "withdrawal_amount": wd_amount,
            "latitude": atm_row["latitude"],
            "longitude": atm_row["longitude"],
            "time_since_fraud": round(time_since_fraud, 3),
            "time_since_last_transfer": round(time_since_last_transfer, 3),
            "withdrawal_sequence": 1,
            "withdrawal_success": int(rng.random() < 0.93),
        })
        wd_counter += 1

        case_links.append({
            "complaint_id": row.complaint_id,
            "cluster_id": cluster["cluster_id"],
            "chain_accounts": "|".join(full_chain),
            "cashout_account_id": cashout_acc,
            "pattern_used": pattern,
        })

    return (
        pd.DataFrame(transactions),
        pd.DataFrame(withdrawals),
        pd.DataFrame(case_links),
        pd.DataFrame(graph_edges),
    )


def _pick_atm(rng, pattern, complaint_row, atms_df, cluster):
    vlat, vlon = complaint_row.victim_lat, complaint_row.victim_lon

    if pattern == "A":  # nearby withdrawal
        dists = haversine_km(atms_df["latitude"].values, atms_df["longitude"].values, vlat, vlon)
        near = atms_df[dists < 10]
        pool = near if len(near) else atms_df
        return pool.sample(1, random_state=int(rng.integers(0, 1e6))).iloc[0]

    if pattern == "E":  # long distance
        dists = haversine_km(atms_df["latitude"].values, atms_df["longitude"].values, vlat, vlon)
        far = atms_df[dists > 200]
        pool = far if len(far) else atms_df
        return pool.sample(1, random_state=int(rng.integers(0, 1e6))).iloc[0]

    if pattern == "D" and cluster["preferred_atms"]:
        # time-behaviour pattern still needs a location -> use cluster's own turf
        atm_id = rng.choice(cluster["preferred_atms"])
        match = atms_df[atms_df["atm_id"] == atm_id]
        if len(match):
            return match.iloc[0]

    # default / "B" district shift / cluster reuse -> cluster's preferred ATMs
    if cluster["preferred_atms"]:
        atm_id = rng.choice(cluster["preferred_atms"])
        match = atms_df[atms_df["atm_id"] == atm_id]
        if len(match):
            return match.iloc[0]

    return atms_df.sample(1, random_state=int(rng.integers(0, 1e6))).iloc[0]

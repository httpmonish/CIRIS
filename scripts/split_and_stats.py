"""Chronological train/validation/test split + dataset-level statistics."""

import numpy as np
import pandas as pd


def chronological_split(rank_pairs, time_labels, anomaly_features, complaints):
    """Split by each complaint's prediction_timestamp so TRAIN is strictly
    older than VALIDATION which is strictly older than TEST — no shuffling."""
    order = complaints[["complaint_id", "complaint_timestamp"]].drop_duplicates()
    order = order[order["complaint_id"].isin(rank_pairs["complaint_id"].unique())]
    order = order.sort_values("complaint_timestamp").reset_index(drop=True)

    n = len(order)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    train_ids = set(order["complaint_id"].iloc[:n_train])
    val_ids = set(order["complaint_id"].iloc[n_train:n_train + n_val])
    test_ids = set(order["complaint_id"].iloc[n_train + n_val:])

    def split_df(df):
        return (
            df[df["complaint_id"].isin(train_ids)].reset_index(drop=True),
            df[df["complaint_id"].isin(val_ids)].reset_index(drop=True),
            df[df["complaint_id"].isin(test_ids)].reset_index(drop=True),
        )

    rp_splits = split_df(rank_pairs)
    tl_splits = split_df(time_labels)
    af_splits = split_df(anomaly_features)
    return rp_splits, tl_splits, af_splits, (train_ids, val_ids, test_ids)


def compute_recall_at_k(rank_pairs, withdrawals, ks):
    """Recall@K measured on the model-facing candidate set: for each complaint,
    rank candidates by a simple unsupervised proxy (geographic_similarity +
    historical_hotspot_score_as_of_T) and check whether the true ATM falls in
    the top K. This mirrors what Recall@K would mean at inference before any
    supervised ranker is trained."""
    true_atm = withdrawals.set_index("complaint_id")["atm_id"]
    rp = rank_pairs.copy()
    rp["proxy_score"] = rp["geographic_similarity"].fillna(0) + rp["historical_hotspot_score_as_of_T"].fillna(0)
    results = {}
    for k in ks:
        hits = 0
        total = 0
        for cid, g in rp.groupby("complaint_id"):
            if cid not in true_atm.index:
                continue
            total += 1
            top_k = g.sort_values("proxy_score", ascending=False).head(k)
            if true_atm.loc[cid] in set(top_k["atm_id"]):
                hits += 1
        results[f"recall_at_{k}"] = round(hits / max(1, total), 4)
    return results


def build_statistics(complaints, accounts, atms, transactions, withdrawals, rank_pairs,
                      time_labels, recall_stats, cand_stats):
    stats = {
        "total_complaints": int(len(complaints)),
        "total_transactions": int(len(transactions)),
        "total_accounts": int(len(accounts)),
        "total_atms": int(len(atms)),
        "total_withdrawals": int(len(withdrawals)),
        "total_fraud_types": int(complaints["fraud_type"].nunique()),
        "avg_transactions_per_complaint": round(float(transactions.groupby("complaint_id").size().mean()), 3),
        "avg_candidates_per_complaint": round(float(rank_pairs.groupby("complaint_id").size().mean()), 3) if len(rank_pairs) else 0,
        "ranking_positive_negative_ratio": _pos_neg_ratio(rank_pairs),
        "geographic_distribution_by_city": complaints["victim_city"].value_counts().to_dict(),
        "fraud_type_distribution": complaints["fraud_type"].value_counts().to_dict(),
        "time_window_distribution": time_labels["time_window_label"].value_counts().sort_index().to_dict() if len(time_labels) else {},
        "candidate_retrieval": cand_stats,
        "recall_at_k": recall_stats,
    }
    return stats


def _pos_neg_ratio(rank_pairs):
    if not len(rank_pairs):
        return None
    pos = int((rank_pairs["label"] == 1).sum())
    neg = int((rank_pairs["label"] == 0).sum())
    return {"positive": pos, "negative": neg, "ratio_neg_per_pos": round(neg / max(1, pos), 2)}

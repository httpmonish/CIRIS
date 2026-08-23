"""Chronological train/validation/test split + dataset-level statistics."""

import numpy as np
import pandas as pd


def _pos_neg_ratio_from_stats(rank_stats):
    total = rank_stats.get("total_rank_pair_rows", 0)
    pos = rank_stats.get("total_actionable_complaints", 0)  # 1 positive per actionable complaint by construction
    neg = max(0, total - pos)
    return {"positive": pos, "negative": neg, "ratio_neg_per_pos": round(neg / max(1, pos), 2)}


def build_statistics(complaints, accounts, atms, transactions, withdrawals,
                      time_labels, rank_stats):
    stats = {
        "total_complaints": int(len(complaints)),
        "total_transactions": int(len(transactions)),
        "total_accounts": int(len(accounts)),
        "total_atms": int(len(atms)),
        "total_withdrawals": int(len(withdrawals)),
        "total_fraud_types": int(complaints["fraud_type"].nunique()),
        "avg_transactions_per_complaint": round(float(transactions.groupby("complaint_id").size().mean()), 3),
        "avg_candidates_per_complaint": rank_stats.get("avg_candidates_per_complaint", 0),
        "ranking_positive_negative_ratio": _pos_neg_ratio_from_stats(rank_stats),
        "geographic_distribution_by_city": complaints["victim_city"].value_counts().to_dict(),
        "fraud_type_distribution": complaints["fraud_type"].value_counts().to_dict(),
        "time_window_distribution": time_labels["time_window_label"].value_counts().sort_index().to_dict() if len(time_labels) else {},
        "candidate_retrieval": rank_stats,
        "recall_at_k": rank_stats.get("recall_at_k", {}),
    }
    return stats

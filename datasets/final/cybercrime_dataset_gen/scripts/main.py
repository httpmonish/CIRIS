"""Orchestrates the full synthetic cybercrime ATM-prediction dataset build.

Run with:  python3 main.py
Control scale with:  DATASET_SCALE=demo|dev|full python3 main.py
"""

import json
import os
import time
import numpy as np
import pandas as pd

import config
from gen_atms import generate_atms
from gen_complaints import generate_complaints
from gen_accounts import generate_accounts, generate_upi_entities
from gen_clusters import build_clusters, assign_clusters_to_complaints
from gen_flow import generate_flow_for_complaints
from gen_rank_pairs import generate_rank_pairs, determine_actionable_split
from validate import validate_all
from split_and_stats import build_statistics


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main():
    rng = np.random.default_rng(config.SEED)
    out = config.OUT_DIR
    os.makedirs(out, exist_ok=True)

    log(f"Scale = {config.SCALE} | complaints={config.N_COMPLAINTS} atms={config.N_ATMS} "
        f"accounts={config.N_ACCOUNTS} transactions_target={config.N_TRANSACTIONS}")

    log("Generating ATM master...")
    atms = generate_atms(rng)

    log("Generating complaints...")
    complaints = generate_complaints(rng)

    log("Generating accounts...")
    accounts = generate_accounts(rng)

    log("Generating UPI entities...")
    upi_entities = generate_upi_entities(rng, accounts)

    log("Building fraud clusters...")
    clusters = build_clusters(rng, accounts, atms)
    cluster_lookup = {c["cluster_id"]: c for c in clusters}
    cluster_assign = assign_clusters_to_complaints(rng, complaints, clusters)

    log("Simulating transaction chains + withdrawal events...")
    transactions, withdrawals, case_links, graph_edges = generate_flow_for_complaints(
        rng, complaints, accounts, atms, clusters, cluster_assign
    )

    log(f"  -> {len(transactions)} transactions, {len(withdrawals)} withdrawals, "
        f"{len(graph_edges)} graph edges")

    # Fill in upi_id on transactions (pick a upi belonging to the 'to' account)
    log("Linking UPI IDs to transactions...")
    acc_to_upis = upi_entities.groupby("account_id")["upi_id"].apply(list).to_dict()
    upi_choice = []
    for to_acc in transactions["to_account_id"]:
        opts = acc_to_upis.get(to_acc)
        upi_choice.append(rng.choice(opts) if opts else "")
    transactions["upi_id"] = upi_choice

    # Update upi_entities linked_case_count / linked_account_count from case history
    upi_case_counts = transactions.groupby("upi_id")["complaint_id"].nunique().to_dict()
    upi_acc_counts = transactions.groupby("upi_id")["from_account_id"].nunique().to_dict()
    upi_entities["linked_case_count"] = upi_entities["upi_id"].map(upi_case_counts).fillna(0).astype(int)
    upi_entities["linked_account_count"] = upi_entities["upi_id"].map(upi_acc_counts).fillna(0).astype(int)

    log("Determining actionable complaints + chronological train/val/test split "
        "(upfront, before the heavy feature loop)...")
    train_ids, val_ids, test_ids = determine_actionable_split(complaints, withdrawals)
    log(f"  -> train={len(train_ids)} val={len(val_ids)} test={len(test_ids)} actionable complaints")

    log("Running hybrid candidate retrieval + as-of-T feature engineering, "
        "streaming rank_pairs.csv (+ train/val/test splits) directly to disk...")
    time_labels, anomaly_features, rank_stats = generate_rank_pairs(
        rng, complaints, atms, withdrawals, transactions, case_links, graph_edges,
        accounts, cluster_lookup, out, train_ids, val_ids, test_ids,
        config.CANDIDATE_RECALL_TARGETS,
    )
    log(f"  -> {rank_stats['total_rank_pair_rows']} rank pairs across "
        f"{rank_stats['total_actionable_complaints']} actionable complaints")
    log(f"  -> Recall@K: {rank_stats['recall_at_k']}")

    log("Running leakage/quality validation...")
    leakage_report = validate_all(complaints, accounts, atms, transactions, withdrawals, rank_stats)
    leakage_report["candidate_retrieval_stats"] = rank_stats

    log("Building statistics.json...")
    statistics = build_statistics(complaints, accounts, atms, transactions, withdrawals,
                                   time_labels, rank_stats)
    statistics["split_sizes"] = {
        "train_complaints": len(train_ids), "validation_complaints": len(val_ids),
        "test_complaints": len(test_ids),
    }
    statistics["total_fraud_clusters"] = len(clusters)
    statistics["total_cross_case_links"] = int(case_links["cluster_id"].value_counts().gt(1).sum())
    statistics["avg_accounts_per_case"] = round(
        case_links["chain_accounts"].apply(lambda s: len(s.split("|"))).mean(), 3
    ) if len(case_links) else 0

    # ---------------- write everything out ----------------
    # (rank_pairs.csv, time_labels.csv, anomaly_features.csv + their
    # train/validation/test splits were already streamed to disk inside
    # generate_rank_pairs — nothing more to write for those here)
    log("Writing remaining CSVs...")
    complaints.to_csv(f"{out}/complaints.csv", index=False)
    accounts.to_csv(f"{out}/accounts.csv", index=False)
    upi_entities.to_csv(f"{out}/upi_entities.csv", index=False)
    transactions.to_csv(f"{out}/transactions.csv", index=False)
    withdrawals.to_csv(f"{out}/withdrawals.csv", index=False)
    atms.to_csv(f"{out}/atm_master.csv", index=False)
    case_links.to_csv(f"{out}/case_links.csv", index=False)
    graph_edges.to_csv(f"{out}/graph_edges.csv", index=False)

    with open(f"{out}/metadata/leakage_report.json", "w") as f:
        json.dump(leakage_report, f, indent=2, default=str)
    with open(f"{out}/metadata/statistics.json", "w") as f:
        json.dump(statistics, f, indent=2, default=str)

    generation_config = {
        "seed": config.SEED,
        "scale": config.SCALE,
        "n_complaints": config.N_COMPLAINTS,
        "n_transactions_generated": int(len(transactions)),
        "n_accounts": config.N_ACCOUNTS,
        "n_atms": config.N_ATMS,
        "n_withdrawals": config.N_WITHDRAWALS,
        "sim_start": config.SIM_START,
        "sim_end": config.SIM_END,
        "candidate_recall_targets": config.CANDIDATE_RECALL_TARGETS,
    }
    with open(f"{out}/metadata/generation_config.json", "w") as f:
        json.dump(generation_config, f, indent=2, default=str)

    write_schema_and_dictionary(out)

    log("Done.")
    return statistics, leakage_report


def write_schema_and_dictionary(out):
    schema = {
        "complaints.csv": list_cols(f"{out}/complaints.csv"),
        "accounts.csv": list_cols(f"{out}/accounts.csv"),
        "upi_entities.csv": list_cols(f"{out}/upi_entities.csv"),
        "transactions.csv": list_cols(f"{out}/transactions.csv"),
        "withdrawals.csv": list_cols(f"{out}/withdrawals.csv"),
        "atm_master.csv": list_cols(f"{out}/atm_master.csv"),
        "case_links.csv": list_cols(f"{out}/case_links.csv"),
        "graph_edges.csv": list_cols(f"{out}/graph_edges.csv"),
        "rank_pairs.csv": list_cols(f"{out}/rank_pairs.csv"),
        "time_labels.csv": list_cols(f"{out}/time_labels.csv"),
        "anomaly_features.csv": list_cols(f"{out}/anomaly_features.csv"),
    }
    with open(f"{out}/metadata/schema.json", "w") as f:
        json.dump(schema, f, indent=2)

    rows = []
    for fname, cols in schema.items():
        for c in cols:
            rows.append({"file": fname, "column": c})
    pd.DataFrame(rows).to_csv(f"{out}/metadata/data_dictionary.csv", index=False)


def list_cols(path):
    return list(pd.read_csv(path, nrows=1).columns)


if __name__ == "__main__":
    main()

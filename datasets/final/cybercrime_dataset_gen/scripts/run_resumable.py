"""Resumable driver for large (e.g. full 50k-complaint) runs.

Each invocation only has a few minutes of wall-clock budget available, so
this script does ONE of two things per call and then exits cleanly:

  1. SETUP (first call only): generate all the non-rank_pairs data (complaints,
     accounts, ATMs, transactions, withdrawals, clusters, graph edges), write
     the static CSVs, build the as-of-T lookup context once, and pickle
     everything needed to /checkpoint/ so later calls don't redo it.

  2. CHUNK (every call after setup): load the pickled context, process the
     next CHUNK_SIZE complaints, append their rows to rank_pairs.csv /
     time_labels.csv / anomaly_features.csv (+ train/val/test splits), and
     save updated progress + running statistics to checkpoint/state.json.
     When the last chunk finishes, it also runs FINALIZE (leakage report,
     statistics.json, schema, data dictionary) and marks the run done.

Run it repeatedly until it prints "RUN COMPLETE":
    DATASET_SCALE=full python3 run_resumable.py
"""

import json
import os
import pickle
import time
import numpy as np
import pandas as pd

import config
from gen_atms import generate_atms
from gen_complaints import generate_complaints
from gen_accounts import generate_accounts, generate_upi_entities
from gen_clusters import build_clusters, assign_clusters_to_complaints
from gen_flow import generate_flow_for_complaints
from gen_rank_pairs import (
    build_rank_pair_context, process_one_complaint, determine_actionable_split,
    open_all_writers,
)
from validate import validate_all
from split_and_stats import build_statistics
from main import write_schema_and_dictionary

CHECKPOINT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "checkpoint")
STATE_PATH = os.path.join(CHECKPOINT_DIR, "state.json")
DATA_PICKLE = os.path.join(CHECKPOINT_DIR, "base_data.pkl")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "4000"))


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_setup():
    rng = np.random.default_rng(config.SEED)
    out = config.OUT_DIR
    os.makedirs(out, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    log(f"SETUP: Scale = {config.SCALE} | complaints={config.N_COMPLAINTS} atms={config.N_ATMS} "
        f"accounts={config.N_ACCOUNTS}")

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

    log("Linking UPI IDs to transactions...")
    acc_to_upis = upi_entities.groupby("account_id")["upi_id"].apply(list).to_dict()
    upi_choice = []
    for to_acc in transactions["to_account_id"]:
        opts = acc_to_upis.get(to_acc)
        upi_choice.append(rng.choice(opts) if opts else "")
    transactions["upi_id"] = upi_choice
    upi_case_counts = transactions.groupby("upi_id")["complaint_id"].nunique().to_dict()
    upi_acc_counts = transactions.groupby("upi_id")["from_account_id"].nunique().to_dict()
    upi_entities["linked_case_count"] = upi_entities["upi_id"].map(upi_case_counts).fillna(0).astype(int)
    upi_entities["linked_account_count"] = upi_entities["upi_id"].map(upi_acc_counts).fillna(0).astype(int)

    log("Writing static CSVs (complaints/accounts/atms/transactions/withdrawals/...)...")
    complaints.to_csv(f"{out}/complaints.csv", index=False)
    accounts.to_csv(f"{out}/accounts.csv", index=False)
    upi_entities.to_csv(f"{out}/upi_entities.csv", index=False)
    transactions.to_csv(f"{out}/transactions.csv", index=False)
    withdrawals.to_csv(f"{out}/withdrawals.csv", index=False)
    atms.to_csv(f"{out}/atm_master.csv", index=False)
    case_links.to_csv(f"{out}/case_links.csv", index=False)
    graph_edges.to_csv(f"{out}/graph_edges.csv", index=False)

    log("Determining actionable complaints + chronological split...")
    train_ids, val_ids, test_ids = determine_actionable_split(complaints, withdrawals)
    log(f"  -> train={len(train_ids)} val={len(val_ids)} test={len(test_ids)}")

    log("Building as-of-T lookup context (static ATM density + hotspot buckets)...")
    ctx = build_rank_pair_context(
        complaints, atms, withdrawals, transactions, case_links, graph_edges,
        accounts, cluster_lookup,
    )

    log("Opening output writers (header row)...")
    rank_w, time_w, anomaly_w = open_all_writers(out, train_ids, val_ids, test_ids, mode="w")
    rank_w.close(); time_w.close(); anomaly_w.close()

    log("Pickling base data + context for chunked resumption...")
    with open(DATA_PICKLE, "wb") as f:
        pickle.dump({
            "complaints": complaints, "accounts": accounts, "atms": atms,
            "transactions": transactions, "withdrawals": withdrawals,
            "train_ids": train_ids, "val_ids": val_ids, "test_ids": test_ids,
            "ctx": ctx,
        }, f, protocol=pickle.HIGHEST_PROTOCOL)

    state = {
        "next_index": 0, "total_complaints": len(complaints),
        "total_actionable": 0, "recall_union_hits": 0, "recall_denom": 0,
        "forced_insertions": 0, "candidate_count_sum": 0,
        "recall_at_k_hits": {str(k): 0 for k in config.CANDIDATE_RECALL_TARGETS},
        "n_train": 0, "n_val": 0, "n_test": 0, "done": False,
    }
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
    log("SETUP complete. Run again to start processing chunks.")


def run_chunk():
    with open(STATE_PATH) as f:
        state = json.load(f)
    if state["done"]:
        log("Already done -- nothing to do. (See dataset/metadata/ for final outputs.)")
        return

    with open(DATA_PICKLE, "rb") as f:
        data = pickle.load(f)

    complaints = data["complaints"]
    ctx = data["ctx"]
    train_ids, val_ids, test_ids = data["train_ids"], data["val_ids"], data["test_ids"]
    out = config.OUT_DIR
    recall_ks = config.CANDIDATE_RECALL_TARGETS

    start = state["next_index"]
    end = min(start + CHUNK_SIZE, state["total_complaints"])
    log(f"CHUNK: processing complaints [{start}:{end}] of {state['total_complaints']}...")

    rank_w, time_w, anomaly_w = open_all_writers(out, train_ids, val_ids, test_ids, mode="a")
    recall_at_k_hits = {int(k): v for k, v in state["recall_at_k_hits"].items()}
    try:
        chunk_df = complaints.iloc[start:end]
        for local_i, row in enumerate(chunk_df.itertuples(index=False)):
            global_idx = start + local_i
            result = process_one_complaint(ctx, row, global_idx, recall_ks)
            if result is None:
                continue
            time_row, anomaly_row, rank_rows, hit, forced, n_cand, recall_hit = result
            cid = row.complaint_id

            state["total_actionable"] += 1
            state["recall_denom"] += 1
            if hit:
                state["recall_union_hits"] += 1
            if forced:
                state["forced_insertions"] += 1
            state["candidate_count_sum"] += n_cand
            for k, v in recall_hit.items():
                if v:
                    recall_at_k_hits[k] += 1

            time_w.write(time_row, cid)
            anomaly_w.write(anomaly_row, cid)
            for rr in rank_rows:
                rank_w.write(rr, cid)
    finally:
        state["n_train"] = state.get("n_train", 0) + rank_w.n_train
        state["n_val"] = state.get("n_val", 0) + rank_w.n_val
        state["n_test"] = state.get("n_test", 0) + rank_w.n_test
        rank_w.close(); time_w.close(); anomaly_w.close()

    state["next_index"] = end
    state["recall_at_k_hits"] = {str(k): v for k, v in recall_at_k_hits.items()}
    log(f"  -> chunk done. total_actionable so far={state['total_actionable']}, "
        f"rows so far={state['n_train'] + state['n_val'] + state['n_test']:,}")

    if end >= state["total_complaints"]:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        log("Last chunk finished -- running FINALIZE...")
        run_finalize(data, state)
        state["done"] = True

    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)

    if state["done"]:
        log("RUN COMPLETE.")
    else:
        pct = 100.0 * end / state["total_complaints"]
        log(f"Progress: {end}/{state['total_complaints']} complaints ({pct:.1f}%). "
            f"Run again to continue.")


def run_finalize(data, state):
    out = config.OUT_DIR
    complaints, accounts, atms = data["complaints"], data["accounts"], data["atms"]
    transactions, withdrawals = data["transactions"], data["withdrawals"]

    total_denom = max(1, state["recall_denom"])
    total_actionable = max(1, state["total_actionable"])
    rank_stats = {
        "total_actionable_complaints": state["total_actionable"],
        "total_rank_pair_rows": state["n_train"] + state["n_val"] + state["n_test"],
        "split_row_counts": {"train": state["n_train"], "validation": state["n_val"], "test": state["n_test"]},
        "recall_of_union_candidate_set": round(state["recall_union_hits"] / total_denom, 4),
        "forced_insertions_of_true_atm": state["forced_insertions"],
        "forced_insertion_rate": round(state["forced_insertions"] / total_denom, 4),
        "avg_candidates_per_complaint": round(state["candidate_count_sum"] / total_actionable, 3),
        "recall_at_k": {
            f"recall_at_{k}": round(v / total_actionable, 4)
            for k, v in {int(kk): vv for kk, vv in state["recall_at_k_hits"].items()}.items()
        },
    }

    log("Reading back time_labels.csv for statistics (small file)...")
    time_labels = pd.read_csv(f"{out}/time_labels.csv")

    log("Running leakage/quality validation...")
    leakage_report = validate_all(complaints, accounts, atms, transactions, withdrawals, rank_stats)
    leakage_report["candidate_retrieval_stats"] = rank_stats

    log("Building statistics.json...")
    statistics = build_statistics(complaints, accounts, atms, transactions, withdrawals,
                                   time_labels, rank_stats)
    statistics["split_sizes"] = {
        "train_complaints": len(data["train_ids"]), "validation_complaints": len(data["val_ids"]),
        "test_complaints": len(data["test_ids"]),
    }

    with open(f"{out}/metadata/leakage_report.json", "w") as f:
        json.dump(leakage_report, f, indent=2, default=str)
    with open(f"{out}/metadata/statistics.json", "w") as f:
        json.dump(statistics, f, indent=2, default=str)

    generation_config = {
        "seed": config.SEED, "scale": config.SCALE,
        "n_complaints": config.N_COMPLAINTS,
        "n_transactions_generated": int(len(transactions)),
        "n_accounts": config.N_ACCOUNTS, "n_atms": config.N_ATMS,
        "n_withdrawals": config.N_WITHDRAWALS,
        "sim_start": config.SIM_START, "sim_end": config.SIM_END,
        "candidate_recall_targets": config.CANDIDATE_RECALL_TARGETS,
    }
    with open(f"{out}/metadata/generation_config.json", "w") as f:
        json.dump(generation_config, f, indent=2, default=str)

    write_schema_and_dictionary(out)
    log(f"FINALIZE complete. total_violations={leakage_report['total_violations']}")


if __name__ == "__main__":
    if not os.path.exists(STATE_PATH):
        run_setup()
    else:
        run_chunk()

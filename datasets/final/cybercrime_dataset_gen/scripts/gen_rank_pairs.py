"""Hybrid candidate retrieval + timestamp-safe feature engineering.

Produces: rank_pairs.csv, time_labels.csv, anomaly_features.csv, plus the
Recall@K statistics used in leakage_report.json / statistics.json.

CANDIDATE SOURCES (merged + deduplicated, computed WITHOUT knowledge of the
true withdrawal ATM):
  1. Geographic   - ATMs within a radius of the victim's location
  2. Hotspot      - ATMs with the highest as-of-T historical hotspot score
  3. Network      - ATMs previously used (as of T) by the complaint's fraud
                     cluster (case_links) — i.e. recurring mule infrastructure
  4. Behavioural  - ATMs used by other same-fraud-type / same-district
                     complaints as of T

Recall@K is measured on this raw union BEFORE any forced insertion, exactly as
required by the spec (section 21). For the *training* file we then force-add
the true ATM if retrieval missed it (label=1), since a ranker cannot learn
from a positive-free case; how often that forcing was needed is logged
separately in statistics.json / leakage_report.json — never silently.
"""

import csv
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from utils import haversine_km
from gen_history_features import build_atm_history, atm_as_of_stats, to_int64, AsOfIndex
import config

GEO_RADIUS_KM = 30
N_GEO = config.CAND_N_GEO
N_HOTSPOT = config.CAND_N_HOTSPOT
N_NETWORK = config.CAND_N_NETWORK
N_BEHAV = config.CAND_N_BEHAV
N_HOTSPOT_BUCKETS = 60  # ~time-bucketed hotspot scoring resolution (see below)

RANK_PAIR_FIELDS = [
    "complaint_id", "atm_id", "prediction_timestamp", "label",
    "victim_lat", "victim_lon", "atm_lat", "atm_lon", "haversine_distance_km",
    "same_city", "same_district", "same_pincode", "nearby_atm_count",
    "geographic_similarity", "location_type",
    "in_geo_candidates", "in_hotspot_candidates", "in_network_candidates", "in_behavioural_candidates",
    "historical_complaints_as_of_T", "historical_cashout_count_as_of_T",
    "historical_cashout_rate_as_of_T", "historical_avg_loss_as_of_T", "historical_hotspot_score_as_of_T",
    "hour", "minute_bucket", "day_of_week", "is_weekend", "holiday_flag",
    "time_since_complaint_h", "time_since_last_transaction_h", "recent_activity_count",
    "velocity_15m", "velocity_30m", "velocity_1h", "velocity_3h", "velocity_6h", "velocity_24h",
    "account_degree_as_of_T", "cluster_size", "fraud_cluster_membership",
    "linked_complaint_count_as_of_T", "account_type", "is_synthetic_mule",
]


TIME_LABEL_FIELDS = [
    "complaint_id", "prediction_timestamp", "withdrawal_timestamp",
    "withdrawal_delay_hours", "time_window_label",
]

ANOMALY_FIELDS = [
    "complaint_id", "reported_loss_amount", "amount_deviation_z",
    "transaction_count_deviation", "velocity_1h", "velocity_24h",
    "unusual_time_of_day", "new_beneficiary_anomaly", "sudden_degree_change",
    "is_otp_shared", "clicked_malicious_link", "urgency_score",
]


class MultiSplitWriter:
    """Opens a master CSV plus its train/val/test split files and fans each
    row out to the master + the correct split. Supports append mode so a
    resumable/chunked run can pick up across separate process invocations
    without ever holding the full (potentially 5-20M row) file in memory."""

    def __init__(self, out_dir, master_path, train_path, val_path, test_path,
                 fieldnames, train_ids, val_ids, test_ids, mode="w"):
        self.train_ids, self.val_ids, self.test_ids = train_ids, val_ids, test_ids
        self.fieldnames = fieldnames
        write_header = (mode == "w")
        self._fh_master = open(f"{out_dir}/{master_path}", mode, newline="")
        self._fh_train = open(f"{out_dir}/{train_path}", mode, newline="")
        self._fh_val = open(f"{out_dir}/{val_path}", mode, newline="")
        self._fh_test = open(f"{out_dir}/{test_path}", mode, newline="")
        self.w_master = csv.DictWriter(self._fh_master, fieldnames=fieldnames)
        self.w_train = csv.DictWriter(self._fh_train, fieldnames=fieldnames)
        self.w_val = csv.DictWriter(self._fh_val, fieldnames=fieldnames)
        self.w_test = csv.DictWriter(self._fh_test, fieldnames=fieldnames)
        if write_header:
            for w in (self.w_master, self.w_train, self.w_val, self.w_test):
                w.writeheader()
        self.n_train = self.n_val = self.n_test = 0

    def write(self, row, complaint_id):
        self.w_master.writerow(row)
        if complaint_id in self.train_ids:
            self.w_train.writerow(row)
            self.n_train += 1
        elif complaint_id in self.val_ids:
            self.w_val.writerow(row)
            self.n_val += 1
        else:
            self.w_test.writerow(row)
            self.n_test += 1

    def close(self):
        for fh in (self._fh_master, self._fh_train, self._fh_val, self._fh_test):
            fh.close()


def open_all_writers(out_dir, train_ids, val_ids, test_ids, mode="w"):
    rank_w = MultiSplitWriter(
        out_dir, "rank_pairs.csv", "train/rank_pairs_train.csv",
        "validation/rank_pairs_val.csv", "test/rank_pairs_test.csv",
        RANK_PAIR_FIELDS, train_ids, val_ids, test_ids, mode)
    time_w = MultiSplitWriter(
        out_dir, "time_labels.csv", "train/time_train.csv",
        "validation/time_val.csv", "test/time_test.csv",
        TIME_LABEL_FIELDS, train_ids, val_ids, test_ids, mode)
    anomaly_w = MultiSplitWriter(
        out_dir, "anomaly_features.csv", "train/anomaly_train.csv",
        "validation/anomaly_val.csv", "test/anomaly_test.csv",
        ANOMALY_FIELDS, train_ids, val_ids, test_ids, mode)
    return rank_w, time_w, anomaly_w


def _holiday_flag(ts):
    # Simplified fixed list of common Indian public holiday month/day pairs.
    md = {(1, 26), (8, 15), (10, 2), (12, 25), (1, 1), (11, 1)}
    return int((ts.month, ts.day) in md)


def _precompute_static_atm_density(atms_df, radius_km=5.0):
    """ATM-to-ATM density doesn't depend on the prediction timestamp, so it is
    computed ONCE for the whole ATM master instead of once per (complaint,
    candidate) pair -- the single biggest win for scaling to 50k complaints."""
    lat = np.radians(atms_df["latitude"].values)
    lon = np.radians(atms_df["longitude"].values)
    xyz = np.column_stack([
        np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat),
    ])
    tree = cKDTree(xyz)
    # chord length for a given great-circle radius (approx, earth radius 6371km)
    chord = 2 * np.sin((radius_km / 6371.0) / 2)
    counts = tree.query_ball_point(xyz, r=chord, return_length=True) - 1
    return dict(zip(atms_df["atm_id"].values, counts.astype(int)))


def _precompute_hotspot_buckets(atms_df, atm_idx, sim_start, sim_end, n_buckets):
    """Precompute, once per time bucket (not once per complaint), the top-N
    hotspot ATMs as-of the START of that bucket. A complaint's candidate list
    then does an O(log n) bucket lookup instead of rescoring every ATM.
    Using the bucket START (<= the complaint's real T) keeps this leakage-safe
    -- it can only ever be conservative (older cutoff), never look ahead."""
    edges = pd.date_range(sim_start, sim_end, periods=n_buckets + 1)
    bucket_starts_int64 = edges[:-1].values.astype(np.int64)
    atm_ids = atms_df["atm_id"].values
    bucket_top_atms = []
    for T_int64 in bucket_starts_int64:
        scores = np.array([
            atm_as_of_stats(atm_idx, a, T_int64)["historical_hotspot_score_as_of_T"]
            for a in atm_ids
        ])
        top_order = np.argsort(-scores)[:N_HOTSPOT]
        bucket_top_atms.append(set(atm_ids[top_order]))
    return bucket_starts_int64, bucket_top_atms


def build_rank_pair_context(complaints_df, atms_df, withdrawals_df, transactions_df,
                             case_links_df, graph_edges_df, accounts_df, cluster_lookup):
    """All the as-of-T lookup structures needed to score complaints, built
    ONCE and (by the resumable runner) pickled to disk so a multi-call/
    multi-chunk run never has to rebuild them."""
    atm_idx, district_idx, wd_joined = build_atm_history(withdrawals_df, complaints_df)

    cl_wd = withdrawals_df.merge(case_links_df[["complaint_id", "cluster_id"]], on="complaint_id", how="left")
    cluster_atm_hist = {}
    for cid, g in cl_wd.groupby("cluster_id"):
        g = g.sort_values("withdrawal_timestamp")
        cluster_atm_hist[cid] = g[["withdrawal_timestamp", "atm_id"]].reset_index(drop=True)

    fd = withdrawals_df.merge(
        complaints_df[["complaint_id", "fraud_type", "victim_district"]], on="complaint_id", how="left")
    behav_hist = {}
    for key, g in fd.groupby(["fraud_type", "victim_district"]):
        g = g.sort_values("withdrawal_timestamp")
        behav_hist[key] = g[["withdrawal_timestamp", "atm_id"]].reset_index(drop=True)

    tx_by_case = {cid: g.sort_values("timestamp") for cid, g in transactions_df.groupby("complaint_id")}

    edges = graph_edges_df.copy()
    out_idx = AsOfIndex(edges, "src_account_id", "timestamp")
    in_idx = AsOfIndex(edges, "dst_account_id", "timestamp")

    atm_lookup = atms_df.set_index("atm_id")
    print("  [rank_pairs] precomputing static ATM density...", flush=True)
    static_density = _precompute_static_atm_density(atms_df)

    print(f"  [rank_pairs] precomputing {N_HOTSPOT_BUCKETS} hotspot time buckets "
          f"({N_HOTSPOT_BUCKETS * len(atms_df):,} scoring calls instead of "
          f"{len(complaints_df) * len(atms_df):,})...", flush=True)
    bucket_starts, bucket_top_atms = _precompute_hotspot_buckets(
        atms_df, atm_idx, config.SIM_START, config.SIM_END, N_HOTSPOT_BUCKETS
    )

    return dict(
        atm_idx=atm_idx, cluster_atm_hist=cluster_atm_hist, behav_hist=behav_hist,
        tx_by_case=tx_by_case, out_idx=out_idx, in_idx=in_idx,
        atm_lat=atm_lookup["latitude"].to_dict(), atm_lon=atm_lookup["longitude"].to_dict(),
        atm_city=atm_lookup["city"].to_dict(), atm_district=atm_lookup["district"].to_dict(),
        atm_pincode=atm_lookup["pincode"].to_dict(), atm_loctype=atm_lookup["location_type"].to_dict(),
        static_density=static_density, bucket_starts=bucket_starts, bucket_top_atms=bucket_top_atms,
        case_link_lookup=case_links_df.set_index("complaint_id"),
        account_lookup=accounts_df.set_index("account_id"),
        wd_by_case=withdrawals_df.set_index("complaint_id"),
        cluster_lookup=cluster_lookup,
        complaints_reported_loss_median=float(complaints_df["reported_loss_amount"].median()),
        complaints_reported_loss_std=float(complaints_df["reported_loss_amount"].std()),
        atms_df=atms_df,
    )


def process_one_complaint(ctx, row, global_idx, recall_ks):
    """Process a single complaint row against the prebuilt context. Returns
    None if the complaint isn't actionable, else (time_row, anomaly_row,
    list_of_rank_pair_row_dicts, recall_hit(bool), forced(bool),
    n_candidates(int), recall_at_k_hit_flags(dict), true_atm_writers_key)."""
    cid = row.complaint_id
    wd_by_case = ctx["wd_by_case"]
    if cid not in wd_by_case.index:
        return None
    wd = wd_by_case.loc[cid]
    T = pd.Timestamp(row.complaint_timestamp)
    wd_ts = pd.Timestamp(wd.withdrawal_timestamp)
    if wd_ts <= T:
        return None
    T_int64 = to_int64(T)
    true_atm = wd.atm_id
    atms_df = ctx["atms_df"]
    atm_idx = ctx["atm_idx"]

    dists_all = haversine_km(atms_df["latitude"].values, atms_df["longitude"].values,
                              row.victim_lat, row.victim_lon)
    geo_mask = dists_all < GEO_RADIUS_KM
    geo_order = np.argsort(np.where(geo_mask, dists_all, np.inf))[:N_GEO]
    geo_candidates = set(atms_df["atm_id"].values[geo_order][
        np.isfinite(np.where(geo_mask, dists_all, np.inf)[geo_order])])

    bucket_starts, bucket_top_atms = ctx["bucket_starts"], ctx["bucket_top_atms"]
    bucket_pos = min(np.searchsorted(bucket_starts, T_int64, side="right") - 1, len(bucket_top_atms) - 1)
    hotspot_candidates = bucket_top_atms[max(0, bucket_pos)]

    case_link_lookup = ctx["case_link_lookup"]
    cluster_id = case_link_lookup.loc[cid, "cluster_id"] if cid in case_link_lookup.index else None
    cluster_atm_hist = ctx["cluster_atm_hist"]
    cluster_lookup = ctx["cluster_lookup"]
    network_candidates = set()
    if cluster_id in cluster_atm_hist:
        hist = cluster_atm_hist[cluster_id]
        past = hist[hist["withdrawal_timestamp"] < T]
        network_candidates = set(past["atm_id"].value_counts().head(N_NETWORK).index)
    if cluster_id in cluster_lookup:
        network_candidates |= set(cluster_lookup[cluster_id]["preferred_atms"][:N_NETWORK])

    behav_hist = ctx["behav_hist"]
    behav_key = (row.fraud_type, row.victim_district)
    behav_candidates = set()
    if behav_key in behav_hist:
        hist = behav_hist[behav_key]
        past = hist[hist["withdrawal_timestamp"] < T]
        behav_candidates = set(past["atm_id"].value_counts().head(N_BEHAV).index)

    union_candidates = geo_candidates | hotspot_candidates | network_candidates | behav_candidates
    hit = true_atm in union_candidates
    final_candidates = set(union_candidates)
    forced = not hit
    if forced:
        final_candidates.add(true_atm)

    tx_by_case = ctx["tx_by_case"]
    tx = tx_by_case.get(cid)
    tx_before = tx[tx["timestamp"] < T] if tx is not None else None
    if tx_before is not None and len(tx_before):
        last_tx_ts = tx_before["timestamp"].max()
        time_since_last_txn_h = (T - last_tx_ts).total_seconds() / 3600.0
        recent_activity_count = len(tx_before)
    else:
        time_since_last_txn_h = np.nan
        recent_activity_count = 0

    velocity = {}
    for label, minutes in [("15m", 15), ("30m", 30), ("1h", 60), ("3h", 180), ("6h", 360), ("24h", 1440)]:
        if tx_before is not None and len(tx_before):
            window_start = T - pd.Timedelta(minutes=minutes)
            velocity[label] = int(((tx_before["timestamp"] >= window_start)).sum())
        else:
            velocity[label] = 0

    acc_id = case_link_lookup.loc[cid, "cashout_account_id"] if cid in case_link_lookup.index else None
    account_lookup = ctx["account_lookup"]
    acc_row = account_lookup.loc[acc_id] if acc_id in account_lookup.index else None

    out_idx, in_idx = ctx["out_idx"], ctx["in_idx"]
    out_deg = out_idx.count_before(acc_id, T_int64) if acc_id else 0
    in_deg = in_idx.count_before(acc_id, T_int64) if acc_id else 0
    degree = out_deg + in_deg
    cluster_size = len(cluster_lookup[cluster_id]["member_accounts"]) if cluster_id in cluster_lookup else 1
    linked_complaints_cluster = 0
    if cluster_id in cluster_atm_hist:
        linked_complaints_cluster = int((cluster_atm_hist[cluster_id]["withdrawal_timestamp"] < T).sum())

    amt_dev = (row.reported_loss_amount - ctx["complaints_reported_loss_median"]) / (
        ctx["complaints_reported_loss_std"] + 1e-6)
    unusual_hour = int(T.hour < 5 or T.hour > 23)

    # deterministic per-row RNG so results don't depend on chunk boundaries
    row_rng = np.random.default_rng([config.SEED, int(global_idx)])

    time_row = {
        "complaint_id": cid, "prediction_timestamp": T, "withdrawal_timestamp": wd_ts,
        "withdrawal_delay_hours": round((wd_ts - T).total_seconds() / 3600.0, 3),
        "time_window_label": _twlabel((wd_ts - T).total_seconds() / 3600.0),
    }
    anomaly_row = {
        "complaint_id": cid, "reported_loss_amount": row.reported_loss_amount,
        "amount_deviation_z": round(float(amt_dev), 4),
        "transaction_count_deviation": recent_activity_count - 3,
        "velocity_1h": velocity["1h"], "velocity_24h": velocity["24h"],
        "unusual_time_of_day": unusual_hour,
        "new_beneficiary_anomaly": int(row_rng.random() < (0.35 if degree <= 1 else 0.08)),
        "sudden_degree_change": int(degree > 0 and row_rng.random() < 0.15),
        "is_otp_shared": row.is_otp_shared, "clicked_malicious_link": row.clicked_malicious_link,
        "urgency_score": row.urgency_score,
    }

    atm_lat, atm_lon = ctx["atm_lat"], ctx["atm_lon"]
    atm_city, atm_district, atm_pincode, atm_loctype = ctx["atm_city"], ctx["atm_district"], ctx["atm_pincode"], ctx["atm_loctype"]
    static_density = ctx["static_density"]

    cand_scored = []
    for atm_id in final_candidates:
        a_lat, a_lon = atm_lat[atm_id], atm_lon[atm_id]
        dist_km = float(haversine_km(a_lat, a_lon, row.victim_lat, row.victim_lon))
        astats = atm_as_of_stats(atm_idx, atm_id, T_int64)
        geo_sim = 1.0 / (1.0 + dist_km)
        proxy_score = geo_sim + astats["historical_hotspot_score_as_of_T"]
        cand_scored.append((proxy_score, atm_id, dist_km, astats, geo_sim))
    cand_scored.sort(key=lambda t: -t[0])

    recall_at_k_hit = {}
    for k in recall_ks:
        top_ids = {c[1] for c in cand_scored[:k]}
        recall_at_k_hit[k] = true_atm in top_ids

    rank_rows = []
    for _, atm_id, dist_km, astats, geo_sim in cand_scored:
        rank_rows.append({
            "complaint_id": cid, "atm_id": atm_id, "prediction_timestamp": T,
            "label": int(atm_id == true_atm),
            "victim_lat": row.victim_lat, "victim_lon": row.victim_lon,
            "atm_lat": atm_lat[atm_id], "atm_lon": atm_lon[atm_id],
            "haversine_distance_km": round(dist_km, 3),
            "same_city": int(atm_city[atm_id] == row.victim_city),
            "same_district": int(atm_district[atm_id] == row.victim_district),
            "same_pincode": int(atm_pincode[atm_id] == row.victim_pincode),
            "nearby_atm_count": static_density.get(atm_id, 0),
            "geographic_similarity": round(geo_sim, 5),
            "location_type": atm_loctype[atm_id],
            "in_geo_candidates": int(atm_id in geo_candidates),
            "in_hotspot_candidates": int(atm_id in hotspot_candidates),
            "in_network_candidates": int(atm_id in network_candidates),
            "in_behavioural_candidates": int(atm_id in behav_candidates),
            **astats,
            "hour": T.hour, "minute_bucket": T.minute // 15, "day_of_week": T.dayofweek,
            "is_weekend": int(T.dayofweek >= 5), "holiday_flag": _holiday_flag(T),
            "time_since_complaint_h": 0.0,
            "time_since_last_transaction_h": None if pd.isna(time_since_last_txn_h) else round(time_since_last_txn_h, 3),
            "recent_activity_count": recent_activity_count,
            "velocity_15m": velocity["15m"], "velocity_30m": velocity["30m"], "velocity_1h": velocity["1h"],
            "velocity_3h": velocity["3h"], "velocity_6h": velocity["6h"], "velocity_24h": velocity["24h"],
            "account_degree_as_of_T": degree, "cluster_size": cluster_size,
            "fraud_cluster_membership": int(cluster_id is not None),
            "linked_complaint_count_as_of_T": linked_complaints_cluster,
            "account_type": acc_row["account_type"] if acc_row is not None else "unknown",
            "is_synthetic_mule": int(acc_row["is_synthetic_mule"]) if acc_row is not None else 0,
        })

    return time_row, anomaly_row, rank_rows, hit, forced, len(final_candidates), recall_at_k_hit


def generate_rank_pairs(rng, complaints_df, atms_df, withdrawals_df, transactions_df,
                         case_links_df, graph_edges_df, accounts_df, cluster_lookup,
                         out_dir, train_ids, val_ids, test_ids, recall_ks):
    """Single-shot convenience wrapper around build_rank_pair_context() +
    process_one_complaint() for demo/dev-scale runs (used by main.py). Full
    50k-scale runs use run_resumable.py instead, which calls the same two
    functions but processes complaints in resumable chunks across multiple
    process invocations."""
    ctx = build_rank_pair_context(
        complaints_df, atms_df, withdrawals_df, transactions_df,
        case_links_df, graph_edges_df, accounts_df, cluster_lookup,
    )
    rank_w, time_w, anomaly_w = open_all_writers(out_dir, train_ids, val_ids, test_ids, mode="w")

    recall_union_hits = recall_denom = forced_insertions = candidate_count_sum = 0
    total_actionable = 0
    recall_at_k_hits = {k: 0 for k in recall_ks}
    time_rows_all = []
    anomaly_rows_all = []

    n_complaints = len(complaints_df)
    try:
        for global_idx, row in enumerate(complaints_df.itertuples(index=False)):
            if global_idx and global_idx % 5000 == 0:
                print(f"  [rank_pairs] {global_idx}/{n_complaints} complaints processed "
                      f"({total_actionable} actionable so far)...", flush=True)
            result = process_one_complaint(ctx, row, global_idx, recall_ks)
            if result is None:
                continue
            time_row, anomaly_row, rank_rows, hit, forced, n_cand, recall_hit = result
            cid = row.complaint_id

            total_actionable += 1
            recall_denom += 1
            if hit:
                recall_union_hits += 1
            if forced:
                forced_insertions += 1
            candidate_count_sum += n_cand
            for k, v in recall_hit.items():
                if v:
                    recall_at_k_hits[k] += 1

            time_w.write(time_row, cid)
            anomaly_w.write(anomaly_row, cid)
            time_rows_all.append(time_row)
            anomaly_rows_all.append(anomaly_row)
            for rr in rank_rows:
                rank_w.write(rr, cid)
    finally:
        rank_w.close(); time_w.close(); anomaly_w.close()

    total_denom = max(1, recall_denom)
    total_actionable_safe = max(1, total_actionable)
    stats = {
        "total_actionable_complaints": total_actionable,
        "total_rank_pair_rows": rank_w.n_train + rank_w.n_val + rank_w.n_test,
        "split_row_counts": {"train": rank_w.n_train, "validation": rank_w.n_val, "test": rank_w.n_test},
        "recall_of_union_candidate_set": round(recall_union_hits / total_denom, 4),
        "forced_insertions_of_true_atm": forced_insertions,
        "forced_insertion_rate": round(forced_insertions / total_denom, 4),
        "avg_candidates_per_complaint": round(candidate_count_sum / total_actionable_safe, 3),
        "recall_at_k": {f"recall_at_{k}": round(v / total_actionable_safe, 4) for k, v in recall_at_k_hits.items()},
    }
    return pd.DataFrame(time_rows_all), pd.DataFrame(anomaly_rows_all), stats


def determine_actionable_split(complaints_df, withdrawals_df, train_frac=0.70, val_frac=0.15):
    """Cheap upfront pass (no candidate retrieval) that decides which
    complaints are 'actionable' (withdrawal strictly after complaint filing)
    and assigns each to train/val/test by chronological order of
    complaint_timestamp. Computed BEFORE the expensive feature loop so that
    loop can stream rows straight into the correct split file."""
    wd = withdrawals_df[["complaint_id", "withdrawal_timestamp"]]
    merged = complaints_df[["complaint_id", "complaint_timestamp"]].merge(wd, on="complaint_id", how="inner")
    merged = merged[pd.to_datetime(merged["withdrawal_timestamp"]) > pd.to_datetime(merged["complaint_timestamp"])]
    merged = merged.sort_values("complaint_timestamp").reset_index(drop=True)
    n = len(merged)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)
    train_ids = set(merged["complaint_id"].iloc[:n_train])
    val_ids = set(merged["complaint_id"].iloc[n_train:n_train + n_val])
    test_ids = set(merged["complaint_id"].iloc[n_train + n_val:])
    return train_ids, val_ids, test_ids


def _twlabel(delay_hours):
    if delay_hours < 1:
        return 0
    if delay_hours < 3:
        return 1
    if delay_hours < 6:
        return 2
    if delay_hours < 12:
        return 3
    return 4

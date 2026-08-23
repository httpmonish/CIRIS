"""
Untouched Test Evaluation & Dynamic E2E Benchmark for CIRIS / CIPHER ML V4 (V2 Frozen Retrieval).

Executes:
1. Full-scale untouched ranking test set evaluation on 1,973,305 rows (rank_pairs_test.csv)
   - Hit@1, Hit@5, Hit@10, NDCG@5, NDCG@10, MRR
   - Probability Calibration: Brier score, Log Loss, ECE (Expected Calibration Error)
2. Time-to-cashout untouched test evaluation
   - Regression MAE, RMSE, Classification Accuracy, Macro F1
3. Dynamic Candidate Retrieval Evaluation (True dynamic retrieval without ground-truth ATM insertion)
   - Recall@50, Recall@100, Recall@200, Recall@300, Union Recall, Missed count
4. Geographic Accuracy
   - Median geographic error (km), P90 geographic error (km) between Top-1 predicted ATM and actual withdrawal ATM
5. Operational Latency Profiles
   - Retrieval latency, feature latency, inference latency, total P50, total P95
6. Comparative Scorecard vs:
   - Baseline 1: Nearest ATM (pure proximity)
   - Baseline 2: Pure Hotspot Heuristic
   - Baseline 3: SKYVAR (SIH 2025 Baseline)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple
from sklearn.metrics import brier_score_loss, log_loss

from src.ml.data.loader import DatasetLoader
from src.ml.models.ranker import ATMRanker
from src.ml.models.time_predictor import TimeToCashoutPredictor
from src.ml.models.anomaly_detector import AnomalyDetector
from src.ml.models.fusion import MultiSignalRiskFusionEngine, ProbabilityCalibrator
from src.ml.features.feature_builder import FeatureBuilder
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.candidate_retriever import CandidateRetriever
from src.ml.contracts.schemas import ComplaintPayload, VictimLocation


def calculate_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper if i < n_bins - 1 else y_prob <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(y_true[in_bin])
            avg_confidence_in_bin = np.mean(y_prob[in_bin])
            ece += np.abs(accuracy_in_bin - avg_confidence_in_bin) * prop_in_bin
    return float(ece)


def run_evaluation(
    dataset_dir: str = "datasets/final",
    model_dir: str = "models/final_v2",
    n_e2e_cases: int = 500,
) -> Dict[str, Any]:
    print("=" * 80)
    print("CIRIS / CIPHER ML V4 (V2) — UNTOUCHED FINAL TEST SET EVALUATION")
    print(f"Dataset Directory: {dataset_dir}")
    print(f"Model Artifacts:   {model_dir}")
    print(f"Timestamp:         {datetime.now().isoformat()}")
    print("=" * 80)

    loader = DatasetLoader(dataset_dir)

    # 1. Load Model Suite
    print("\n[Step 1/6] Loading Frozen Production Model Artifacts from:", model_dir)
    ranker = ATMRanker()
    ranker.load(os.path.join(model_dir, "location_ranker.joblib"))

    time_predictor = TimeToCashoutPredictor()
    time_predictor.load(os.path.join(model_dir, "time_predictor.joblib"))

    anomaly_detector = AnomalyDetector()
    anomaly_detector.load(os.path.join(model_dir, "anomaly_detector.joblib"))

    fusion_engine = MultiSignalRiskFusionEngine()
    fusion_engine.load(os.path.join(model_dir, "fusion_engine.joblib"))
    calibrator = fusion_engine.calibrator

    atm_df = loader.load_atm_master()
    wd_df = loader.load_withdrawals()
    graph_edges_df = loader.load_graph_edges()
    cases_df = loader.load_case_links()
    upi_df = loader.load_upi_entities()
    comp_df = loader.load_complaints()

    spatial_index = SpatialIndex(atm_df)
    hotspot_cache = HistoricalHotspotCache(atm_master_df=atm_df, withdrawals_df=wd_df, complaints_df=comp_df)
    graph_engine = TemporalGraphEngine(graph_edges_df=graph_edges_df, case_links_df=cases_df, withdrawals_df=wd_df, upi_df=upi_df)

    retriever = CandidateRetriever(
        spatial_index=spatial_index,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
        geo_radius_km=250.0,
        geo_fallback_knn=200,
        top_hotspots_count=1500,
        enable_district_fallback=True,
        enable_state_fallback=True,
        state_top_k=100,
    )
    builder = FeatureBuilder(
        atm_master_df=atm_df,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
        spatial_index=spatial_index,
    )

    # 2. Evaluate Full-Scale Test Ranking Split (1,973,305 rows)
    print("\n[Step 2/6] Evaluating LambdaMART on Untouched Test Ranking Split (rank_pairs_test.csv)...")
    t0 = time.time()
    test_rank_df = loader.load_rank_split("test")
    load_duration = time.time() - t0
    print(f"  - Loaded {len(test_rank_df):,} test rank pairs in {load_duration:.2f}s")

    t0 = time.time()
    raw_ranking_metrics = ranker.evaluate(test_rank_df)
    rank_eval_duration = time.time() - t0
    print(f"  - Ranking evaluation completed in {rank_eval_duration:.2f}s")

    # Calibration Metrics on Test Split
    print("\n[Step 3/6] Computing Calibration & Log Loss on Test Split...")
    test_scores = ranker.predict_scores(test_rank_df)
    y_test = test_rank_df["label"].values.astype(int)
    cal_probs = calibrator.calibrate(test_scores)
    # Clip for safe log loss
    cal_probs_clipped = np.clip(cal_probs, 1e-6, 1.0 - 1e-6)

    brier = float(brier_score_loss(y_test, cal_probs))
    ll = float(log_loss(y_test, cal_probs_clipped))
    ece = calculate_ece(y_test, cal_probs, n_bins=10)

    calibration_metrics = {
        "brier_score": brier,
        "log_loss": ll,
        "expected_calibration_error_ece": ece,
    }

    # 3. Evaluate Time and Anomaly Models on Test Split
    print("\n[Step 4/6] Evaluating Time-to-Cashout and Anomaly Predictor on Test Split...")
    _, _, test_time = loader.load_time_splits()
    _, _, test_anom = loader.load_anomaly_splits()

    test_comp = comp_df[comp_df["complaint_id"].isin(test_time["complaint_id"])].copy()
    time_metrics = time_predictor.evaluate(test_comp, test_time)

    anom_scores = anomaly_detector.predict_anomaly_scores(test_anom)
    anom_metrics = {
        "n_test_samples": len(test_anom),
        "mean_anomaly_score": float(np.mean(anom_scores)),
        "std_anomaly_score": float(np.std(anom_scores)),
        "high_anomaly_rate": float(np.mean(anom_scores >= 0.70)),
    }

    # 4. True Dynamic E2E Benchmark (Zero Ground-Truth ATM Insertion)
    print(f"\n[Step 5/6] Running True Dynamic E2E Benchmark on {n_e2e_cases} Test Complaints (Zero Ground-Truth Insertion)...")
    wd_lookup = dict(zip(wd_df["complaint_id"], wd_df["atm_id"]))
    acc_lookup = dict(zip(cases_df["complaint_id"], cases_df["cashout_account_id"]))
    atm_coord_map = {str(r["atm_id"]).strip(): (float(r["latitude"]), float(r["longitude"])) for _, r in atm_df.iterrows()}

    # Select test set complaints
    test_cases_df = comp_df.tail(n_e2e_cases).copy()

    retrieval_stats = {
        "recall_at_50": 0,
        "recall_at_100": 0,
        "recall_at_200": 0,
        "recall_at_300": 0,
        "union_recall": 0,
        "missed_count": 0,
    }

    cipher_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0, "ndcg_5": [], "ndcg_10": [], "rr": []}
    nearest_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0}
    hotspot_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0}
    skyvar_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0}

    geo_errors_km = []

    latencies = {
        "retrieval_ms": [],
        "features_ms": [],
        "inference_ms": [],  # ranker + time + anom + fusion
        "total_ms": [],
    }

    total_valid_cases = 0

    for _, row in test_cases_df.iterrows():
        cid = str(row["complaint_id"])
        true_atm = str(wd_lookup.get(cid, "")).strip()
        if not true_atm:
            continue

        t_complaint = pd.to_datetime(row["complaint_timestamp"]).to_pydatetime()
        acc_id = acc_lookup.get(cid, None)
        chain_accs = [acc_id] if acc_id else None

        payload = ComplaintPayload(
            complaint_id=cid,
            complaint_timestamp=t_complaint,
            fraud_type=str(row.get("fraud_type", "UPI Fraud")),
            reported_loss_amount=float(row.get("reported_loss_amount", 50000.0)),
            victim_location=VictimLocation(
                latitude=float(row["victim_lat"]),
                longitude=float(row["victim_lon"]),
                city=str(row.get("victim_city", "")),
                district=str(row.get("victim_district", "")),
                state=str(row.get("victim_state", "")),
                pincode=str(row.get("victim_pincode", "")),
            ),
        )

        # Stage 0: Dynamic Retrieval
        t_start_ret = time.perf_counter()
        candidates = retriever.retrieve_candidates(
            complaint=payload,
            as_of_T=t_complaint,
            chain_accounts=chain_accs,
        )
        t_ret_ms = (time.perf_counter() - t_start_ret) * 1000.0

        cand_ids = [c.atm_id for c in candidates]
        is_in_union = true_atm in cand_ids

        if is_in_union:
            retrieval_stats["union_recall"] += 1
        else:
            retrieval_stats["missed_count"] += 1

        if true_atm in cand_ids[:50]:
            retrieval_stats["recall_at_50"] += 1
        if true_atm in cand_ids[:100]:
            retrieval_stats["recall_at_100"] += 1
        if true_atm in cand_ids[:200]:
            retrieval_stats["recall_at_200"] += 1
        if true_atm in cand_ids[:300]:
            retrieval_stats["recall_at_300"] += 1

        # Stage 1: Feature Building
        t_start_feat = time.perf_counter()
        feat_df = builder.build_features_for_candidates(
            complaint=payload,
            candidates=candidates,
            as_of_T=t_complaint,
            chain_accounts=chain_accs,
        )
        t_feat_ms = (time.perf_counter() - t_start_feat) * 1000.0

        # Stage 2-5: ML Inference (Ranker + Time + Anomaly + Fusion)
        t_start_inf = time.perf_counter()
        raw_scores = ranker.predict_scores(feat_df)
        feat_df["ranking_score"] = raw_scores
        feat_df_sorted = feat_df.sort_values(by="ranking_score", ascending=False).reset_index(drop=True)

        pred_delay, pred_window_name, window_probs = time_predictor.predict(payload)
        anom_score, anom_subs = anomaly_detector.predict_anomaly_score(payload)

        time_window_short = list(window_probs.keys())[0] if window_probs else "<1h"
        fused_predictions = fusion_engine.fuse_predictions(
            ranked_candidates_df=feat_df_sorted,
            predicted_delay_hours=pred_delay,
            predicted_time_window_short=time_window_short,
            predicted_time_window_full=pred_window_name,
            anomaly_score=anom_score,
            anomaly_sub_scores=anom_subs,
        )
        t_inf_ms = (time.perf_counter() - t_start_inf) * 1000.0
        t_tot_ms = t_ret_ms + t_feat_ms + t_inf_ms

        latencies["retrieval_ms"].append(t_ret_ms)
        latencies["features_ms"].append(t_feat_ms)
        latencies["inference_ms"].append(t_inf_ms)
        latencies["total_ms"].append(t_tot_ms)

        # Evaluate CIPHER Final Ranked Order
        cipher_ranked_ids = [p.atm_id for p in fused_predictions]
        rank_pos = None
        if true_atm in cipher_ranked_ids:
            rank_pos = cipher_ranked_ids.index(true_atm) + 1
            cipher_hits["rr"].append(1.0 / rank_pos)
            if rank_pos <= 1:
                cipher_hits["hit_1"] += 1
            if rank_pos <= 5:
                cipher_hits["hit_5"] += 1
                cipher_hits["ndcg_5"].append(1.0 / np.log2(rank_pos + 1))
            else:
                cipher_hits["ndcg_5"].append(0.0)
            if rank_pos <= 10:
                cipher_hits["hit_10"] += 1
                cipher_hits["ndcg_10"].append(1.0 / np.log2(rank_pos + 1))
            else:
                cipher_hits["ndcg_10"].append(0.0)
        else:
            cipher_hits["rr"].append(0.0)
            cipher_hits["ndcg_5"].append(0.0)
            cipher_hits["ndcg_10"].append(0.0)

        # Geographic Error Calculation
        if len(cipher_ranked_ids) > 0 and true_atm in atm_coord_map:
            top1_atm = cipher_ranked_ids[0]
            if top1_atm in atm_coord_map:
                p_lat, p_lon = atm_coord_map[top1_atm]
                a_lat, a_lon = atm_coord_map[true_atm]
                err_km = SpatialIndex.haversine_distance(p_lat, p_lon, a_lat, a_lon)
                geo_errors_km.append(err_km)

        # Baseline 1: Nearest ATM
        nearest_sorted = sorted(candidates, key=lambda c: c.distance_km)
        nearest_ids = [c.atm_id for c in nearest_sorted]
        if true_atm in nearest_ids[:1]:
            nearest_hits["hit_1"] += 1
        if true_atm in nearest_ids[:5]:
            nearest_hits["hit_5"] += 1
        if true_atm in nearest_ids[:10]:
            nearest_hits["hit_10"] += 1

        # Baseline 2: Pure Hotspot Heuristic
        hotspot_sorted = feat_df.sort_values(by="historical_hotspot_score_as_of_T", ascending=False)
        hotspot_ids = list(hotspot_sorted["atm_id"])
        if true_atm in hotspot_ids[:1]:
            hotspot_hits["hit_1"] += 1
        if true_atm in hotspot_ids[:5]:
            hotspot_hits["hit_5"] += 1
        if true_atm in hotspot_ids[:10]:
            hotspot_hits["hit_10"] += 1

        # Baseline 3: SKYVAR SIH 2025 Baseline
        skyvar_score = 0.60 * feat_df["geographic_similarity"] + 0.40 * (feat_df["nearby_atm_count"] / 20.0)
        feat_df["skyvar_score"] = skyvar_score
        skyvar_sorted = feat_df.sort_values(by="skyvar_score", ascending=False)
        skyvar_ids = list(skyvar_sorted["atm_id"])
        if true_atm in skyvar_ids[:1]:
            skyvar_hits["hit_1"] += 1
        if true_atm in skyvar_ids[:5]:
            skyvar_hits["hit_5"] += 1
        if true_atm in skyvar_ids[:10]:
            skyvar_hits["hit_10"] += 1

        total_valid_cases += 1

    n_cases = max(1, total_valid_cases)

    # 5. Compile Final Performance Records
    final_report = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "model_version": "v4.1.0-final_v2",
        "dataset_evaluated": {
            "test_split_path": os.path.abspath(os.path.join(dataset_dir, "rank_pairs_test.csv")),
            "test_rows": len(test_rank_df),
            "test_period": "2026-02-12 to 2026-06-30",
            "e2e_benchmark_cases": n_cases,
        },
        "ranking_offline_test_split": {
            "HitRate@1": raw_ranking_metrics.get("HitRate@1", 0.0),
            "HitRate@5": raw_ranking_metrics.get("HitRate@5", 0.0),
            "HitRate@10": raw_ranking_metrics.get("HitRate@10", 0.0),
            "NDCG@5": raw_ranking_metrics.get("NDCG@5", 0.0),
            "NDCG@10": raw_ranking_metrics.get("NDCG@10", 0.0),
            "MRR": raw_ranking_metrics.get("MRR", 0.0),
        },
        "calibration_metrics": calibration_metrics,
        "time_prediction_metrics": time_metrics,
        "anomaly_metrics": anom_metrics,
        "dynamic_retrieval_metrics": {
            "Recall@50": retrieval_stats["recall_at_50"] / n_cases,
            "Recall@100": retrieval_stats["recall_at_100"] / n_cases,
            "Recall@200": retrieval_stats["recall_at_200"] / n_cases,
            "Recall@300": retrieval_stats["recall_at_300"] / n_cases,
            "union_recall": retrieval_stats["union_recall"] / n_cases,
            "missed_retrieval_count": retrieval_stats["missed_count"],
            "total_evaluated": n_cases,
        },
        "geographic_accuracy_km": {
            "median_error_km": float(np.median(geo_errors_km)) if geo_errors_km else 0.0,
            "p90_error_km": float(np.percentile(geo_errors_km, 90)) if geo_errors_km else 0.0,
            "mean_error_km": float(np.mean(geo_errors_km)) if geo_errors_km else 0.0,
        },
        "operational_latencies_ms": {
            "retrieval_latency_p50": float(np.percentile(latencies["retrieval_ms"], 50)),
            "retrieval_latency_p95": float(np.percentile(latencies["retrieval_ms"], 95)),
            "feature_latency_p50": float(np.percentile(latencies["features_ms"], 50)),
            "feature_latency_p95": float(np.percentile(latencies["features_ms"], 95)),
            "inference_latency_p50": float(np.percentile(latencies["inference_ms"], 50)),
            "inference_latency_p95": float(np.percentile(latencies["inference_ms"], 95)),
            "total_e2e_p50": float(np.percentile(latencies["total_ms"], 50)),
            "total_e2e_p95": float(np.percentile(latencies["total_ms"], 95)),
        },
        "e2e_benchmark_live_rankings": {
            "cipher_ml_v4": {
                "HitRate@1": cipher_hits["hit_1"] / n_cases,
                "HitRate@5": cipher_hits["hit_5"] / n_cases,
                "HitRate@10": cipher_hits["hit_10"] / n_cases,
                "NDCG@5": float(np.mean(cipher_hits["ndcg_5"])),
                "NDCG@10": float(np.mean(cipher_hits["ndcg_10"])),
                "MRR": float(np.mean(cipher_hits["rr"])),
            },
            "baseline_nearest_atm": {
                "HitRate@1": nearest_hits["hit_1"] / n_cases,
                "HitRate@5": nearest_hits["hit_5"] / n_cases,
                "HitRate@10": nearest_hits["hit_10"] / n_cases,
            },
            "baseline_pure_hotspot": {
                "HitRate@1": hotspot_hits["hit_1"] / n_cases,
                "HitRate@5": hotspot_hits["hit_5"] / n_cases,
                "HitRate@10": hotspot_hits["hit_10"] / n_cases,
            },
            "baseline_skyvar_sih2025": {
                "HitRate@1": skyvar_hits["hit_1"] / n_cases,
                "HitRate@5": skyvar_hits["hit_5"] / n_cases,
                "HitRate@10": skyvar_hits["hit_10"] / n_cases,
            },
        },
    }

    # Save to models/final_v2/
    with open(os.path.join(model_dir, "test_evaluation_results.json"), "w") as f:
        json.dump(final_report, f, indent=2)

    print("\n" + "=" * 80)
    print("EVALUATION RESULTS SUMMARY:")
    print(f"  - Test Ranking Split (1.97M rows) NDCG@10: {final_report['ranking_offline_test_split']['NDCG@10']:.4f}")
    print(f"  - Test Calibration Brier Score:            {brier:.6f} | Log Loss: {ll:.4f} | ECE: {ece:.4f}")
    print(f"  - Dynamic Candidate Union Recall:         {final_report['dynamic_retrieval_metrics']['union_recall']*100:.2f}%")
    print(f"  - Dynamic E2E Top-10 Hit Rate:             {final_report['e2e_benchmark_live_rankings']['cipher_ml_v4']['HitRate@10']*100:.2f}%")
    print(f"  - Median Geographic Error:                 {final_report['geographic_accuracy_km']['median_error_km']:.2f} km")
    print(f"  - Total E2E Latency P50 / P95:             {final_report['operational_latencies_ms']['total_e2e_p50']:.2f} ms / {final_report['operational_latencies_ms']['total_e2e_p95']:.2f} ms")
    print("=" * 80)

    return final_report


if __name__ == "__main__":
    run_evaluation()

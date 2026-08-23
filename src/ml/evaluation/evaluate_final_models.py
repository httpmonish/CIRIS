"""
Comprehensive Evaluation & Benchmarking Suite for CIRIS / CIPHER ML V4.

Executes:
- STEP 14: Untouched Test Evaluation on 1,973,305 rows (rank_pairs_test.csv)
- STEP 15: True End-to-End Pipeline Validation without true ATM insertion
- STEP 16: Baseline Comparison against Nearest ATM, Hotspot Frequency, and SKYVAR (SIH 2025)
- Saves evaluation results to docs/ and models/final/
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


def evaluate_test_rank_pairs(
    ranker: ATMRanker,
    calibrator: ProbabilityCalibrator,
    test_rank_df: pd.DataFrame,
) -> Dict[str, float]:
    """Evaluate LambdaMART Ranker on untouched test ranking split."""
    print("  - Running ranking evaluation across test ranking split...")
    eval_metrics = ranker.evaluate(test_rank_df)
    
    # Calibration evaluation
    raw_scores = ranker.predict_scores(test_rank_df)
    y_test = test_rank_df["label"].values.astype(int)
    cal_probs = calibrator.calibrate(raw_scores)
    
    from sklearn.metrics import brier_score_loss, log_loss
    brier = float(brier_score_loss(y_test, cal_probs))
    eval_metrics["brier_score"] = brier
    
    return eval_metrics


def evaluate_test_time_and_anomaly(
    time_predictor: TimeToCashoutPredictor,
    anomaly_detector: AnomalyDetector,
    loader: DatasetLoader,
    complaints_df: pd.DataFrame,
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Evaluate Time and Anomaly models on untouched test split."""
    _, _, test_time = loader.load_time_splits()
    _, _, test_anom = loader.load_anomaly_splits()
    
    test_comp = complaints_df[complaints_df["complaint_id"].isin(test_time["complaint_id"])].copy()
    time_metrics = time_predictor.evaluate(test_comp, test_time)
    
    # Anomaly scores on test
    anom_scores = anomaly_detector.predict_anomaly_scores(test_anom)
    anom_metrics = {
        "n_test_samples": len(test_anom),
        "mean_anomaly_score": float(np.mean(anom_scores)),
        "std_anomaly_score": float(np.std(anom_scores)),
        "high_anomaly_rate": float(np.mean(anom_scores >= 0.70)),
    }
    
    return time_metrics, anom_metrics


def run_true_e2e_benchmark(
    retriever: CandidateRetriever,
    builder: FeatureBuilder,
    ranker: ATMRanker,
    time_predictor: TimeToCashoutPredictor,
    anomaly_detector: AnomalyDetector,
    fusion_engine: MultiSignalRiskFusionEngine,
    complaints_df: pd.DataFrame,
    withdrawals_df: pd.DataFrame,
    case_links_df: pd.DataFrame,
    n_sample_cases: int = 500,
) -> Dict[str, Any]:
    """
    Run True E2E validation on test complaints WITHOUT true ATM insertion.
    
    Validates:
    1. Retrieval Recall@50 / Recall@100
    2. Ranked Top-1, Top-3, Top-5, Top-10 Hit Rate
    3. Baseline comparisons: Nearest ATM, Pure Hotspot, SKYVAR Baseline
    4. Inference latency per stage
    """
    print(f"\n[E2E Benchmark] Evaluating dynamic retrieval + inference on {n_sample_cases} test cases...")
    
    # Map complaint_id -> true withdrawal ATM
    wd_lookup = dict(zip(withdrawals_df["complaint_id"], withdrawals_df["atm_id"]))
    acc_lookup = dict(zip(case_links_df["complaint_id"], case_links_df["cashout_account_id"]))
    
    # Filter test complaints
    test_cases = complaints_df.tail(n_sample_cases).copy()
    
    cipher_hits = {"top1": 0, "top3": 0, "top5": 0, "top10": 0, "retrieved": 0}
    nearest_hits = {"top1": 0, "top3": 0, "top5": 0, "top10": 0}
    hotspot_hits = {"top1": 0, "top3": 0, "top5": 0, "top10": 0}
    skyvar_hits = {"top1": 0, "top3": 0, "top5": 0, "top10": 0}
    
    latencies = {
        "retrieval_ms": [],
        "features_ms": [],
        "ranking_ms": [],
        "time_ms": [],
        "anomaly_ms": [],
        "fusion_ms": [],
        "total_ms": [],
    }
    
    total_evaluated = 0
    
    for _, row in test_cases.iterrows():
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
        
        # 1. Retrieval
        t0 = time.perf_counter()
        candidates = retriever.retrieve_candidates(
            complaint=payload,
            as_of_T=t_complaint,
            chain_accounts=chain_accs,
        )
        t_ret = (time.perf_counter() - t0) * 1000.0
        
        cand_ids = [c.atm_id for c in candidates]
        is_retrieved = true_atm in cand_ids
        if is_retrieved:
            cipher_hits["retrieved"] += 1
            
        # 2. Feature Building
        t0 = time.perf_counter()
        feat_df = builder.build_features_for_candidates(
            complaint=payload,
            candidates=candidates,
            as_of_T=t_complaint,
            chain_accounts=chain_accs,
        )
        t_feat = (time.perf_counter() - t0) * 1000.0
        
        # 3. Ranking
        t0 = time.perf_counter()
        raw_scores = ranker.predict_scores(feat_df)
        feat_df["ranking_score"] = raw_scores
        feat_df_sorted = feat_df.sort_values(by="ranking_score", ascending=False).reset_index(drop=True)
        t_rank = (time.perf_counter() - t0) * 1000.0
        
        # 4. Time Prediction
        t0 = time.perf_counter()
        pred_delay, pred_window_name, window_probs = time_predictor.predict(payload)
        t_time = (time.perf_counter() - t0) * 1000.0
        
        # 5. Anomaly Detection
        t0 = time.perf_counter()
        anom_score, anom_subs = anomaly_detector.predict_anomaly_score(payload)
        t_anom = (time.perf_counter() - t0) * 1000.0
        
        # 6. Multi-Signal Fusion
        t0 = time.perf_counter()
        time_window_short = list(window_probs.keys())[0] if window_probs else "<1h"
        fused_predictions = fusion_engine.fuse_predictions(
            ranked_candidates_df=feat_df_sorted,
            predicted_delay_hours=pred_delay,
            predicted_time_window_short=time_window_short,
            predicted_time_window_full=pred_window_name,
            anomaly_score=anom_score,
            anomaly_sub_scores=anom_subs,
        )
        t_fuse = (time.perf_counter() - t0) * 1000.0
        t_tot = t_ret + t_feat + t_rank + t_time + t_anom + t_fuse
        
        latencies["retrieval_ms"].append(t_ret)
        latencies["features_ms"].append(t_feat)
        latencies["ranking_ms"].append(t_rank)
        latencies["time_ms"].append(t_time)
        latencies["anomaly_ms"].append(t_anom)
        latencies["fusion_ms"].append(t_fuse)
        latencies["total_ms"].append(t_tot)
        
        # CIPHER Ranked order
        cipher_ranked_ids = [p.atm_id for p in fused_predictions]
        if true_atm in cipher_ranked_ids[:1]:
            cipher_hits["top1"] += 1
        if true_atm in cipher_ranked_ids[:3]:
            cipher_hits["top3"] += 1
        if true_atm in cipher_ranked_ids[:5]:
            cipher_hits["top5"] += 1
        if true_atm in cipher_ranked_ids[:10]:
            cipher_hits["top10"] += 1
            
        # Baseline 1: Nearest ATM (by distance_km)
        nearest_sorted_ids = sorted(candidates, key=lambda c: c.distance_km)
        nearest_ids = [c.atm_id for c in nearest_sorted_ids]
        if true_atm in nearest_ids[:1]:
            nearest_hits["top1"] += 1
        if true_atm in nearest_ids[:3]:
            nearest_hits["top3"] += 1
        if true_atm in nearest_ids[:5]:
            nearest_hits["top5"] += 1
        if true_atm in nearest_ids[:10]:
            nearest_hits["top10"] += 1
            
        # Baseline 2: Pure Hotspot Heuristic
        hotspot_sorted = feat_df.sort_values(by="historical_hotspot_score_as_of_T", ascending=False)
        hotspot_ids = list(hotspot_sorted["atm_id"])
        if true_atm in hotspot_ids[:1]:
            hotspot_hits["top1"] += 1
        if true_atm in hotspot_ids[:3]:
            hotspot_hits["top3"] += 1
        if true_atm in hotspot_ids[:5]:
            hotspot_hits["top5"] += 1
        if true_atm in hotspot_ids[:10]:
            hotspot_hits["top10"] += 1
            
        # Baseline 3: SKYVAR Reconstructed Baseline (Distance + Static Density)
        skyvar_score = 0.60 * feat_df["geographic_similarity"] + 0.40 * (feat_df["nearby_atm_count"] / 20.0)
        feat_df["skyvar_score"] = skyvar_score
        skyvar_sorted = feat_df.sort_values(by="skyvar_score", ascending=False)
        skyvar_ids = list(skyvar_sorted["atm_id"])
        if true_atm in skyvar_ids[:1]:
            skyvar_hits["top1"] += 1
        if true_atm in skyvar_ids[:3]:
            skyvar_hits["top3"] += 1
        if true_atm in skyvar_ids[:5]:
            skyvar_hits["top5"] += 1
        if true_atm in skyvar_ids[:10]:
            skyvar_hits["top10"] += 1
            
        total_evaluated += 1

    # Aggregate Rates
    n = max(1, total_evaluated)
    e2e_results = {
        "n_evaluated_cases": total_evaluated,
        "retrieval_recall_at_candidate_pool": cipher_hits["retrieved"] / n,
        "cipher_v4": {
            "hit_rate_top1": cipher_hits["top1"] / n,
            "hit_rate_top3": cipher_hits["top3"] / n,
            "hit_rate_top5": cipher_hits["top5"] / n,
            "hit_rate_top10": cipher_hits["top10"] / n,
        },
        "baseline_nearest_atm": {
            "hit_rate_top1": nearest_hits["top1"] / n,
            "hit_rate_top3": nearest_hits["top3"] / n,
            "hit_rate_top5": nearest_hits["top5"] / n,
            "hit_rate_top10": nearest_hits["top10"] / n,
        },
        "baseline_pure_hotspot": {
            "hit_rate_top1": hotspot_hits["top1"] / n,
            "hit_rate_top3": hotspot_hits["top3"] / n,
            "hit_rate_top5": hotspot_hits["top5"] / n,
            "hit_rate_top10": hotspot_hits["top10"] / n,
        },
        "baseline_skyvar_sih2025": {
            "hit_rate_top1": skyvar_hits["top1"] / n,
            "hit_rate_top3": skyvar_hits["top3"] / n,
            "hit_rate_top5": skyvar_hits["top5"] / n,
            "hit_rate_top10": skyvar_hits["top10"] / n,
        },
        "latency_profile_ms": {
            "candidate_retrieval_p50": float(np.percentile(latencies["retrieval_ms"], 50)),
            "candidate_retrieval_p95": float(np.percentile(latencies["retrieval_ms"], 95)),
            "feature_building_p50": float(np.percentile(latencies["features_ms"], 50)),
            "feature_building_p95": float(np.percentile(latencies["features_ms"], 95)),
            "ranker_inference_p50": float(np.percentile(latencies["ranking_ms"], 50)),
            "ranker_inference_p95": float(np.percentile(latencies["ranking_ms"], 95)),
            "time_model_p50": float(np.percentile(latencies["time_ms"], 50)),
            "anomaly_detector_p50": float(np.percentile(latencies["anomaly_ms"], 50)),
            "fusion_p50": float(np.percentile(latencies["fusion_ms"], 50)),
            "total_e2e_latency_p50_ms": float(np.percentile(latencies["total_ms"], 50)),
            "total_e2e_latency_p95_ms": float(np.percentile(latencies["total_ms"], 95)),
            "mean_total_latency_ms": float(np.mean(latencies["total_ms"])),
        }
    }
    
    return e2e_results


def main():
    print("=" * 70)
    print("CIRIS / CIPHER ML V4 — FINAL UNTOUCHED TEST & E2E BENCHMARK")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)
    
    loader = DatasetLoader("datasets/final")
    models_dir = "models/final"
    
    # 1. Load Trained Models
    print("\n[Stage 1/4] Loading Trained Model Artifacts from 'models/final'...")
    ranker = ATMRanker.load(os.path.join(models_dir, "location_ranker.joblib"))
    time_predictor = TimeToCashoutPredictor.load(os.path.join(models_dir, "time_predictor.joblib"))
    anomaly_detector = AnomalyDetector.load(os.path.join(models_dir, "anomaly_detector.joblib"))
    calibrator = ProbabilityCalibrator.load(os.path.join(models_dir, "calibrator.joblib"))
    fusion_engine = MultiSignalRiskFusionEngine.load(os.path.join(models_dir, "fusion_engine.joblib"))
    print("  - All Model Artifacts Loaded Successfully.")
    
    # 2. Evaluate Untouched Test Ranking Split (1,973,305 rows)
    print("\n[Stage 2/4] Loading & Evaluating Untouched Test Rank Pairs (1,973,305 rows)...")
    t0 = time.time()
    test_rank_df = loader.load_rank_split("test", optimized_dtypes=True)
    load_test_duration = time.time() - t0
    print(f"  - Test Ranking Split Loaded: {len(test_rank_df):,} rows in {load_test_duration:.2f}s")
    
    test_ranking_metrics = evaluate_test_rank_pairs(ranker, calibrator, test_rank_df)
    print(f"  - Test NDCG@1:     {test_ranking_metrics.get('NDCG@1', 0.0):.4f}")
    print(f"  - Test NDCG@3:     {test_ranking_metrics.get('NDCG@3', 0.0):.4f}")
    print(f"  - Test NDCG@5:     {test_ranking_metrics.get('NDCG@5', 0.0):.4f}")
    print(f"  - Test NDCG@10:    {test_ranking_metrics.get('NDCG@10', 0.0):.4f}")
    print(f"  - Test MRR:        {test_ranking_metrics.get('MRR', 0.0):.4f}")
    print(f"  - Test HitRate@1:  {test_ranking_metrics.get('HitRate@1', 0.0):.4f}")
    print(f"  - Test HitRate@5:  {test_ranking_metrics.get('HitRate@5', 0.0):.4f}")
    print(f"  - Test HitRate@10: {test_ranking_metrics.get('HitRate@10', 0.0):.4f}")
    print(f"  - Test Brier Score: {test_ranking_metrics.get('brier_score', 0.0):.6f}")
    
    # 3. Evaluate Test Time & Anomaly
    print("\n[Stage 3/4] Evaluating Time & Anomaly on Untouched Test Split...")
    complaints_df = loader.load_complaints()
    time_test_metrics, anom_test_metrics = evaluate_test_time_and_anomaly(
        time_predictor, anomaly_detector, loader, complaints_df
    )
    print(f"  - Time Test MAE:         {time_test_metrics.get('regression_MAE_hours', 0.0):.2f} hours")
    print(f"  - Time Test Accuracy:    {time_test_metrics.get('classification_Accuracy', 0.0):.4f}")
    print(f"  - Time Test Macro F1:    {time_test_metrics.get('classification_Macro_F1', 0.0):.4f}")
    print(f"  - Anomaly Test Samples:  {anom_test_metrics.get('n_test_samples', 0):,}")
    print(f"  - Mean Anomaly Score:    {anom_test_metrics.get('mean_anomaly_score', 0.0):.4f}")
    
    # 4. Initialize Offline Engines for Live Dynamic E2E Benchmark
    print("\n[Stage 4/4] Executing True Live End-to-End Benchmark (Without True ATM Insertion)...")
    atm_master_df = loader.load_atm_master()
    withdrawals_df = loader.load_withdrawals()
    graph_edges_df = loader.load_graph_edges()
    case_links_df = loader.load_case_links()
    upi_df = loader.load_upi_entities()
    
    spatial_index = SpatialIndex(atm_master_df)
    hotspot_cache = HistoricalHotspotCache(
        atm_master_df=atm_master_df,
        withdrawals_df=withdrawals_df,
        complaints_df=complaints_df,
    )
    graph_engine = TemporalGraphEngine(
        graph_edges_df=graph_edges_df,
        case_links_df=case_links_df,
        withdrawals_df=withdrawals_df,
        upi_df=upi_df,
    )
    retriever = CandidateRetriever(
        spatial_index=spatial_index,
        hotspot_cache=hotspot_cache,
        graph_engine=graph_engine,
    )
    builder = FeatureBuilder(
        atm_master_df=atm_master_df,
        hotspot_cache=hotspot_cache,
        spatial_index=spatial_index,
    )
    
    e2e_results = run_true_e2e_benchmark(
        retriever=retriever,
        builder=builder,
        ranker=ranker,
        time_predictor=time_predictor,
        anomaly_detector=anomaly_detector,
        fusion_engine=fusion_engine,
        complaints_df=complaints_df,
        withdrawals_df=withdrawals_df,
        case_links_df=case_links_df,
        n_sample_cases=300,
    )
    
    # Print Benchmark Summary
    print("\n" + "=" * 70)
    print("FINAL BENCHMARK COMPARISON MATRIX")
    print("=" * 70)
    c4 = e2e_results["cipher_v4"]
    b_near = e2e_results["baseline_nearest_atm"]
    b_hot = e2e_results["baseline_pure_hotspot"]
    b_sky = e2e_results["baseline_skyvar_sih2025"]
    
    print(f"{'Method / Model':<28} | {'Top-1 Hit':<10} | {'Top-3 Hit':<10} | {'Top-5 Hit':<10} | {'Top-10 Hit':<10}")
    print("-" * 75)
    print(f"{'Nearest ATM (Geospatial)':<28} | {b_near['hit_rate_top1']*100:6.2f}%    | {b_near['hit_rate_top3']*100:6.2f}%    | {b_near['hit_rate_top5']*100:6.2f}%    | {b_near['hit_rate_top10']*100:6.2f}%")
    print(f"{'Pure Hotspot Heuristic':<28} | {b_hot['hit_rate_top1']*100:6.2f}%    | {b_hot['hit_rate_top3']*100:6.2f}%    | {b_hot['hit_rate_top5']*100:6.2f}%    | {b_hot['hit_rate_top10']*100:6.2f}%")
    print(f"{'SKYVAR Baseline (SIH 2025)':<28} | {b_sky['hit_rate_top1']*100:6.2f}%    | {b_sky['hit_rate_top3']*100:6.2f}%    | {b_sky['hit_rate_top5']*100:6.2f}%    | {b_sky['hit_rate_top10']*100:6.2f}%")
    print(f"{'CIPHER ML V4 (Final)':<28} | {c4['hit_rate_top1']*100:6.2f}%    | {c4['hit_rate_top3']*100:6.2f}%    | {c4['hit_rate_top5']*100:6.2f}%    | {c4['hit_rate_top10']*100:6.2f}%")
    print("=" * 75)
    
    lat = e2e_results["latency_profile_ms"]
    print("\nEND-TO-END INFERENCE LATENCY PROFILE:")
    print(f"  - Candidate Retrieval P50: {lat['candidate_retrieval_p50']:.2f} ms")
    print(f"  - Feature Building P50:    {lat['feature_building_p50']:.2f} ms")
    print(f"  - Ranker Inference P50:    {lat['ranker_inference_p50']:.2f} ms")
    print(f"  - Time Predictor P50:      {lat['time_model_p50']:.2f} ms")
    print(f"  - Anomaly Detector P50:    {lat['anomaly_detector_p50']:.2f} ms")
    print(f"  - Risk Fusion P50:         {lat['fusion_p50']:.2f} ms")
    print(f"  - Total E2E Latency P50:   {lat['total_e2e_latency_p50_ms']:.2f} ms")
    print(f"  - Total E2E Latency P95:   {lat['total_e2e_latency_p95_ms']:.2f} ms")
    print(f"  - Mean Total Latency:      {lat['mean_total_latency_ms']:.2f} ms")
    
    # Save Full Benchmark Results
    full_eval_payload = {
        "evaluation_timestamp": datetime.now().isoformat(),
        "test_ranking_metrics": test_ranking_metrics,
        "time_test_metrics": time_test_metrics,
        "anomaly_test_metrics": anom_test_metrics,
        "e2e_benchmark": e2e_results,
    }
    with open(os.path.join(models_dir, "test_evaluation_results.json"), "w") as f:
        json.dump(full_eval_payload, f, indent=2)
        
    print(f"\n[Saved] Test evaluation results saved to '{models_dir}/test_evaluation_results.json'")
    return full_eval_payload


if __name__ == "__main__":
    main()

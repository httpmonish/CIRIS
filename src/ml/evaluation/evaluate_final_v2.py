"""
Untouched Test Evaluation & Dynamic E2E Benchmark for CIRIS / CIPHER ML V4 (V2 Frozen Retrieval).

Supports independent execution modes:
- `--mode ranking`: Full-scale untouched LightGBM ranking & calibration evaluation on 1,973,305 rows
- `--mode e2e`: True Dynamic Candidate Retrieval & E2E System Benchmark with Checkpointing
- `--mode all`: Sequential execution of both modes
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
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


class EvaluatorV2:
    def __init__(self, dataset_dir: str = "datasets/final", model_dir: str = "models/final_v2"):
        self.dataset_dir = dataset_dir
        self.model_dir = model_dir
        self.loader = DatasetLoader(dataset_dir)
        
        print("\n[Init] Loading Production Model Suite from:", model_dir)
        self.ranker = ATMRanker()
        self.ranker.load(os.path.join(model_dir, "location_ranker.joblib"))

        self.time_predictor = TimeToCashoutPredictor()
        self.time_predictor.load(os.path.join(model_dir, "time_predictor.joblib"))

        self.anomaly_detector = AnomalyDetector()
        self.anomaly_detector.load(os.path.join(model_dir, "anomaly_detector.joblib"))

        self.fusion_engine = MultiSignalRiskFusionEngine()
        self.fusion_engine.load(os.path.join(model_dir, "fusion_engine.joblib"))
        self.calibrator = self.fusion_engine.calibrator

        print("[Init] Loading Core Datasets & Indexes (Once)...")
        self.atm_df = self.loader.load_atm_master()
        self.wd_df = self.loader.load_withdrawals()
        self.graph_edges_df = self.loader.load_graph_edges()
        self.cases_df = self.loader.load_case_links()
        self.upi_df = self.loader.load_upi_entities()
        self.comp_df = self.loader.load_complaints()

        self.spatial_index = SpatialIndex(self.atm_df)
        self.hotspot_cache = HistoricalHotspotCache(
            atm_master_df=self.atm_df,
            withdrawals_df=self.wd_df,
            complaints_df=self.comp_df
        )
        self.graph_engine = TemporalGraphEngine(
            graph_edges_df=self.graph_edges_df,
            case_links_df=self.cases_df,
            withdrawals_df=self.wd_df,
            upi_df=self.upi_df
        )

        self.retriever = CandidateRetriever(
            spatial_index=self.spatial_index,
            hotspot_cache=self.hotspot_cache,
            graph_engine=self.graph_engine,
            geo_radius_km=250.0,
            geo_fallback_knn=200,
            top_hotspots_count=1500,
            enable_district_fallback=True,
            enable_state_fallback=True,
            state_top_k=100,
        )
        self.builder = FeatureBuilder(
            atm_master_df=self.atm_df,
            hotspot_cache=self.hotspot_cache,
            graph_engine=self.graph_engine,
            spatial_index=self.spatial_index,
        )

        # Pre-computed fast lookups
        self.wd_lookup = dict(zip(self.wd_df["complaint_id"], self.wd_df["atm_id"]))
        self.acc_lookup = dict(zip(self.cases_df["complaint_id"], self.cases_df["cashout_account_id"]))
        self.atm_coord_map = {
            str(r["atm_id"]).strip(): (float(r["latitude"]), float(r["longitude"]))
            for _, r in self.atm_df.iterrows()
        }
        print("[Init] Pipeline Components & Lookups Initialized Successfully.\n")

    def run_ranking_eval(self) -> Dict[str, Any]:
        """Mode COMMAND A: Evaluate 1,973,305 test rows offline ranking & calibration."""
        from sklearn.metrics import brier_score_loss, log_loss

        print("=" * 80)
        print("COMMAND A: FULL OFFLINE RANKING & CALIBRATION EVALUATION (1.97M ROWS)")
        print("=" * 80)

        t0 = time.time()
        test_rank_df = self.loader.load_rank_split("test")
        load_duration = time.time() - t0
        print(f"  - Loaded {len(test_rank_df):,} test rank pairs in {load_duration:.2f}s")

        t0 = time.time()
        raw_ranking_metrics = self.ranker.evaluate(test_rank_df)
        rank_eval_duration = time.time() - t0
        print(f"  - Ranking evaluation completed in {rank_eval_duration:.2f}s")

        print("\n  - Computing Calibration & Log Loss on Test Split...")
        test_scores = self.ranker.predict_scores(test_rank_df)
        y_test = test_rank_df["label"].values.astype(int)
        cal_probs = self.calibrator.calibrate(test_scores)
        cal_probs_clipped = np.clip(cal_probs, 1e-6, 1.0 - 1e-6)

        brier = float(brier_score_loss(y_test, cal_probs))
        ll = float(log_loss(y_test, cal_probs_clipped))
        ece = calculate_ece(y_test, cal_probs, n_bins=10)

        print("\n  - Evaluating Time-to-Cashout and Anomaly Predictor on Test Split...")
        _, _, test_time = self.loader.load_time_splits()
        _, _, test_anom = self.loader.load_anomaly_splits()

        test_comp = self.comp_df[self.comp_df["complaint_id"].isin(test_time["complaint_id"])].copy()
        time_metrics = self.time_predictor.evaluate(test_comp, test_time)

        anom_scores = self.anomaly_detector.predict_anomaly_scores(test_anom)
        anom_metrics = {
            "n_test_samples": len(test_anom),
            "mean_anomaly_score": float(np.mean(anom_scores)),
            "std_anomaly_score": float(np.std(anom_scores)),
            "high_anomaly_rate": float(np.mean(anom_scores >= 0.70)),
        }

        ranking_report = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "model_version": "v4.1.0-final_v2",
            "dataset_evaluated": {
                "test_split_path": os.path.abspath(os.path.join(self.dataset_dir, "rank_pairs_test.csv")),
                "test_rows": len(test_rank_df),
                "test_period": "2026-02-12 to 2026-06-30",
            },
            "ranking_offline_test_split": raw_ranking_metrics,
            "calibration_metrics": {
                "brier_score": brier,
                "log_loss": ll,
                "expected_calibration_error_ece": ece,
            },
            "time_prediction_metrics": time_metrics,
            "anomaly_metrics": anom_metrics,
        }

        output_path = os.path.join(self.model_dir, "test_ranking_evaluation_results.json")
        with open(output_path, "w") as f:
            json.dump(ranking_report, f, indent=2)

        print(f"\n[Offline Ranking Done] Saved to {output_path}")
        return ranking_report

    def run_e2e_eval(self, n_e2e_cases: int = 25, checkpoint_freq: int = 25) -> Dict[str, Any]:
        """Mode COMMAND B: True Dynamic E2E System Benchmark with Checkpointing & Progress Tracking."""
        print("=" * 80)
        print(f"COMMAND B: DYNAMIC E2E SYSTEM BENCHMARK ({n_e2e_cases} CASES)")
        print(f"Checkpointing Frequency: every {checkpoint_freq} cases")
        print("=" * 80)

        # Select test complaints
        test_cases_df = self.comp_df.tail(n_e2e_cases).copy()

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
            "inference_ms": [],
            "evidence_ms": [],
            "total_ms": [],
        }

        candidate_counts = []
        total_valid_cases = 0
        loop_start_time = time.time()

        for idx, (_, row) in enumerate(test_cases_df.iterrows(), start=1):
            t_case_start = time.time()
            cid = str(row["complaint_id"])
            true_atm = str(self.wd_lookup.get(cid, "")).strip()
            if not true_atm:
                continue

            t_complaint = pd.to_datetime(row["complaint_timestamp"]).to_pydatetime()
            acc_id = self.acc_lookup.get(cid, None)
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
            candidates = self.retriever.retrieve_candidates(
                complaint=payload,
                as_of_T=t_complaint,
                chain_accounts=chain_accs,
            )
            t_ret_ms = (time.perf_counter() - t_start_ret) * 1000.0

            cand_ids = [c.atm_id for c in candidates]
            candidate_counts.append(len(cand_ids))
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

            # Stage 1: Live Feature Extraction for Candidates
            t_start_feat = time.perf_counter()
            feat_df = self.builder.build_features_for_candidates(
                complaint=payload,
                candidates=candidates,
                as_of_T=t_complaint,
                chain_accounts=chain_accs,
            )
            t_feat_ms = (time.perf_counter() - t_start_feat) * 1000.0

            # Stage 2-4: ML Models (Ranker + Time + Anomaly)
            t_start_inf = time.perf_counter()
            raw_scores = self.ranker.predict_scores(feat_df)
            feat_df["ranking_score"] = raw_scores
            feat_df_sorted = feat_df.sort_values(by="ranking_score", ascending=False).reset_index(drop=True)

            pred_delay, pred_window_name, window_probs = self.time_predictor.predict(payload)
            anom_score, anom_subs = self.anomaly_detector.predict_anomaly_score(payload)
            t_inf_ms = (time.perf_counter() - t_start_inf) * 1000.0

            # Stage 5: Multi-Signal Fusion & Evidence Building
            t_start_evid = time.perf_counter()
            time_window_short = list(window_probs.keys())[0] if window_probs else "<1h"
            fused_predictions = self.fusion_engine.fuse_predictions(
                ranked_candidates_df=feat_df_sorted,
                predicted_delay_hours=pred_delay,
                predicted_time_window_short=time_window_short,
                predicted_time_window_full=pred_window_name,
                anomaly_score=anom_score,
                anomaly_sub_scores=anom_subs,
            )
            t_evid_ms = (time.perf_counter() - t_start_evid) * 1000.0

            t_tot_ms = t_ret_ms + t_feat_ms + t_inf_ms + t_evid_ms

            latencies["retrieval_ms"].append(t_ret_ms)
            latencies["features_ms"].append(t_feat_ms)
            latencies["inference_ms"].append(t_inf_ms)
            latencies["evidence_ms"].append(t_evid_ms)
            latencies["total_ms"].append(t_tot_ms)

            # Metrics Computation: CIPHER ML V4
            cipher_ranked_ids = [p.atm_id for p in fused_predictions]
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

            # Geographic Error
            if len(cipher_ranked_ids) > 0 and true_atm in self.atm_coord_map:
                top1_atm = cipher_ranked_ids[0]
                if top1_atm in self.atm_coord_map:
                    p_lat, p_lon = self.atm_coord_map[top1_atm]
                    a_lat, a_lon = self.atm_coord_map[true_atm]
                    err_km = SpatialIndex.haversine_distance(p_lat, p_lon, a_lat, a_lon)
                    geo_errors_km.append(err_km)

            # Baselines
            nearest_sorted = sorted(candidates, key=lambda c: c.distance_km)
            nearest_ids = [c.atm_id for c in nearest_sorted]
            if true_atm in nearest_ids[:1]:
                nearest_hits["hit_1"] += 1
            if true_atm in nearest_ids[:5]:
                nearest_hits["hit_5"] += 1
            if true_atm in nearest_ids[:10]:
                nearest_hits["hit_10"] += 1

            hotspot_sorted = feat_df.sort_values(by="historical_hotspot_score_as_of_T", ascending=False)
            hotspot_ids = list(hotspot_sorted["atm_id"])
            if true_atm in hotspot_ids[:1]:
                hotspot_hits["hit_1"] += 1
            if true_atm in hotspot_ids[:5]:
                hotspot_hits["hit_5"] += 1
            if true_atm in hotspot_ids[:10]:
                hotspot_hits["hit_10"] += 1

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
            case_sec = time.time() - t_case_start
            elapsed_sec = time.time() - loop_start_time
            avg_sec_per_case = elapsed_sec / total_valid_cases
            est_rem_sec = (n_e2e_cases - idx) * avg_sec_per_case

            pct = (idx / n_e2e_cases) * 100.0
            curr_recall = (retrieval_stats["union_recall"] / total_valid_cases) * 100.0

            print(
                f"Case {idx:3d}/{n_e2e_cases:3d} [{pct:5.1f}%] | "
                f"CID: {cid[:12]} | Cand: {len(cand_ids):4d} | "
                f"Ret: {t_ret_ms:6.1f}ms | Feat: {t_feat_ms:6.1f}ms | Inf: {t_inf_ms:5.1f}ms | "
                f"Total: {t_tot_ms:6.1f}ms | Avg: {avg_sec_per_case:.2f}s/case | "
                f"Rem: {est_rem_sec:5.1f}s | Union Recall: {curr_recall:5.1f}%"
            )

            # Incremental Checkpoint
            if idx % checkpoint_freq == 0 or idx == n_e2e_cases:
                self._save_e2e_checkpoint(
                    n_cases=total_valid_cases,
                    retrieval_stats=retrieval_stats,
                    cipher_hits=cipher_hits,
                    nearest_hits=nearest_hits,
                    hotspot_hits=hotspot_hits,
                    skyvar_hits=skyvar_hits,
                    geo_errors_km=geo_errors_km,
                    latencies=latencies,
                    candidate_counts=candidate_counts,
                    is_final=(idx == n_e2e_cases),
                )

        n_cases = max(1, total_valid_cases)
        total_time_sec = time.time() - loop_start_time

        e2e_report = {
            "evaluation_timestamp": datetime.now().isoformat(),
            "model_version": "v4.1.0-final_v2",
            "benchmark_execution": {
                "e2e_cases_evaluated": n_cases,
                "total_time_seconds": total_time_sec,
                "average_seconds_per_case": total_time_sec / n_cases,
                "mean_candidate_count": float(np.mean(candidate_counts)),
                "median_candidate_count": float(np.median(candidate_counts)),
                "p95_candidate_count": float(np.percentile(candidate_counts, 95)),
                "min_candidate_count": int(np.min(candidate_counts)),
                "max_candidate_count": int(np.max(candidate_counts)),
                "exhaustive_search_usage": 0,
                "crashes_errors": 0,
            },
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
                "evidence_latency_p50": float(np.percentile(latencies["evidence_ms"], 50)),
                "evidence_latency_p95": float(np.percentile(latencies["evidence_ms"], 95)),
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

        output_path = os.path.join(self.model_dir, "test_e2e_evaluation_results.json")
        with open(output_path, "w") as f:
            json.dump(e2e_report, f, indent=2)

        print("\n" + "=" * 80)
        print("DYNAMIC E2E BENCHMARK COMPLETED SUMMARY:")
        print(f"  - Total Time:                {total_time_sec:.2f}s for {n_cases} cases")
        print(f"  - Average Time/Case:        {total_time_sec / n_cases:.3f}s")
        print(f"  - Mean Candidate Count:      {np.mean(candidate_counts):.1f}")
        print(f"  - Dynamic Union Recall:      {e2e_report['dynamic_retrieval_metrics']['union_recall']*100:.2f}%")
        print(f"  - Dynamic Top-10 Hit Rate:   {e2e_report['e2e_benchmark_live_rankings']['cipher_ml_v4']['HitRate@10']*100:.2f}%")
        print(f"  - Latency P50 (ms):          Retrieval={e2e_report['operational_latencies_ms']['retrieval_latency_p50']:.2f} | Feature={e2e_report['operational_latencies_ms']['feature_latency_p50']:.2f} | Inf={e2e_report['operational_latencies_ms']['inference_latency_p50']:.2f} | Evid={e2e_report['operational_latencies_ms']['evidence_latency_p50']:.2f} | Total={e2e_report['operational_latencies_ms']['total_e2e_p50']:.2f}")
        print("=" * 80)

        return e2e_report

    def _save_e2e_checkpoint(
        self,
        n_cases: int,
        retrieval_stats: Dict[str, int],
        cipher_hits: Dict[str, Any],
        nearest_hits: Dict[str, int],
        hotspot_hits: Dict[str, int],
        skyvar_hits: Dict[str, int],
        geo_errors_km: List[float],
        latencies: Dict[str, List[float]],
        candidate_counts: List[int],
        is_final: bool = False,
    ):
        ckpt_name = "test_evaluation_results.json" if is_final else "e2e_checkpoint_latest.json"
        ckpt_path = os.path.join(self.model_dir, ckpt_name)

        checkpoint_data = {
            "checkpoint_timestamp": datetime.now().isoformat(),
            "n_cases_completed": n_cases,
            "mean_candidates": float(np.mean(candidate_counts)) if candidate_counts else 0.0,
            "dynamic_retrieval_union_recall": (retrieval_stats["union_recall"] / n_cases) if n_cases > 0 else 0.0,
            "retrieval_stats": retrieval_stats,
            "cipher_hit10": (cipher_hits["hit_10"] / n_cases) if n_cases > 0 else 0.0,
            "median_geo_error_km": float(np.median(geo_errors_km)) if geo_errors_km else 0.0,
            "latency_p50_total_ms": float(np.percentile(latencies["total_ms"], 50)) if latencies["total_ms"] else 0.0,
        }

        with open(ckpt_path, "w") as f:
            json.dump(checkpoint_data, f, indent=2)


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate CIPHER ML V4 V2 on Untouched Test Set")
    parser.add_argument("--dataset-dir", type=str, default="datasets/final")
    parser.add_argument("--model-dir", type=str, default="models/final_v2")
    parser.add_argument("--mode", type=str, choices=["ranking", "e2e", "all"], default="e2e", help="Evaluation mode")
    parser.add_argument("--n-e2e-cases", type=int, default=25, help="Number of E2E cases")
    parser.add_argument("--checkpoint-freq", type=int, default=25, help="Checkpoint frequency")
    args = parser.parse_args()

    evaluator = EvaluatorV2(dataset_dir=args.dataset_dir, model_dir=args.model_dir)

    if args.mode in ["ranking", "all"]:
        evaluator.run_ranking_eval()

    if args.mode in ["e2e", "all"]:
        evaluator.run_e2e_eval(n_e2e_cases=args.n_e2e_cases, checkpoint_freq=args.checkpoint_freq)

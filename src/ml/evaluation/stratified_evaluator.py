"""
Stratified Evaluator for CIRIS ML V4 & Baseline Performance.

Evaluates E2E Candidate Retrieval and Ranking across 6 distinct strata:
1. Local Cashouts (Same district)
2. Cross-District Cashouts (Same state, different district)
3. Cross-State Cashouts (Different state)
4. Cold ATMs (<=2 prior complaints)
5. High Network/Graph Evidence (Chain accounts connected in graph)
6. Low/No Network Evidence (Isolated complaints)
"""

import os
import sys
sys.path.insert(0, ".")
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

from src.ml.data.loader import DatasetLoader
from src.ml.models.ranker import ATMRanker
from src.ml.models.time_predictor import TimeToCashoutPredictor
from src.ml.models.anomaly_detector import AnomalyDetector
from src.ml.models.fusion import MultiSignalRiskFusionEngine
from src.ml.features.feature_builder import FeatureBuilder
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.candidate_retriever import CandidateRetriever
from src.ml.contracts.schemas import ComplaintPayload, VictimLocation


class StratifiedEvaluator:
    def __init__(self, dataset_dir: str = "datasets/final", model_dir: str = "models/final_v2"):
        self.dataset_dir = dataset_dir
        self.model_dir = model_dir
        self.loader = DatasetLoader(dataset_dir)

        print("\n[StratifiedEvaluator] Loading Models & Datasets...")
        self.ranker = ATMRanker()
        self.ranker.load(os.path.join(model_dir, "location_ranker.joblib"))

        self.time_predictor = TimeToCashoutPredictor()
        self.time_predictor.load(os.path.join(model_dir, "time_predictor.joblib"))

        self.anomaly_detector = AnomalyDetector()
        self.anomaly_detector.load(os.path.join(model_dir, "anomaly_detector.joblib"))

        self.fusion_engine = MultiSignalRiskFusionEngine()
        self.fusion_engine.load(os.path.join(model_dir, "fusion_engine.joblib"))

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

        self.wd_lookup = dict(zip(self.wd_df["complaint_id"], self.wd_df["atm_id"]))
        self.acc_lookup = dict(zip(self.cases_df["complaint_id"], self.cases_df["cashout_account_id"]))

        # Build ATM lookup metadata
        self.atm_meta = {}
        for _, r in self.atm_df.iterrows():
            aid = str(r["atm_id"]).strip()
            self.atm_meta[aid] = {
                "state": str(r.get("state", "")).strip().lower(),
                "district": str(r.get("district", "")).strip().lower(),
            }

        # Count historical ATM complaints
        self.atm_counts = self.wd_df["atm_id"].value_counts().to_dict()

    def build_stratified_samples(self, target_per_stratum: int = 20) -> Dict[str, pd.DataFrame]:
        """
        Sample complaints across 6 distinct strata from holdout test split.
        """
        # Test split complaints (last 15,000 complaints)
        test_df = self.comp_df.tail(15000).copy()

        strata_samples: Dict[str, List[pd.Series]] = {
            "local_same_district": [],
            "cross_district_same_state": [],
            "cross_state": [],
            "cold_atms": [],
            "high_graph_evidence": [],
            "low_graph_evidence": [],
        }

        for _, row in test_df.iterrows():
            cid = str(row["complaint_id"])
            true_atm = str(self.wd_lookup.get(cid, "")).strip()
            if not true_atm:
                continue

            v_state = str(row.get("victim_state", "")).strip().lower()
            v_district = str(row.get("victim_district", "")).strip().lower()

            t_meta = self.atm_meta.get(true_atm, {})
            t_state = t_meta.get("state", "")
            t_district = t_meta.get("district", "")

            is_same_state = (v_state == t_state) if (v_state and t_state) else False
            is_same_district = (v_district == t_district) if (v_district and t_district) else False

            prior_cnt = self.atm_counts.get(true_atm, 0)
            is_cold = (prior_cnt <= 2)

            acc_id = self.acc_lookup.get(cid, None)
            has_graph = False
            if acc_id and self.graph_engine:
                net_atms = self.graph_engine.get_network_associated_atms_as_of_T([acc_id], as_of_T=row["complaint_timestamp"])
                has_graph = len(net_atms) > 0

            # Assign to strata
            if is_same_district and len(strata_samples["local_same_district"]) < target_per_stratum:
                strata_samples["local_same_district"].append(row)
            elif is_same_state and not is_same_district and len(strata_samples["cross_district_same_state"]) < target_per_stratum:
                strata_samples["cross_district_same_state"].append(row)
            elif not is_same_state and len(strata_samples["cross_state"]) < target_per_stratum:
                strata_samples["cross_state"].append(row)

            if is_cold and len(strata_samples["cold_atms"]) < target_per_stratum:
                strata_samples["cold_atms"].append(row)

            if has_graph and len(strata_samples["high_graph_evidence"]) < target_per_stratum:
                strata_samples["high_graph_evidence"].append(row)
            elif not has_graph and len(strata_samples["low_graph_evidence"]) < target_per_stratum:
                strata_samples["low_graph_evidence"].append(row)

        return {k: pd.DataFrame(v) for k, v in strata_samples.items()}

    def evaluate_stratum(self, stratum_name: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Evaluate performance metrics for a single stratum."""
        if len(df) == 0:
            return {"cases": 0, "recall": 0.0, "hit1": 0.0, "hit5": 0.0, "hit10": 0.0, "ndcg10": 0.0, "mrr": 0.0}

        retrieved_hits = {"union_recall": 0, "hit_1": 0, "hit_5": 0, "hit_10": 0, "ndcg_10": [], "rr": []}

        # Baseline performance tracking
        nearest_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0}
        skyvar_hits = {"hit_1": 0, "hit_5": 0, "hit_10": 0}

        n_cases = len(df)
        for _, row in df.iterrows():
            cid = str(row["complaint_id"])
            true_atm = str(self.wd_lookup.get(cid, "")).strip()
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

            candidates = self.retriever.retrieve_candidates(complaint=payload, as_of_T=t_complaint, chain_accounts=chain_accs)
            cand_ids = [c.atm_id for c in candidates]
            if true_atm in cand_ids:
                retrieved_hits["union_recall"] += 1

            feat_df = self.builder.build_features_for_candidates(complaint=payload, candidates=candidates, as_of_T=t_complaint, chain_accounts=chain_accs)
            raw_scores = self.ranker.predict_scores(feat_df)
            feat_df["ranking_score"] = raw_scores
            feat_df_sorted = feat_df.sort_values(by="ranking_score", ascending=False).reset_index(drop=True)

            pred_delay, pred_window_name, window_probs = self.time_predictor.predict(payload)
            anom_score, anom_subs = self.anomaly_detector.predict_anomaly_score(payload)
            time_window_short = list(window_probs.keys())[0] if window_probs else "<1h"

            fused_predictions = self.fusion_engine.fuse_predictions(
                ranked_candidates_df=feat_df_sorted,
                predicted_delay_hours=pred_delay,
                predicted_time_window_short=time_window_short,
                predicted_time_window_full=pred_window_name,
                anomaly_score=anom_score,
                anomaly_sub_scores=anom_subs,
            )

            cipher_ids = [p.atm_id for p in fused_predictions]
            if true_atm in cipher_ids:
                pos = cipher_ids.index(true_atm) + 1
                retrieved_hits["rr"].append(1.0 / pos)
                if pos <= 1:
                    retrieved_hits["hit_1"] += 1
                if pos <= 5:
                    retrieved_hits["hit_5"] += 1
                if pos <= 10:
                    retrieved_hits["hit_10"] += 1
                    retrieved_hits["ndcg_10"].append(1.0 / np.log2(pos + 1))
                else:
                    retrieved_hits["ndcg_10"].append(0.0)
            else:
                retrieved_hits["rr"].append(0.0)
                retrieved_hits["ndcg_10"].append(0.0)

            # Nearest ATM Baseline
            nearest_sorted = sorted(candidates, key=lambda c: c.distance_km)
            n_ids = [c.atm_id for c in nearest_sorted]
            if true_atm in n_ids[:1]:
                nearest_hits["hit_1"] += 1
            if true_atm in n_ids[:5]:
                nearest_hits["hit_5"] += 1
            if true_atm in n_ids[:10]:
                nearest_hits["hit_10"] += 1

            # SKYVAR Baseline
            skyvar_score = 0.60 * feat_df["geographic_similarity"] + 0.40 * (feat_df["nearby_atm_count"] / 20.0)
            feat_df["skyvar_score"] = skyvar_score
            skyvar_sorted = feat_df.sort_values(by="skyvar_score", ascending=False)
            s_ids = list(skyvar_sorted["atm_id"])
            if true_atm in s_ids[:1]:
                skyvar_hits["hit_1"] += 1
            if true_atm in s_ids[:5]:
                skyvar_hits["hit_5"] += 1
            if true_atm in s_ids[:10]:
                skyvar_hits["hit_10"] += 1

        return {
            "cases": n_cases,
            "ciris_recall": retrieved_hits["union_recall"] / n_cases,
            "ciris_hit1": retrieved_hits["hit_1"] / n_cases,
            "ciris_hit5": retrieved_hits["hit_5"] / n_cases,
            "ciris_hit10": retrieved_hits["hit_10"] / n_cases,
            "ciris_ndcg10": float(np.mean(retrieved_hits["ndcg_10"])),
            "ciris_mrr": float(np.mean(retrieved_hits["rr"])),
            "nearest_hit10": nearest_hits["hit_10"] / n_cases,
            "skyvar_hit10": skyvar_hits["hit_10"] / n_cases,
        }

    def run_stratified_benchmark(self, target_per_stratum: int = 15) -> Dict[str, Any]:
        """Execute full stratified benchmark across all 6 strata."""
        print("=" * 80)
        print("PHASE 5: STRATIFIED BENCHMARK EVALUATION")
        print("=" * 80)

        samples = self.build_stratified_samples(target_per_stratum=target_per_stratum)
        results = {}

        all_cases = []
        for name, df in samples.items():
            print(f"\n[Evaluating Stratum] {name} ({len(df)} cases)...")
            res = self.evaluate_stratum(name, df)
            results[name] = res
            print(f"  -> Recall: {res['ciris_recall']*100:.1f}% | Hit@1: {res['ciris_hit1']*100:.1f}% | Hit@5: {res['ciris_hit5']*100:.1f}% | Hit@10: {res['ciris_hit10']*100:.1f}% | NDCG@10: {res['ciris_ndcg10']:.4f}")
            all_cases.append(df)

        # Pooled performance
        pooled_df = pd.concat(all_cases).drop_duplicates(subset=["complaint_id"])
        print(f"\n[Evaluating Pooled Stratified Benchmark] ({len(pooled_df)} total unique cases)...")
        pooled_res = self.evaluate_stratum("pooled_total", pooled_df)
        results["pooled_total"] = pooled_res

        output_path = os.path.join(self.model_dir, "stratified_benchmark_results.json")
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print("\n" + "=" * 80)
        print("STRATIFIED BENCHMARK COMPLETED SUMMARY:")
        print(f"  - Total Pooled Cases: {pooled_res['cases']}")
        print(f"  - Pooled Union Recall: {pooled_res['ciris_recall']*100:.2f}%")
        print(f"  - Pooled HitRate@10:  {pooled_res['ciris_hit10']*100:.2f}%")
        print(f"  - Pooled NDCG@10:     {pooled_res['ciris_ndcg10']:.4f}")
        print("=" * 80)

        return results


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    evaluator = StratifiedEvaluator()
    evaluator.run_stratified_benchmark(target_per_stratum=15)

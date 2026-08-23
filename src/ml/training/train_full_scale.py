"""
Full-Scale Production Training Pipeline for CIRIS / CIPHER ML V4.

Executes Step 7 through Step 13:
- Trains LightGBM LambdaMART on 8,019,703 training rank pairs
- Evaluates on 1,939,597 validation rank pairs
- Trains Time-to-Cashout Regression & Classification Models
- Trains Isolation Forest Anomaly Detector
- Builds Historical Hotspot Cache
- Generates Out-of-Fold (OOF) predictions and trains Logistic Regression Fusion Meta-Model
- Fits Probability Calibration on validation data
- Saves production artifacts to models/final/
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import yaml
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple

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


def run_full_training(
    dataset_dir: str = "datasets/final",
    output_dir: str = "models/final",
    n_ranker_estimators: int = 150,
    n_time_estimators: int = 100,
) -> Dict[str, Any]:
    start_total_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("CIRIS / CIPHER ML V4 — FULL-SCALE MODEL TRAINING")
    print(f"Dataset Directory: {dataset_dir}")
    print(f"Output Artifacts:  {output_dir}")
    print(f"Timestamp:         {datetime.now().isoformat()}")
    print("=" * 70)

    loader = DatasetLoader(dataset_dir)

    # -------------------------------------------------------------
    # 1. LOAD AND INITIALIZE OFFLINE INTELLIGENCE
    # -------------------------------------------------------------
    print("\n[Stage 1/7] Loading Relational Entity Tables...")
    t0 = time.time()
    atm_master_df = loader.load_atm_master()
    withdrawals_df = loader.load_withdrawals()
    graph_edges_df = loader.load_graph_edges()
    case_links_df = loader.load_case_links()
    upi_df = loader.load_upi_entities()
    complaints_df = loader.load_complaints()

    print(f"  - ATMs Loaded:         {len(atm_master_df):,}")
    print(f"  - Withdrawals Loaded:  {len(withdrawals_df):,}")
    print(f"  - Graph Edges Loaded:  {len(graph_edges_df):,}")
    print(f"  - Case Links Loaded:   {len(case_links_df):,}")
    print(f"  - Complaints Loaded:   {len(complaints_df):,}")
    print(f"  - Relational Load Time: {time.time() - t0:.2f}s")

    print("\n[Stage 2/7] Initializing Spatial Index & Hotspot Cache...")
    t0 = time.time()
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
    print(f"  - Offline Engines Initialized in {time.time() - t0:.2f}s")

    # -------------------------------------------------------------
    # 2. TRAIN TIME-TO-CASHOUT PREDICTOR
    # -------------------------------------------------------------
    print("\n[Stage 3/7] Training Time-to-Cashout Predictor (Regression + Classification)...")
    t0 = time.time()
    train_time, val_time, _ = loader.load_time_splits()
    train_comp = complaints_df[complaints_df["complaint_id"].isin(train_time["complaint_id"])].copy()
    val_comp = complaints_df[complaints_df["complaint_id"].isin(val_time["complaint_id"])].copy()

    time_predictor = TimeToCashoutPredictor(n_estimators=n_time_estimators, learning_rate=0.06)
    time_metrics = time_predictor.fit(
        train_complaints_df=train_comp,
        train_time_df=train_time,
        val_complaints_df=val_comp,
        val_time_df=val_time,
    )
    time_train_duration = time.time() - t0
    print(f"  - Time Model Trained in {time_train_duration:.2f}s")
    print(f"  - Regression MAE (Val):    {time_metrics.get('regression_MAE_hours', 0.0):.2f} hours")
    print(f"  - Classifier Accuracy:     {time_metrics.get('classification_Accuracy', 0.0):.4f}")
    print(f"  - Classifier Macro F1:     {time_metrics.get('classification_Macro_F1', 0.0):.4f}")

    # -------------------------------------------------------------
    # 3. TRAIN ANOMALY DETECTOR (ISOLATION FOREST)
    # -------------------------------------------------------------
    print("\n[Stage 4/7] Training Anomaly Detector (Isolation Forest)...")
    t0 = time.time()
    train_anom, val_anom, _ = loader.load_anomaly_splits()
    anomaly_detector = AnomalyDetector(contamination=0.10, random_state=42)
    anom_metrics = anomaly_detector.fit(train_anom)
    anom_train_duration = time.time() - t0
    print(f"  - Anomaly Model Trained in {anom_train_duration:.2f}s")
    print(f"  - Training Samples:        {anom_metrics.get('n_samples', 0):,}")
    print(f"  - Score Range:             [{anom_metrics.get('score_min', 0.0):.4f}, {anom_metrics.get('score_max', 0.0):.4f}]")

    # -------------------------------------------------------------
    # 4. TRAIN FULL-SCALE LOCATION RANKER (LAMBDAMART)
    # -------------------------------------------------------------
    print("\n[Stage 5/7] Loading Full-Scale Ranking Splits...")
    t0 = time.time()
    train_rank = loader.load_rank_split("train", optimized_dtypes=True)
    val_rank = loader.load_rank_split("val", optimized_dtypes=True)
    load_rank_duration = time.time() - t0

    n_train_rows = len(train_rank)
    n_val_rows = len(val_rank)
    print(f"  - Train Rank Pairs Loaded: {n_train_rows:,} rows in {load_rank_duration:.2f}s")
    print(f"  - Val Rank Pairs Loaded:   {n_val_rows:,} rows")

    print(f"\n[Stage 5b/7] Training LightGBM LambdaMART Ranker on {n_train_rows:,} rows...")
    t0 = time.time()
    ranker = ATMRanker(
        n_estimators=n_ranker_estimators,
        learning_rate=0.08,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
    )
    ranker_metrics = ranker.fit(train_df=train_rank, val_df=val_rank, early_stopping_rounds=25)
    ranker_train_duration = time.time() - t0
    print(f"  - LambdaMART Trained in {ranker_train_duration:.2f}s")
    print(f"  - Best Iteration:  {ranker_metrics.get('best_iteration', n_ranker_estimators)}")
    print(f"  - Val NDCG@1:      {ranker_metrics.get('NDCG@1', 0.0):.4f}")
    print(f"  - Val NDCG@3:      {ranker_metrics.get('NDCG@3', 0.0):.4f}")
    print(f"  - Val NDCG@5:      {ranker_metrics.get('NDCG@5', 0.0):.4f}")
    print(f"  - Val NDCG@10:     {ranker_metrics.get('NDCG@10', 0.0):.4f}")
    print(f"  - Val MRR:         {ranker_metrics.get('MRR', 0.0):.4f}")
    print(f"  - Val HitRate@1:   {ranker_metrics.get('HitRate@1', 0.0):.4f}")
    print(f"  - Val HitRate@5:   {ranker_metrics.get('HitRate@5', 0.0):.4f}")
    print(f"  - Val HitRate@10:  {ranker_metrics.get('HitRate@10', 0.0):.4f}")

    # -------------------------------------------------------------
    # 5. OUT-OF-FOLD MULTI-SIGNAL FUSION & PROBABILITY CALIBRATION
    # -------------------------------------------------------------
    print("\n[Stage 6/7] Generating Validation Predictions & Fitting Calibration / Fusion...")
    t0 = time.time()

    # Predict validation scores
    val_raw_scores = ranker.predict_scores(val_rank)
    val_labels = val_rank["label"].values.astype(int)

    # Fit Probability Calibrator (Platt Scaling)
    calibrator = ProbabilityCalibrator(method="platt")
    cal_metrics = calibrator.fit(val_raw_scores, val_labels)
    val_calibrated_probs = calibrator.predict_proba(val_raw_scores)

    print(f"  - Probability Calibrator Fit (Brier Score: {cal_metrics.get('brier_score', 0.0):.6f})")

    # Fit Multi-Signal Logistic Regression Meta-Model on Validation Signals
    # Feature 1: Location calibrated probability
    # Feature 2: Time urgency score
    # Feature 3: Anomaly score
    # Feature 4: Historical hotspot score
    time_pred_map = dict(zip(val_comp["complaint_id"], val_comp.get("urgency_score", [0.5]*len(val_comp))))
    anom_pred_map = dict(zip(val_anom["complaint_id"], anomaly_detector.predict_anomaly_scores(val_anom)))

    val_time_signals = val_rank["complaint_id"].map(time_pred_map).fillna(0.5).values
    val_anom_signals = val_rank["complaint_id"].map(anom_pred_map).fillna(0.5).values
    val_hist_signals = val_rank["historical_hotspot_score_as_of_T"].fillna(0.0).values
    val_hist_norm = np.clip(val_hist_signals / (val_hist_signals.max() + 1e-5), 0.0, 1.0)

    # Design matrix for meta-model
    X_meta = np.column_stack([
        val_calibrated_probs,
        val_time_signals,
        val_anom_signals,
        val_hist_norm,
    ])

    fusion_engine = MultiSignalRiskFusionEngine(calibrator=calibrator)
    fusion_engine.fit_meta_model(X_meta, val_labels)
    fusion_duration = time.time() - t0
    print(f"  - Multi-Signal Risk Fusion Meta-Model Trained in {fusion_duration:.2f}s")

    # -------------------------------------------------------------
    # 6. SERIALIZE ALL ARTIFACTS TO models/final/
    # -------------------------------------------------------------
    print(f"\n[Stage 7/7] Serializing Production Model Artifacts to '{output_dir}'...")
    t0 = time.time()

    ranker.save(os.path.join(output_dir, "location_ranker.joblib"))
    time_predictor.save(os.path.join(output_dir, "time_predictor.joblib"))
    anomaly_detector.save(os.path.join(output_dir, "anomaly_detector.joblib"))
    fusion_engine.save(os.path.join(output_dir, "fusion_engine.joblib"))
    calibrator.save(os.path.join(output_dir, "calibrator.joblib"))

    # Save offline metadata & indices
    offline_metadata = {
        "atm_master_df": atm_master_df,
        "withdrawals_df": withdrawals_df,
        "graph_edges_df": graph_edges_df,
        "case_links_df": case_links_df,
        "upi_df": upi_df,
    }
    joblib.dump(offline_metadata, os.path.join(output_dir, "offline_metadata.joblib"), compress=3)

    # Save feature schema
    feature_schema = {
        "feature_version": "v4.0.0",
        "feature_columns": FeatureBuilder.FEATURE_COLUMNS,
        "num_features": len(FeatureBuilder.FEATURE_COLUMNS),
        "location_type_map": FeatureBuilder.LOCATION_TYPE_MAP,
        "account_type_map": FeatureBuilder.ACCOUNT_TYPE_MAP,
    }
    with open(os.path.join(output_dir, "feature_schema.json"), "w") as f:
        json.dump(feature_schema, f, indent=2)

    # Save training configuration
    training_config = {
        "model_version": "v4.1.0-final_v2",
        "dataset_version": "50k-final-scale",
        "dataset_path": os.path.abspath(dataset_dir),
        "random_seed": 42,
        "training_timestamp": datetime.now().isoformat(),
        "candidate_retrieval_configuration": {
            "geo_radius_km": 250.0,
            "geo_fallback_knn": 200,
            "top_hotspots_count": 1500,
            "enable_district_fallback": True,
            "enable_state_fallback": True,
            "state_top_k": 100,
            "enable_temporal_mule_graph": True,
            "freeze_status": "FROZEN_VALIDATED_K2",
        },
        "ranker": {
            "model_type": "LightGBM LGBMRanker (LambdaRank)",
            "n_estimators": n_ranker_estimators,
            "learning_rate": 0.08,
            "num_leaves": 31,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "train_rows": n_train_rows,
            "val_rows": n_val_rows,
            "feature_count": len(FeatureBuilder.FEATURE_COLUMNS),
        },
        "time_model": {
            "model_type": "LightGBM Regressor + Classifier",
            "n_estimators": n_time_estimators,
            "train_cases": len(train_time),
            "val_cases": len(val_time),
        },
        "anomaly_model": {
            "model_type": "Isolation Forest",
            "contamination": 0.10,
            "train_cases": len(train_anom),
        },
        "fusion_model": {
            "model_type": "Logistic Regression Meta-Learner + Platt Calibration",
        },
    }
    with open(os.path.join(output_dir, "training_config.yaml"), "w") as f:
        yaml.dump(training_config, f, default_flow_style=False)

    # Save metrics summary
    metrics_summary = {
        "training_timestamp": datetime.now().isoformat(),
        "total_training_duration_seconds": round(time.time() - start_total_time, 2),
        "ranker_metrics": ranker_metrics,
        "time_metrics": time_metrics,
        "anomaly_metrics": anom_metrics,
        "calibration_metrics": cal_metrics,
    }
    with open(os.path.join(output_dir, "metrics.json"), "w") as f:
        json.dump(metrics_summary, f, indent=2)

    # Save metadata JSON
    model_metadata = {
        "model_name": "CIPHER-X ML V4 Production Suite (V2 Optimized Retrieval)",
        "version": "4.1.0",
        "trained_on": "50,000 complaints final-scale dataset (8,019,703 rank pairs)",
        "train_period": "2024-01-01 to 2025-09-27",
        "val_period": "2025-09-28 to 2026-02-12",
        "test_period": "2026-02-12 to 2026-06-30 (UNTOUCHED)",
        "feature_count": len(FeatureBuilder.FEATURE_COLUMNS),
        "retrieval_configuration": training_config["candidate_retrieval_configuration"],
        "metrics": metrics_summary,
    }
    with open(os.path.join(output_dir, "model_metadata.json"), "w") as f:
        json.dump(model_metadata, f, indent=2)

    print(f"  - Production Artifacts Saved in {time.time() - t0:.2f}s to '{output_dir}'")
    total_duration = time.time() - start_total_time
    print("\n" + "=" * 70)
    print(f"TRAINING COMPLETE IN {total_duration:.2f}s ({total_duration/60:.2f} min)")
    print("=" * 70)

    return metrics_summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Full-Scale Training for CIRIS ML V4")
    parser.add_argument("--dataset-dir", type=str, default="datasets/final", help="Path to final datasets")
    parser.add_argument("--output-dir", type=str, default="models/final_v2", help="Artifact output directory")
    parser.add_argument("--ranker-estimators", type=int, default=150, help="Number of estimators for ranker")
    parser.add_argument("--time-estimators", type=int, default=100, help="Number of estimators for time model")
    args = parser.parse_args()

    run_full_training(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        n_ranker_estimators=args.ranker_estimators,
        n_time_estimators=args.time_estimators,
    )

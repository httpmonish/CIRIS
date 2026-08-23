"""
CIPHER-X v4 End-to-End Intelligence Pipeline Orchestrator.

Integrates all offline intelligence structures, candidate retrieval, point-in-time feature builders,
multi-model ranker, time predictor, anomaly detector, probability calibrator, multi-signal fusion,
TreeSHAP explainability, and operational guardrails into a production-grade inference service.
"""

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from src.ml.contracts.schemas import (
    ComplaintPayload,
    IntelligenceReport,
    ATMRiskPrediction,
)
from src.ml.retrieval.spatial_index import SpatialIndex
from src.ml.retrieval.graph_engine import TemporalGraphEngine
from src.ml.retrieval.hotspot_cache import HistoricalHotspotCache
from src.ml.retrieval.candidate_retriever import CandidateRetriever
from src.ml.features.feature_builder import FeatureBuilder
from src.ml.models.ranker import ATMRanker
from src.ml.models.time_predictor import TimeToCashoutPredictor
from src.ml.models.anomaly_detector import AnomalyDetector
from src.ml.models.fusion import ProbabilityCalibrator, MultiSignalRiskFusionEngine
from src.ml.xai.explainer import TreeSHAPExplainer
from src.ml.routing.guardrails import OperationalGuardrails


from src.ml.data.loader import DatasetLoader


class CIPHERPipeline:
    """
    End-to-End Predictive Cybercrime Analytics Pipeline.
    """

    def __init__(
        self,
        atm_master_df: Optional[pd.DataFrame] = None,
        withdrawals_df: Optional[pd.DataFrame] = None,
        graph_edges_df: Optional[pd.DataFrame] = None,
        case_links_df: Optional[pd.DataFrame] = None,
        upi_df: Optional[pd.DataFrame] = None,
    ):
        self.atm_master_df = atm_master_df.copy() if atm_master_df is not None else pd.DataFrame()
        self.withdrawals_df = withdrawals_df.copy() if withdrawals_df is not None else pd.DataFrame()
        self.graph_edges_df = graph_edges_df.copy() if graph_edges_df is not None else pd.DataFrame()
        self.case_links_df = case_links_df.copy() if case_links_df is not None else pd.DataFrame()
        self.upi_df = upi_df.copy() if upi_df is not None else pd.DataFrame()

        # Component instances
        self.spatial_index: Optional[SpatialIndex] = None
        self.hotspot_cache: Optional[HistoricalHotspotCache] = None
        self.graph_engine: Optional[TemporalGraphEngine] = None
        self.candidate_retriever: Optional[CandidateRetriever] = None
        self.feature_builder: Optional[FeatureBuilder] = None
        self.ranker: Optional[ATMRanker] = None
        self.time_predictor: Optional[TimeToCashoutPredictor] = None
        self.anomaly_detector: Optional[AnomalyDetector] = None
        self.calibrator: Optional[ProbabilityCalibrator] = None
        self.fusion_engine: Optional[MultiSignalRiskFusionEngine] = None
        self.explainer: Optional[TreeSHAPExplainer] = None

        if not self.atm_master_df.empty:
            self._init_offline_intelligence()

    def _init_offline_intelligence(self) -> None:
        """Initialize core retrieval and graph engines from in-memory tables."""
        self.spatial_index = SpatialIndex(self.atm_master_df)
        self.hotspot_cache = HistoricalHotspotCache(
            atm_master_df=self.atm_master_df,
            withdrawals_df=self.withdrawals_df,
        )
        self.graph_engine = TemporalGraphEngine(
            graph_edges_df=self.graph_edges_df,
            case_links_df=self.case_links_df,
            withdrawals_df=self.withdrawals_df,
            upi_df=self.upi_df,
        )
        self.candidate_retriever = CandidateRetriever(
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
        self.feature_builder = FeatureBuilder(
            atm_master_df=self.atm_master_df,
            hotspot_cache=self.hotspot_cache,
            graph_engine=self.graph_engine,
            spatial_index=self.spatial_index,
        )

    def train(
        self,
        dataset_dir: str = "datasets/final",
        n_ranker_estimators: int = 120,
        n_time_estimators: int = 80,
        rank_sample_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Train all supervised and unsupervised models from dataset directory via DatasetLoader.
        """
        loader = DatasetLoader(dataset_dir)

        # Load tables
        self.atm_master_df = loader.load_atm_master()
        self.withdrawals_df = loader.load_withdrawals()
        self.graph_edges_df = loader.load_graph_edges()
        self.case_links_df = loader.load_case_links()
        self.upi_df = loader.load_upi_entities()

        self._init_offline_intelligence()

        # Load split datasets
        train_rank = loader.load_rank_split("train", nrows=rank_sample_rows)
        val_rank = loader.load_rank_split("val", nrows=rank_sample_rows // 4 if rank_sample_rows else None)

        train_time, val_time, _ = loader.load_time_splits()
        complaints_df = loader.load_complaints()
        train_anom, val_anom, _ = loader.load_anomaly_splits()

        # 1. Train ATM Ranker
        self.ranker = ATMRanker(n_estimators=n_ranker_estimators, learning_rate=0.08)
        ranker_metrics = self.ranker.fit(train_rank, val_df=val_rank)

        # 2. Fit Probability Calibrator on Validation Ranker Outputs
        val_raw_scores = self.ranker.predict_scores(val_rank)
        val_labels = val_rank["label"].values
        self.calibrator = ProbabilityCalibrator(method="platt")
        cal_metrics = self.calibrator.fit(val_raw_scores, val_labels)

        # 3. Train Time-to-Cashout Predictor
        self.time_predictor = TimeToCashoutPredictor(n_estimators=n_time_estimators, learning_rate=0.08)
        train_comp = complaints_df[complaints_df["complaint_id"].isin(train_time["complaint_id"])].copy()
        val_comp = complaints_df[complaints_df["complaint_id"].isin(val_time["complaint_id"])].copy()
        time_metrics = self.time_predictor.fit(train_comp, train_time, val_comp, val_time)

        # 4. Train Anomaly Detector
        self.anomaly_detector = AnomalyDetector(contamination=0.10)
        anom_metrics = self.anomaly_detector.fit(train_anom)

        # 5. Initialize Multi-Signal Fusion Engine & SHAP Explainer
        self.fusion_engine = MultiSignalRiskFusionEngine(calibrator=self.calibrator)
        self.explainer = TreeSHAPExplainer(self.ranker)

        return {
            "ranker_metrics": ranker_metrics,
            "calibration_metrics": cal_metrics,
            "time_metrics": time_metrics,
            "anomaly_metrics": anom_metrics,
        }

    def analyze_complaint(
        self,
        complaint: ComplaintPayload,
        top_k: int = 10,
    ) -> IntelligenceReport:
        """
        Execute full end-to-end predictive intelligence pipeline for an incoming complaint.
        """
        if self.ranker is None or self.time_predictor is None or self.anomaly_detector is None:
            raise RuntimeError("Pipeline models are not loaded or trained.")

        t_pred = complaint.complaint_timestamp

        # -------------------------------------------------------------
        # 1. Operational Guardrails Check
        # -------------------------------------------------------------
        is_actionable, reason = OperationalGuardrails.check_complaint_actionability(complaint)
        if not is_actionable:
            return IntelligenceReport(
                complaint_id=complaint.complaint_id,
                prediction_timestamp=t_pred,
                total_candidates_evaluated=0,
                top_candidates=[],
                highest_risk_atm=None,
                alert_status="MONITOR_HOLD",
                connected_entities={"routing_reason": reason, "actionable": False},
            )

        # -------------------------------------------------------------
        # 2. Stage 0: Hybrid Candidate Retrieval
        # -------------------------------------------------------------
        candidates = self.candidate_retriever.retrieve_candidates(complaint, as_of_T=t_pred)
        if not candidates:
            # Fallback to nearest 10 ATMs if all filters empty
            candidates = [
                self.candidate_retriever.spatial_index.query_knn(
                    complaint.victim_location.latitude,
                    complaint.victim_location.longitude,
                    k=10
                )
            ]

        # -------------------------------------------------------------
        # 3. Stage 1: Feature Matrix Construction
        # -------------------------------------------------------------
        feature_df = self.feature_builder.build_features_for_candidates(complaint, candidates, as_of_T=t_pred)

        # -------------------------------------------------------------
        # 4. Stage 2: Supervised ATM Ranking
        # -------------------------------------------------------------
        ranked_df = self.ranker.rank_candidates_for_complaint(feature_df)

        # -------------------------------------------------------------
        # 5. Stage 3 & 4: Time Prediction and Anomaly Scoring
        # -------------------------------------------------------------
        pred_delay_h, pred_win_full, pred_win_probs = self.time_predictor.predict(complaint)
        pred_win_short = max(pred_win_probs.items(), key=lambda x: x[1])[0]

        anom_score, anom_subs = self.anomaly_detector.predict_anomaly_score(complaint)

        # -------------------------------------------------------------
        # 6. Stage 5: Multi-Signal Risk Fusion
        # -------------------------------------------------------------
        predictions = self.fusion_engine.fuse_predictions(
            ranked_candidates_df=ranked_df,
            predicted_delay_hours=pred_delay_h,
            predicted_time_window_short=pred_win_short,
            predicted_time_window_full=pred_win_full,
            anomaly_score=anom_score,
            anomaly_sub_scores=anom_subs,
        )

        top_predictions = predictions[:top_k]

        # -------------------------------------------------------------
        # 7. Stage 6: TreeSHAP Evidence Generation for Top Candidates
        # -------------------------------------------------------------
        for idx, pred in enumerate(top_predictions[:3]):
            matching_row = ranked_df[ranked_df["atm_id"] == pred.atm_id].iloc[[0]]
            shap_attrs, narrative = self.explainer.explain_candidate(matching_row)
            pred.shap_evidence = shap_attrs
            pred.graph_evidence = {
                "narrative_briefing": narrative,
                "time_window_probabilities": pred_win_probs,
                "anomaly_breakdown": anom_subs,
            }

        highest_risk = top_predictions[0] if top_predictions else None
        alert_status = "DISPATCH_ALERT" if (highest_risk and highest_risk.confidence_tier == "HIGH") else "MONITOR_HOLD"

        # Connected mule entity summary
        connected_entities = {
            "mule_cluster_id": self.graph_engine.case_to_cluster.get(complaint.complaint_id, "NONE"),
            "mule_chain_accounts": self.graph_engine.case_to_chain.get(complaint.complaint_id, []),
            "time_window_breakdown": pred_win_probs,
            "anomaly_score": anom_score,
        }

        report = IntelligenceReport(
            complaint_id=complaint.complaint_id,
            prediction_timestamp=t_pred,
            total_candidates_evaluated=len(candidates),
            top_candidates=top_predictions,
            highest_risk_atm=highest_risk,
            alert_status=alert_status,
            connected_entities=connected_entities,
        )
        return report

    def save_pipeline(self, model_dir: str) -> None:
        """Serialize complete pipeline state and artifacts."""
        os.makedirs(model_dir, exist_ok=True)
        self.ranker.save(os.path.join(model_dir, "ranker.joblib"))
        self.time_predictor.save(os.path.join(model_dir, "time_predictor.joblib"))
        self.anomaly_detector.save(os.path.join(model_dir, "anomaly_detector.joblib"))
        self.fusion_engine.save(os.path.join(model_dir, "fusion_engine.joblib"))

        # Save offline dataframes
        meta_bundle = {
            "atm_master": self.atm_master_df,
            "withdrawals": self.withdrawals_df,
            "graph_edges": self.graph_edges_df,
            "case_links": self.case_links_df,
            "upi": self.upi_df,
        }
        joblib.dump(meta_bundle, os.path.join(model_dir, "offline_metadata.joblib"))

    def load_pipeline(self, model_dir: str) -> None:
        """Load complete serialized pipeline."""
        meta = joblib.load(os.path.join(model_dir, "offline_metadata.joblib"))
        self.atm_master_df = meta.get("atm_master_df", meta.get("atm_master"))
        self.withdrawals_df = meta.get("withdrawals_df", meta.get("withdrawals"))
        self.graph_edges_df = meta.get("graph_edges_df", meta.get("graph_edges"))
        self.case_links_df = meta.get("case_links_df", meta.get("case_links"))
        self.upi_df = meta.get("upi_df", meta.get("upi"))

        self._init_offline_intelligence()

        ranker_path = (
            os.path.join(model_dir, "location_ranker.joblib")
            if os.path.exists(os.path.join(model_dir, "location_ranker.joblib"))
            else os.path.join(model_dir, "ranker.joblib")
        )
        self.ranker = ATMRanker()
        self.ranker.load(ranker_path)

        self.time_predictor = TimeToCashoutPredictor()
        self.time_predictor.load(os.path.join(model_dir, "time_predictor.joblib"))

        self.anomaly_detector = AnomalyDetector()
        self.anomaly_detector.load(os.path.join(model_dir, "anomaly_detector.joblib"))

        self.fusion_engine = MultiSignalRiskFusionEngine()
        self.fusion_engine.load(os.path.join(model_dir, "fusion_engine.joblib"))
        self.calibrator = self.fusion_engine.calibrator

        self.explainer = TreeSHAPExplainer(self.ranker)

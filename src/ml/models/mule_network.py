"""
Mule and Network Intelligence Engine for CIRIS.

Evaluates mule risk scores, confidence tiers, and evidence tags for accounts
in money-flow subgraphs without asserting non-adjudicated criminality labels.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.ml.contracts.case_intelligence import MuleEntityCandidate
from src.ml.features.entity_resolution import EntityResolutionEngine
from src.ml.retrieval.money_flow_graph import MoneyFlowGraphEngine
from src.ml.features.fragmentation_detector import TransactionFragmentationDetector


class MuleNetworkIntelligenceEngine:
    """
    Evaluates account-level mule risk using graph centrality, fragmentation, and cross-case linkage.
    """

    def __init__(
        self,
        entity_resolver: Optional[EntityResolutionEngine] = None,
        graph_engine: Optional[MoneyFlowGraphEngine] = None,
        fragmentation_detector: Optional[TransactionFragmentationDetector] = None,
    ):
        self.entity_resolver = entity_resolver or EntityResolutionEngine()
        self.graph_engine = graph_engine or MoneyFlowGraphEngine()
        self.fragmentation_detector = fragmentation_detector or TransactionFragmentationDetector()

    def evaluate_account_mule_risk(
        self,
        account_id: str,
        complaint_id: str,
        as_of_T: datetime,
        reported_loss_amount: float = 10000.0,
    ) -> MuleEntityCandidate:
        """
        Evaluate mule candidate risk score, confidence, and evidence tags.
        """
        acc_str = str(account_id)
        ent_id = self.entity_resolver.resolve_account_entity(acc_str)

        # 1. Graph topology & cluster extraction
        subgraph = self.graph_engine.extract_point_in_time_subgraph([acc_str], as_of_T=as_of_T, max_hops=2)
        cluster_size = subgraph["cluster_size"]
        edges = subgraph["edges"]
        degree = len(edges)

        # 2. Fragmentation analysis
        frag_analysis = self.fragmentation_detector.analyze_account_fragmentation(
            account_id=acc_str,
            as_of_T=as_of_T,
            reported_loss_amount=reported_loss_amount,
        )

        # 3. Calculate Risk Score
        risk_score = 0.10  # base propensity
        evidence_tags = []

        if degree >= 5:
            risk_score += 0.25
            evidence_tags.append("HIGH_NETWORK_CONNECTIVITY")
        elif degree >= 2:
            risk_score += 0.15
            evidence_tags.append("MULTI_HOP_RELATIONSHIP")

        if frag_analysis["is_fragmented"]:
            risk_score += 0.25
            evidence_tags.append("FRAGMENTED_SPLITTING_PATTERN")

        if frag_analysis["outgoing_txn_count"] >= 3:
            risk_score += 0.20
            evidence_tags.append("RAPID_VELOCITY_SURGE")

        if cluster_size >= 5:
            risk_score += 0.15
            evidence_tags.append("ORGANIZED_CLUSTER_MEMBERSHIP")

        risk_score = min(1.0, risk_score)

        # Determine confidence
        confidence = "HIGH" if risk_score >= 0.70 else ("MEDIUM" if risk_score >= 0.40 else "LOW")

        if not evidence_tags:
            evidence_tags.append("STANDARD_MONEY_FLOW_NODE")

        return MuleEntityCandidate(
            entity_id=ent_id,
            account_id=acc_str,
            mule_risk_score=float(risk_score),
            confidence=confidence,
            evidence_tags=evidence_tags,
            cluster_size=cluster_size,
            degree_centrality=degree,
            rapid_in_out_ratio=frag_analysis["micro_txn_proportion"],
            is_unflagged_related=True,
        )

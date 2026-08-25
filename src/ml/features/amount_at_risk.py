"""
Amount-at-Risk Accounting Engine for CIRIS.

Provides deterministic financial accounting for disputed funds, tracking
moved funds vs remaining balances without asserting arbitrary total balance freezes.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.ml.contracts.case_intelligence import AmountAtRiskSummary
from src.ml.retrieval.money_flow_graph import MoneyFlowGraphEngine


class AmountAtRiskEngine:
    """
    Computes deterministic amount-at-risk accounting across point-in-time money flow paths.
    """

    def __init__(self, graph_engine: Optional[MoneyFlowGraphEngine] = None):
        self.graph_engine = graph_engine or MoneyFlowGraphEngine()

    def compute_amount_at_risk(
        self,
        seed_account: str,
        reported_loss_amount: float,
        as_of_T: datetime,
    ) -> AmountAtRiskSummary:
        """
        Compute deterministic accounting breakdown for a disputed fraud amount.
        """
        loss = float(reported_loss_amount) if reported_loss_amount > 0 else 10000.0
        acc_str = str(seed_account)

        paths = self.graph_engine.find_money_paths(acc_str, as_of_T=as_of_T, max_hops=2)

        observed_moved = 0.0
        for p in paths:
            if p.get("hop_count", 0) > 0:
                observed_moved += float(p.get("total_amount_flow", 0.0))

        observed_moved = min(loss, observed_moved)
        observed_remaining = max(0.0, loss - observed_moved)
        unresolved = max(0.0, loss - (observed_moved + observed_remaining))
        hold_recommended = observed_remaining

        return AmountAtRiskSummary(
            disputed_amount=loss,
            observed_moved_amount=observed_moved,
            observed_remaining_amount=observed_remaining,
            unresolved_amount=unresolved,
            hold_review_recommended_amount=hold_recommended,
        )

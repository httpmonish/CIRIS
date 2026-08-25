"""
Endpoint Type Intelligence and Classifier Module for CIRIS.

Assesses endpoint likelihoods (ATM vs Merchant/POS vs Onward Transfer) and routes
investigative intelligence to specialized prediction sub-modules.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.ml.contracts.case_intelligence import EndpointPrediction
from src.ml.contracts.schemas import ComplaintPayload


class EndpointTypeClassifier:
    """
    Classifies fraud flow endpoints and assesses destination channel risk.
    """

    def __init__(self, atm_master_df: Optional[pd.DataFrame] = None):
        self.atm_master_df = atm_master_df.copy() if atm_master_df is not None else pd.DataFrame()

    def classify_endpoint_route(
        self,
        complaint: ComplaintPayload,
        path_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """
        Assess probability distribution across candidate endpoint types [ATM, MERCHANT, TRANSFER].
        """
        fraud_type = str(complaint.fraud_type).lower()
        channel = str(complaint.channel).lower()
        amount = float(complaint.reported_loss_amount)

        # Baseline probabilities
        p_atm = 0.60
        p_merchant = 0.20
        p_transfer = 0.20

        # Channel & Fraud Type Adjustments
        if "atm" in channel or "cash" in fraud_type:
            p_atm += 0.25
            p_merchant -= 0.15
            p_transfer -= 0.10
        elif "online" in fraud_type or "phishing" in fraud_type or "link" in fraud_type:
            p_merchant += 0.25
            p_atm -= 0.15
        elif "digital arrest" in fraud_type or "investment" in fraud_type:
            p_transfer += 0.30
            p_atm -= 0.20

        # Amount heuristics: Large amounts (>₹100k) lean towards multi-hop transfer
        if amount >= 100000.0:
            p_transfer += 0.20
            p_atm -= 0.10

        # Normalize
        total = p_atm + p_merchant + p_transfer
        p_atm /= total
        p_merchant /= total
        p_transfer /= total

        return {
            "ATM": float(p_atm),
            "MERCHANT": float(p_merchant),
            "TRANSFER": float(p_transfer),
        }

    def generate_merchant_endpoint_prediction(
        self,
        complaint: ComplaintPayload,
        probability: float,
    ) -> EndpointPrediction:
        """Generate Merchant/POS endpoint intelligence record."""
        return EndpointPrediction(
            endpoint_type="MERCHANT",
            endpoint_id="MERCHANT_PAYMENT_GATEWAY",
            endpoint_name="Online Merchant / POS Gateway",
            location_details={
                "city": complaint.victim_location.city,
                "district": complaint.victim_location.district,
                "merchant_category": "E-Commerce / Wallet Gateway",
            },
            probability=probability,
            predicted_time_window="1-3h",
            predicted_delay_hours=2.0,
            fused_risk_score=probability * 0.85,
            evidence_attributions=[
                {"feature": "channel", "friendly_name": "Online Payment Gateway Channel", "value": 1.0},
                {"feature": "fraud_type", "friendly_name": "Phishing / Malicious Link Pattern", "value": 1.0},
            ],
        )

    def generate_transfer_endpoint_prediction(
        self,
        complaint: ComplaintPayload,
        probability: float,
    ) -> EndpointPrediction:
        """Generate Onward Transfer endpoint intelligence record."""
        return EndpointPrediction(
            endpoint_type="TRANSFER",
            endpoint_id="DESTINATION_BANK_ACCOUNT",
            endpoint_name="Multi-Hop Inter-Bank Transfer",
            location_details={
                "city": complaint.victim_location.city,
                "district": complaint.victim_location.district,
                "routing": "IMPS / NEFT Onward Chain",
            },
            probability=probability,
            predicted_time_window="6-12h",
            predicted_delay_hours=8.0,
            fused_risk_score=probability * 0.75,
            evidence_attributions=[
                {"feature": "multi_hop", "friendly_name": "Layered Onward Inter-Bank Transfer", "value": 1.0},
            ],
        )

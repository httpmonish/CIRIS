"""
Intervention Recommendation Engine for CIRIS.

Generates calibrated policy intervention recommendations (HOLD REVIEW, MONITOR,
INVESTIGATE, ESCALATE) for authorized law enforcement and bank fraud officers.
"""

from typing import List, Dict, Any, Optional
from src.ml.contracts.case_intelligence import InterventionRecommendation, AmountAtRiskSummary, MuleEntityCandidate


class InterventionRecommendationEngine:
    """
    Evaluates case risk signals and outputs policy-compliant intervention recommendations.
    """

    def generate_recommendation(
        self,
        fused_risk_score: float,
        amount_summary: AmountAtRiskSummary,
        mule_candidates: List[MuleEntityCandidate],
        highest_risk_endpoint_type: str = "ATM",
    ) -> InterventionRecommendation:
        """
        Produce actionable, evidence-backed intervention recommendation.
        """
        score = float(fused_risk_score)
        rem_amount = amount_summary.observed_remaining_amount
        target_accs = [m.account_id for m in mule_candidates if m.mule_risk_score >= 0.50]

        if not target_accs and mule_candidates:
            target_accs = [mule_candidates[0].account_id]

        if score >= 0.75 or (rem_amount >= 50000.0 and score >= 0.50):
            action = "ESCALATE"
            rationale = (
                f"Critical risk score ({score:.2f}) and high loss amount (₹{amount_summary.disputed_amount:,.2f}). "
                f"Predicted {highest_risk_endpoint_type} cashout endpoint active. Priority field dispatch & bank hold review recommended."
            )
        elif score >= 0.50 or rem_amount > 0:
            action = "HOLD REVIEW"
            rationale = (
                f"Elevated risk score ({score:.2f}) with ₹{rem_amount:,.2f} observed remaining in suspect mule accounts. "
                "Recommend administrative hold review by authorized bank compliance officer."
            )
        elif score >= 0.30:
            action = "INVESTIGATE"
            rationale = (
                f"Moderate risk score ({score:.2f}). Suspicious network velocity detected. "
                "Recommend active surveillance and cross-case intelligence tracking."
            )
        else:
            action = "MONITOR"
            rationale = f"Low risk score ({score:.2f}). Logged for continuous background monitoring."

        return InterventionRecommendation(
            recommended_action=action,
            confidence_score=score,
            action_rationale=rationale,
            potential_hold_amount=rem_amount if action in ["ESCALATE", "HOLD REVIEW"] else 0.0,
            authorization_boundary="Authorized Bank / LEA Officer Review Required",
            target_accounts_for_review=target_accs,
        )

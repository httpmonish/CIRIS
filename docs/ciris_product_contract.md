# CIRIS Product Contract Specification

## Overview
This document defines the canonical JSON representation of a CIRIS Fraud Case, its intelligence data structures, graph relations, evidence attributions, and intervention recommendations.

---

## Case Object Schema (`CIRISCase`)

```json
{
  "case_id": "CASE-2026-0001",
  "complaint_id": "CMP_2026_0001",
  "status": "ANALYZING",
  "priority": "P1",
  "created_at": "2026-08-25T18:00:00Z",
  "updated_at": "2026-08-25T18:05:00Z",
  "prediction_timestamp": "2026-08-25T18:00:00Z",
  "victim": {
    "victim_id": "VICTIM_001",
    "state": "Maharashtra",
    "district": "Mumbai",
    "city": "Mumbai",
    "area": "Andheri West",
    "pincode": 400053,
    "latitude": 19.1136,
    "longitude": 72.8697
  },
  "reported_loss": 50000.0,
  "fraud_type": "Investment Cyber Fraud",
  "risk": {
    "overall_risk_score": 0.88,
    "confidence_tier": "HIGH",
    "calibrated_probability": 0.85
  },
  "amount_at_risk": {
    "disputed_amount": 50000.0,
    "observed_moved_amount": 35000.0,
    "observed_remaining_amount": 15000.0,
    "unresolved_amount": 0.0,
    "hold_review_recommended_amount": 15000.0
  },
  "entities": [
    {
      "entity_id": "ENT_001",
      "entity_type": "MULE_ACCOUNT",
      "risk_score": 0.82,
      "accounts": ["ACC_001"],
      "upi_ids": ["mule@sbi"],
      "cards": ["CARD_001"],
      "mobiles": ["MOB_001"],
      "devices": ["DEV_001"]
    }
  ],
  "money_flow": {
    "nodes": [
      { "id": "ACC_VICTIM", "type": "VICTIM", "label": "Victim Account", "risk": 0.0 },
      { "id": "ACC_001", "type": "MULE", "label": "Primary Mule ACC_001", "risk": 0.82 },
      { "id": "ATM_9981", "type": "ATM", "label": "ATM 9981 - Mumbai", "risk": 0.88 }
    ],
    "edges": [
      { "source": "ACC_VICTIM", "target": "ACC_001", "amount": 50000.0, "timestamp": "2026-08-25T17:15:00Z", "transaction_type": "IMPS" },
      { "source": "ACC_001", "target": "ATM_9981", "amount": 35000.0, "timestamp": "2026-08-25T17:45:00Z", "transaction_type": "ATM_WITHDRAWAL" }
    ]
  },
  "endpoint_predictions": [
    {
      "endpoint_type": "ATM",
      "endpoint_id": "ATM_9981",
      "endpoint_name": "SBI ATM - Andheri West",
      "location": {
        "city": "Mumbai",
        "district": "Mumbai",
        "state": "Maharashtra",
        "latitude": 19.1150,
        "longitude": 72.8710
      },
      "probability": 0.88,
      "predicted_time_window": "3-6h",
      "predicted_delay_hours": 3.5,
      "fused_risk_score": 0.88,
      "evidence_attributions": [
        { "feature": "spatial_distance_km", "importance": 0.35, "direction": "HIGH_RISK", "label": "Proximity to Complaint (4.2 km)" },
        { "feature": "mule_chain_velocity", "importance": 0.28, "direction": "HIGH_RISK", "label": "Rapid In-Out Flow (< 30 min)" }
      ]
    }
  ],
  "evidence": {
    "model_evidence": ["TreeSHAP Top Feature: Proximity < 5km", "Anomaly Score: 0.85"],
    "graph_evidence": ["Connected to known high-degree mule node ACC_001"],
    "transaction_evidence": ["Rapid 70% cashout within 30 minutes of victim transfer"],
    "historical_evidence": ["ATM_9981 flagged in 3 historical cybercrime complaints"],
    "geographic_evidence": ["Located in High-Risk Withdrawal Hotspot Zone"]
  },
  "timeline": [
    { "timestamp": "2026-08-25T17:15:00Z", "type": "COMPLAINT", "description": "Victim reported cyber fraud loss of INR 50,000", "source": "NCRP_1930" },
    { "timestamp": "2026-08-25T17:20:00Z", "type": "TRANSACTION", "description": "IMPS transfer of INR 50,000 to ACC_001", "source": "BANK_LOG" },
    { "timestamp": "2026-08-25T17:45:00Z", "type": "ATM_PREDICTION", "description": "Predicted withdrawal at ATM_9981 (Mumbai) in 3-6h window", "source": "CIRIS_ML_V4" },
    { "timestamp": "2026-08-25T18:00:00Z", "type": "INTERVENTION", "description": "Recommended HOLD REVIEW for INR 15,000 remaining on ACC_001", "source": "CIRIS_ENGINE" }
  ],
  "intervention": {
    "recommended_action": "HOLD REVIEW",
    "confidence_score": 0.88,
    "action_rationale": "High fused risk score (0.88) with INR 15,000 remaining unwithdrawn balance in mule account ACC_001.",
    "potential_hold_amount": 15000.0,
    "authorization_boundary": "Authorized Bank / LEA Officer Review Required",
    "target_accounts_for_review": ["ACC_001"]
  },
  "audit_events": [
    { "event_id": "EVT_001", "event_type": "CASE_CREATED", "actor": "SYSTEM", "timestamp": "2026-08-25T18:00:00Z" }
  ]
}
```

---

## Field Dictionary & Status Matrix

### Case Statuses:
- `NEW`: Complaint received, pending pipeline analysis.
- `ANALYZING`: Pipeline active.
- `REVIEW`: Analysis complete, awaiting officer decision.
- `ESCALATED`: Escalated for LEA ground intervention or bank lien.
- `RESOLVED`: Action completed.
- `CLOSED`: Case archived.

### Priorities:
- `P1`: Disputed amount > INR 100,000 OR High Fused Risk > 0.80 OR Active ATM Window < 3h.
- `P2`: Medium-high risk (0.60 - 0.80) or amount > INR 25,000.
- `P3`: Medium risk (0.40 - 0.60).
- `P4`: Low risk (< 0.40).

### Intervention Recommendations:
- `HOLD REVIEW`: Immediate recommendation to review account balance hold.
- `MONITOR`: Monitor account transaction activity.
- `INVESTIGATE`: Flag for investigator deep dive.
- `ESCALATE`: Priority dispatch to LEA ground unit.

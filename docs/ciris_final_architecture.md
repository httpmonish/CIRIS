# CIRIS — Final System Architecture & Data Flow

## System Overview
**CIRIS** (Smart India Hackathon 2026 Edition) is a proactive financial cybercrime intelligence platform. It reconstructs suspicious money flows, connects related entities and transactions, identifies mule network behavior, traces disputed funds, calculates amounts at risk, predicts actionable cashout/spending endpoints, and produces explainable intervention recommendations for authorized law enforcement and bank fraud investigators.

---

## High-Level Architecture Diagram

```
                              FRAUD COMPLAINT
                                     │
                                     ▼
                             CASE CREATION & LOGGING
                                     │
                                     ▼
                     DATA NORMALIZATION & DATASET LOADER
                                     │
                                     ▼
                      ENTITY RESOLUTION ENGINE (Tier 1/2)
                                     │
                                     ▼
             TRANSACTION CORRELATION & MONEY-FLOW GRAPH ENGINE
                                     │
                                     ▼
             TRANSACTION FRAGMENTATION & SPLITTING DETECTOR
                                     │
                                     ▼
               MULE NETWORK INTELLIGENCE & RISK SCORER
                                     │
                                     ▼
                   AMOUNT-AT-RISK ACCOUNTING ENGINE
                                     │
                                     ▼
                      ENDPOINT-TYPE CLASSIFIER
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
    ATM ENDPOINT              MERCHANT ENDPOINT         ONWARD TRANSFER
  (Preserved ML V4           (POS / E-Commerce        (Inter-Bank Network
  LambdaMART Ranker,          Spend Assessment)        Layering Assessment)
  Time Predictor, Anomaly)           │                         │
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │
                                     ▼
                MULTI-SIGNAL FUSION & PROBABILITY CALIBRATION
                                     │
                                     ▼
                SHAP EXPLAINABILITY & GRAPH EVIDENCE BRIEFING
                                     │
                                     ▼
              INTERVENTION RECOMMENDATION ENGINE (HOLD REVIEW / ESCALATE)
                                     │
                                     ▼
                         INVESTIGATOR DASHBOARD
                                     │
                                     ▼
                    AUTHORIZED BANK / LEA ACTION & OUTCOME
```

---

## 14 Core Component Pipeline Summary

1. **Complaint Payload & Data Contracts**: Validates Pydantic schemas, victim locations, loss amounts, and timestamps.
2. **Entity Resolution Engine**: Maps identity trees across Person ↔ Account ↔ Card ↔ UPI ↔ Mobile ↔ Device with strict field availability tiering.
3. **Point-in-Time Temporal Filtering**: Enforces zero temporal lookahead leakage ($t \le T_{\text{complaint}}$).
4. **Money-Flow Graph Engine**: Extracts multi-hop directed subgraphs, tracing funds through intermediate nodes to final endpoints.
5. **Transaction Fragmentation Detector**: Flags smurfing, fan-out splitting, and micro-transaction velocity bursts.
6. **Mule Network Intelligence**: Computes objective mule candidate risk scores, cluster sizes, and evidence tags without non-adjudicated labels.
7. **Amount-at-Risk Engine**: Provides deterministic accounting (Disputed, Moved, Remaining, Unresolved) for hold recommendations.
8. **Endpoint Type Classifier**: Evaluates destination channel probabilities (ATM vs Merchant vs Transfer).
9. **Preserved ATM Candidate Retrieval (Stage 0)**: BallTree Spatial Index + Historical Hotspot Cache + Temporal Graph Walk ($86\%$ Candidate Pool Recall).
10. **Preserved Supervised ATM Ranker (Stage 2)**: LightGBM LambdaMART ranker optimized for NDCG across 5,000 ATMs.
11. **Preserved Time-to-Cashout Predictor (Stage 3)**: Dual-head GBDT time model ($\text{MAE} = 4.80\text{h}$) and LEA dispatch window classifier.
12. **Preserved Unsupervised Anomaly Engine (Stage 4)**: Isolation Forest anomaly scoring.
13. **Preserved Fusion & Platt Calibration (Stage 5)**: Multi-signal risk fusion meta-model and Platt scaling calibrator.
14. **Explainability & Intervention Routing (Stage 6)**: TreeSHAP local feature attributions, natural-language briefing generator, and calibrated intervention recommendation (HOLD REVIEW / ESCALATE).

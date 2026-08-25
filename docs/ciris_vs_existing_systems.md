# CIRIS vs. Existing Systems — Comprehensive Comparison

## Overview
This document compares CIRIS (Predictive Cybercrime Analytics & Financial Intelligence System) against existing industry systems across financial fraud detection, AML, cybercrime reporting, and graph visualization.

---

## Comparative Analysis Matrix

| System Category | Existing Systems Example | Primary Function | Key Limitations | CIRIS Strategic Value-Add |
|---|---|---|---|---|
| **Cybercrime Reporting Portals** | National Cyber Crime Reporting Portal (NCRP 1930) | Victim complaint reporting, manual helpline routing, static complaint logging. | Reactive logging; manual dispatch; limited real-time predictive capabilities for physical cashouts. | **Proactive Predictive Layer**: Ingests NCRP complaint streams, automatically constructs temporal money-flow graphs, and predicts upcoming cashout endpoints. |
| **Bank Transaction Monitoring (TMS)** | Actimize, Oracle Financial Services Analytical Applications (OFSAA), NetReveal | Real-time rule evaluation on single bank transactions. | Siloed within individual banks; high false-positive rate; rule evasion by fraudsters through micro-splitting. | **Cross-Bank Entity Resolution & Fragmentation Detection**: Unifies multi-bank UPI/IMPS flows, detects micro-fragmentation across accounts, and tracks mule clusters. |
| **Standard ML Fraud Detectors** | Supervised Random Forest / XGBoost transaction classifiers | Binary fraud classification (Fraud vs Licit) on individual transactions. | Single-transaction focus; no spatial candidate ranking; unable to predict physical location or temporal delay. | **Multi-Stage Ranking & Spatial Candidate Engine**: Combines spatial BallTree indexing, historical hotspot caching, LambdaMART candidate ranking, and time prediction. |
| **Graph Visualization Tools** | Maltego, IBM i2 Analyst's Notebook, Linkurious | Manual visual rendering of nodes and edges for crime analysts. | Manual layout; non-predictive; requires human investigator to manually trace paths line-by-line. | **Automated Money-Flow Graph Engine**: Automatically computes k-hop traversals, connected component risk, mule centralities, and graph evidence attributions. |
| **Account Freezing & Lien Modules** | Bank CBS Risk Engines / Enforcement Portals | Hard automated account locking or placing liens on specific accounts. | Cannot act across unflagged intermediate accounts; lacks contextual amount-at-risk accounting. | **Amount-at-Risk Accounting & Intervention Workflow**: Calculates exact moved vs remaining disputed funds and recommends calibrated interventions (HOLD REVIEW, ESCALATE). |
| **Mule Account Risk Scorer** | Specialized vendor mule scoring APIs | Single-account propensity score for mule likelihood. | Static account-level score; does not trace specific disputed funds from a victim complaint to a physical cashout. | **Integrated Case-Level Mule Intelligence**: Connects mule entity risk to specific disputed funds, fragmentation events, and candidate endpoints. |

---

## Detailed Architectural Positioning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXISTING ECOSYSTEM LANDSCAPE                          │
│                                                                             │
│  [NCRP 1930 Portal]     [Bank A TMS]     [Bank B TMS]     [i2 Graph Tool]  │
│  (Static Complaint)     (Siloed Rules)   (Siloed Rules)   (Manual Visual)   │
└───────────────────────┬────────────────┬────────────────┬───────────────────┘
                        │                │                │
                        ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CIRIS UNIFIED ENGINE                             │
│                                                                             │
│  1. Cross-Entity Resolution (Person ↔ Account ↔ Card ↔ UPI ↔ Device)       │
│  2. Multi-Hop Money-Flow Graph Engine (k-hop, time-bounded subgraphs)       │
│  3. Transaction Fragmentation & Splitting Detector                           │
│  4. Mule Network Intelligence & Risk Scoring                                │
│  5. Amount-at-Risk Accounting Engine                                        │
│  6. Multi-Endpoint Classifier (ATM / Merchant / Transfer)                   │
│  7. Preserved ATM ML V4 Candidate Ranker & Time Predictor                   │
│  8. Explainable Intervention Recommendation (HOLD REVIEW / ESCALATE)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Summary of Synthesis

CIRIS does **not** compete with or attempt to replace existing core banking or cybercrime reporting systems. Instead, CIRIS acts as an **intelligent cybercrime analytics and endpoint prediction engine** that ingests inputs from existing reporting portals and bank transaction streams, performs cross-entity and multi-hop graph intelligence, and feeds actionable, explainable intervention recommendations back to authorized law enforcement agencies (LEA) and bank fraud control units.

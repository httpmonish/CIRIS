# CIRIS — SIH 2026 Requirement Mapping Matrix

## Official SIH Problem Statement Core Requirements

| SIH Requirement | Current Implementation (ML V4) | Required Enhancement | Validation Evidence | Status |
|---|---|---|---|---|
| **1. Cash-out Location & ATM Prediction** | 5,000 ATM candidate retrieval (BallTree + Hotspot + Mule Graph) + LightGBM LambdaMART ranker. | Preserve ATM ML V4 as primary ATM Endpoint Intelligence Module. Add Endpoint Classifier for non-ATM routes. | `tests/test_stage_2.py`, `docs/final_v2_e2e_validation.md` | ✅ GREEN |
| **2. Time-to-Cashout Window Estimation** | Dual-head GBDT time model (continuous delay + 5-class LEA window). MAE = 4.80h. | Integrate time window estimation with case intelligence object and intervention alerts. | `tests/test_stage_3.py`, `docs/final_training_report.md` | ✅ GREEN |
| **3. Mule Account & Network Pattern Tracing** | 2-hop account degree, case links, and graph edge lookup in `TemporalGraphEngine`. | Upgrade to generalized financial relationship graph with k-hop tracing, fragmentation detection, & entity resolution. | `src/ml/retrieval/money_flow_graph.py`, `docs/money_flow_graph_engine.md` | 🟡 ENHANCING |
| **4. Point-in-Time Historical Compliance** | Strict $t \le T_{\text{complaint}}$ temporal filtering across all 43 feature columns and retrieval engines. | Enforce point-in-time safety on new fragmentation, mule risk, and amount-at-risk engines (0 leakage). | `tests/test_stage_minus_1.py`, `docs/leakage_audit.md` | ✅ GREEN |
| **5. Unsupervised Anomaly Detection** | Isolation Forest anomaly scorer on complaint & victim transaction velocity. | Combine anomaly sub-scores with entity resolution & fragmentation features. | `tests/test_stage_4.py`, `docs/final_ml_validation.md` | ✅ GREEN |
| **6. Probability Calibration & Risk Fusion** | Platt scaling probability calibrator (Brier Score 0.002039) + multi-signal fusion meta-model. | Expand fusion engine to integrate Endpoint Type, Mule Risk, and Amount at Risk. | `tests/test_stage_5.py`, `docs/final_v2_scorecard.md` | ✅ GREEN |
| **7. Explainability & LEA Actionability** | TreeSHAP local feature attributions + natural-language field officer briefing generator. | Add graph evidence, money-flow path visualization, and intervention recommendations. | `tests/test_stage_6.py`, `src/ml/xai/explainer.py` | ✅ GREEN |
| **8. Real-Time Operational Latency (<15s SLA)** | Pipeline E2E Latency P50 = 2,145 ms (~2.15s), P95 = 3,051 ms. | Maintain vectorized calculation loops, spatial indexing, and group-by caches to ensure P95 < 5,000 ms. | `docs/e2e_100_case_benchmark.md` | ✅ GREEN |

---

## SIH Requirement Preservation Guarantee

The core objective of SIH 2026 — **intercepting financial cyber fraud at cashout endpoints** — remains 100% central to CIRIS. The ATM Prediction Engine is not removed, simplified, or diluted. It serves as the **deepest predictive endpoint model** within the expanded financial cybercrime intelligence system.

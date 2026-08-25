# CIRIS — Predictive Cybercrime Analytics & ATM Cashout Interception System

> [!NOTE]
> **SUPERSEDED / SINGLE SOURCE OF TRUTH NOTICE**:
> For current authoritative numbers, see [docs/ciris_final_honest_scorecard.md](file:///e:/CIRIS-SIH2026/docs/ciris_final_honest_scorecard.md). For complete metric evolution history, see [docs/metrics_changelog.md](file:///e:/CIRIS-SIH2026/docs/metrics_changelog.md).

**CIRIS** (Smart India Hackathon 2026 Edition) is a predictive cybercrime intelligence platform engineered to trace, analyze, and intercept high-velocity financial cyber fraud (UPI scams, digital arrest, phishing, investment fraud) across multi-hop mule networks and ATM cashout endpoints.

---

## 🚀 Key Highlights & Architecture

CIRIS implements a multi-stage predictive intelligence pipeline and multi-layer case intelligence architecture trained on **11,932,605 ranking instances**:

### 1. Predictive ATM Ranking Pipeline
- **Stage -1: Data Contracts & Partitioning** — Strict temporal boundaries ($t \le T_{\text{complaint}}$) with zero temporal lookahead leakage.
- **Stage 0: Hybrid Candidate Retrieval Engine** — BallTree Geospatial Search ($250\text{ km}$ / $200\text{-kNN}$) + Historical Hotspot Cache (Top-1500) + Temporal Mule Graph Multi-Hop Walk ($86.00\%$ Candidate Pool Recall).
- **Stage 1: 43-Column Point-in-Time Feature Pipeline** — Spatial proximity, decayed historical cashout rates, account velocity, and graph centrality.
- **Stage 2: ATM Candidate Ranking** — LightGBM LambdaMART ranker optimized for NDCG across national ATMs.
- **Stage 3: Time-to-Cashout Prediction** — Dual-head gradient boosted continuous delay regressor ($\text{MAE} = 4.95\text{h}$) and 5-class Law Enforcement Agency dispatch window classifier.
- **Stage 4: Unsupervised Anomaly Detection** — Isolation Forest anomaly scoring engine identifying high-risk mule behavior.
- **Stage 5: Probability Calibration & Risk Fusion** — Platt scaling calibrator ($\text{Brier Score} = 0.002039$) and multi-signal meta-fusion engine.
- **Stage 6: TreeSHAP Explainability & Graph Tracing** — Audit-grade local feature attributions and automated Law Enforcement Agency narrative briefing generation.

### 2. Multi-Layer Case Intelligence Suite
Tested & verified via automated unit test suite [`tests/test_case_intelligence_e2e.py`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py):

| Intelligence Engine | Implementation Source | Unit Test Link | Status & Verification |
|---|---|---|:---:|
| **Entity Resolution Engine** | [`src/ml/features/entity_resolution.py`](file:///e:/CIRIS-SIH2026/src/ml/features/entity_resolution.py) | [`test_entity_resolution`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L59) | ✅ Verified |
| **Money-Flow Graph Engine** | [`src/ml/retrieval/money_flow_graph.py`](file:///e:/CIRIS-SIH2026/src/ml/retrieval/money_flow_graph.py) | [`test_money_flow_graph`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L71) | ✅ Verified |
| **Transaction Fragmentation Detector** | [`src/ml/features/fragmentation_detector.py`](file:///e:/CIRIS-SIH2026/src/ml/features/fragmentation_detector.py) | [`test_fragmentation_detector`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L85) | ✅ Verified |
| **Mule Network Intelligence** | [`src/ml/models/mule_network.py`](file:///e:/CIRIS-SIH2026/src/ml/models/mule_network.py) | [`test_mule_network_intelligence`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L95) | ✅ Verified |
| **Amount-at-Risk Engine** | [`src/ml/features/amount_at_risk.py`](file:///e:/CIRIS-SIH2026/src/ml/features/amount_at_risk.py) | [`test_amount_at_risk_engine`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L113) | ✅ Verified |
| **Endpoint Type Classifier** | [`src/ml/routing/endpoint_classifier.py`](file:///e:/CIRIS-SIH2026/src/ml/routing/endpoint_classifier.py) | [`test_endpoint_classifier`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L124) | ✅ Verified |
| **Intervention Workflow Engine** | [`src/ml/routing/intervention.py`](file:///e:/CIRIS-SIH2026/src/ml/routing/intervention.py) | [`test_intervention_recommendation`](file:///e:/CIRIS-SIH2026/tests/test_case_intelligence_e2e.py#L138) | ✅ Verified |

---

## 📊 Performance Scorecard & Benchmark Summary

### 1. Absolute Live Dynamic End-to-End Comparison (100 Cases)

> [!NOTE]
> **Zero-Lift Rule**: Per the Master Hardening Audit, percentage "lift" multipliers against near-zero baselines are eliminated. Baseline and CIRIS ML V4 metrics are reported side-by-side in absolute terms.

| Model / Baseline | Candidate Pool Recall | Hit@1 | Hit@5 | Hit@10 | NDCG@10 | MRR | E2E Latency P50 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nearest ATM (Geospatial Only)** | — | 0.00% | 0.00% | 1.00% | N/A | N/A | < 10 ms |
| **Pure Historical Hotspot Heuristic** | Top 1500 Hotspots | 0.00% | 1.00% | 1.00% | N/A | N/A | < 10 ms |
| **SKYVAR Baseline (SIH 2025)** | Distance + Density | 0.00% | 0.00% | 0.00% | N/A | N/A | < 50 ms |
| **CIRIS / CIPHER ML V4** | **86.00%** | **3.00%** | **27.00%** | **46.00%** | **0.2117** | **0.1444** | **2.15s (2,145ms)** |

### 2. Untouched Test Set Performance (1,973,305 Ranking Pairs)

| Metric | Validation Set (1.94M rows) | Untouched Test Set (1.97M rows) | Status |
| :--- | :---: | :---: | :---: |
| **NDCG@1** | 0.3365 | **0.3314** | ✅ Generalization Verified |
| **NDCG@5** | 0.4280 | **0.4151** | ✅ Generalization Verified |
| **NDCG@10** | 0.4736 | **0.4584** | ✅ Generalization Verified |
| **Mean Reciprocal Rank (MRR)** | 0.4280 | **0.4164** | ✅ Generalization Verified |
| **HitRate@10** | 66.12% | **63.61%** | ✅ Generalization Verified |
| **Brier Score (Calibration)** | 0.002071 | **0.002039** | ✅ Honest Probability Estimates |
| **Time Model MAE** | 4.80 Hours | **4.95 Hours** | ✅ Actionable Time Windows |

### 3. Optimized Operational Latency Profile (P50 / P95)

- **Candidate Retrieval P50**: `170.26 ms` (P95: `455.80 ms`)
- **Feature Pipeline P50**: `1,411.73 ms` (P95: `2,158.97 ms`) — Vectorized GroupBy & Fast Graph Extraction
- **Ranker Inference P50**: `36.17 ms` (P95: `54.96 ms`)
- **Multi-Signal Fusion & Evidence P50**: `427.54 ms` (P95: `756.32 ms`)
- **Total Pipeline E2E Latency P50**: **2,145.50 ms (~2.15s)** (P95: `3,051.43 ms` — well within the 15-second operational SLA).

---

## 📁 Repository Structure

```
├── models/final_v2/          # Production Versioned Serialized ML Artifacts (v2)
├── src/ml/                   # CIRIS ML V4 Core Engine & Case Intelligence
│   ├── contracts/            # Schemas, Complaint Payload, Case Intelligence Objects
│   ├── data/                 # Canonical DatasetLoader & integrity audit engine
│   ├── features/             # FeatureBuilder, Entity Resolution, Fragmentation, Amount-at-Risk
│   ├── models/               # LambdaRanker, TimePredictor, AnomalyDetector, Mule Network, RiskFusion
│   ├── retrieval/            # SpatialIndex BallTree, HotspotCache, TemporalGraphEngine, CandidateRetriever
│   ├── routing/              # EndpointTypeClassifier, InterventionRecommendationEngine
│   └── xai/                  # TreeSHAP explainer & narrative briefing engine
├── docs/                     # Documentation & Authoritative Scorecards
│   ├── ciris_final_honest_scorecard.md  (SINGLE SOURCE OF TRUTH SCORECARD)
│   └── metrics_changelog.md              (APPEND-ONLY METRICS HISTORICAL LOG)
└── tests/                    # Automated Pytest regression test suite
```

---

## 🧪 Testing & Verification

Run the full automated test suite:

```bash
python -m pytest tests/ -v
```

---

## 📄 Authoritative Documentation & Audit Logs

- [Final Honest Performance Scorecard](docs/ciris_final_honest_scorecard.md) — **Single Source of Truth**
- [Metrics Historical Changelog](docs/metrics_changelog.md) — **Append-Only Evolution Log**
- [Release Readiness Assessment](docs/ciris_release_readiness.md)
- [Public Dataset Audit](docs/public_dataset_audit.md)

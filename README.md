# CIRIS — Predictive Cybercrime Analytics & ATM Cashout Interception System

**CIRIS** (Smart India Hackathon 2026 Edition) is a state-of-the-art predictive cybercrime intelligence platform engineered to intercept high-velocity financial cyber fraud (UPI scams, digital arrest, phishing, investment fraud) at ATMs before cashouts occur.

---

## 🚀 Key Highlights & Architecture

CIRIS ML V4 implements a point-in-time compliant, multi-stage predictive intelligence pipeline trained on **11,932,605 ranking instances**:

- **Stage -1: Data Contracts & Partitioning** — Strict temporal boundaries ($t \le T_{\text{complaint}}$) with zero temporal lookahead leakage.
- **Stage 0: Hybrid Candidate Retrieval Engine** — BallTree Geospatial Search ($100\text{ km}$ / $100\text{-kNN}$) + Historical Hotspot Cache (Top-100) + Temporal Mule Graph Multi-Hop Walk ($80.00\%$ Candidate Pool Recall).
- **Stage 1: 43-Column Point-in-Time Feature Pipeline** — Spatial proximity, decayed historical cashout rates, account velocity, and graph centrality.
- **Stage 2: ATM Candidate Ranking** — LightGBM LambdaMART ranker optimized for NDCG across 5,000 national ATMs.
- **Stage 3: Time-to-Cashout Prediction** — Dual-head gradient boosted continuous delay regressor ($\text{MAE} = 4.80\text{h}$) and 5-class Law Enforcement Agency dispatch window classifier.
- **Stage 4: Unsupervised Anomaly Detection** — Isolation Forest anomaly scoring engine identifying high-risk mule behavior.
- **Stage 5: Probability Calibration & Multi-Signal Risk Fusion** — Platt scaling calibrator ($\text{Brier Score} = 0.002039$) and multi-signal meta-fusion engine.
- **Stage 6: TreeSHAP Explainability & Graph Tracing** — Audit-grade local feature attributions and automated Law Enforcement Agency narrative briefing generation.

---

## 📊 Final Performance Scorecard & Benchmark

### 1. True Live Dynamic End-to-End Benchmark (Without True ATM Injection)

Evaluated across dynamic holdout complaint scenarios with ground-truth blind multi-channel candidate retrieval:

| Benchmark / Model | Candidate Pool Recall | Hit@1 | Hit@5 | Hit@10 | NDCG@10 | MRR | E2E Latency P50 | Relative Lift vs SIH 2025 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nearest ATM (Geospatial Only)** | — | 0.00% | 0.00% | 1.00% | N/A | N/A | < 10 ms | +1.0x |
| **Pure Historical Hotspot Heuristic** | Top 1500 Hotspots | 0.00% | 1.00% | 1.00% | N/A | N/A | < 10 ms | +1.0x |
| **SKYVAR Baseline (SIH 2025)** | Distance + Density | 0.00% | 0.00% | 0.00% | N/A | N/A | < 50 ms | Baseline (0.0x) |
| **CIRIS / CIPHER ML V4 (v2 Benchmark - 100 Cases)** | **86.00%** | **3.00%** | **27.00%** | **46.00%** | **0.2117** | **0.1444** | **2.15s (2,145ms)** | **+4,600% Lift (46.0x)** |

### 2. Untouched Test Set Performance (1,973,305 Ranking Pairs)

| Metric | Validation Set (1.94M rows) | Untouched Test Set (1.97M rows) | Status |
| :--- | :---: | :---: | :---: |
| **NDCG@1** | 0.3365 | **0.3314** | ✅ Robust Generalization |
| **NDCG@5** | 0.4280 | **0.4151** | ✅ Robust Generalization |
| **NDCG@10** | 0.4736 | **0.4584** | ✅ Robust Generalization |
| **Mean Reciprocal Rank (MRR)** | 0.4280 | **0.4164** | ✅ High Precision |
| **HitRate@10** | 66.12% | **63.61%** | ✅ Substantial Discriminative Power |
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
│   ├── location_ranker.joblib      (LightGBM LambdaMART ranker bundle)
│   ├── time_predictor.joblib       (Dual-head gradient boosted time model)
│   ├── anomaly_detector.joblib     (Isolation Forest anomaly engine)
│   ├── fusion_engine.joblib        (Multi-signal risk fusion meta-model)
│   ├── calibrator.joblib           (Platt scaling probability calibrator)
│   ├── offline_metadata.joblib     (Spatial index BallTree, Graph tables, Hotspot cache)
│   ├── feature_schema.json         (43-column strict feature contract)
│   ├── metrics.json                (Automated training & validation metrics)
│   └── test_e2e_evaluation_results.json (Untouched test split & 100-case dynamic benchmark results)
├── src/ml/                   # CIRIS ML V4 Core Engine
│   ├── contracts/            # Data payloads & Pydantic schemas
│   ├── data/                 # Canonical DatasetLoader & integrity audit engine
│   ├── features/             # Vectorized point-in-time feature engineering
│   ├── models/               # LambdaRanker, TimePredictor, AnomalyDetector, RiskFusion
│   ├── retrieval/            # SpatialIndex BallTree, HotspotCache, CandidateRetriever
│   ├── routing/              # Operational guardrails & LEA/Bank dispatch routing
│   ├── training/             # Full-scale multi-stage training orchestrator
│   ├── evaluation/           # Live E2E dynamic benchmark & baseline evaluator
│   └── xai/                  # TreeSHAP explainer & narrative briefing engine
├── docs/                     # System architecture & validation reports
│   ├── e2e_evaluation_performance_audit.md
│   ├── e2e_100_case_benchmark.md
│   ├── final_v2_e2e_validation.md
│   └── final_v2_scorecard.md
└── tests/                    # Passing Pytest regression test suite
```

---

## 🧪 Testing & Verification

Run the full automated test suite:

```bash
python -m pytest tests/ -v
```

---

## 📄 Comprehensive Documentation

- [Evaluator Performance Audit](docs/e2e_evaluation_performance_audit.md)
- [100-Case Dynamic E2E System Benchmark](docs/e2e_100_case_benchmark.md)
- [Final V2 End-to-End Validation](docs/final_v2_e2e_validation.md)
- [Final V2 Model Scorecard](docs/final_v2_scorecard.md)


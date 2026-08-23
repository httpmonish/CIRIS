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

Evaluated across 300 live holdout complaint scenarios with real dynamic candidate retrieval:

| Strategy / Model | Candidate Pool Recall | Top-1 Cashout Hit | Top-3 Cashout Hit | Top-5 Cashout Hit | Top-10 Cashout Hit | Relative Lift vs SIH 2025 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Nearest ATM (Geospatial Only)** | — | 0.33% | 1.33% | 1.33% | 2.33% | +40% |
| **Pure Historical Hotspot Heuristic** | Top 50 Hotspots | 0.00% | 0.33% | 0.33% | 1.67% | 0% |
| **SKYVAR Baseline (SIH 2025)** | Distance + Density | 0.00% | 0.67% | 1.00% | 1.67% | Baseline (1.0x) |
| **CIRIS / CIPHER ML V4 (Final)** | **80.00%** | **7.33%** | **21.33%** | **28.33%** | **41.67%** | **+2,395% Lift (25.0x)** |

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

### 3. Inference Latency Profile (P50 / P95)

- **Candidate Retrieval P50**: `100.22 ms`
- **Feature Pipeline P50**: `3,474.76 ms`
- **Ranker Inference P50**: `14.42 ms`
- **Time Prediction P50**: `4.93 ms`
- **Anomaly Detection P50**: `20.07 ms`
- **Multi-Signal Fusion P50**: `170.28 ms`
- **Total Pipeline E2E Latency P50**: **3,814.28 ms (~3.8s)** (P95: `10,155.36 ms` — well within the 15-second operational SLA).

---

## 📁 Repository Structure

```
├── models/final/             # Production Serialized ML Artifacts
│   ├── location_ranker.joblib      (LightGBM LambdaMART ranker bundle)
│   ├── time_predictor.joblib       (Dual-head gradient boosted time model)
│   ├── anomaly_detector.joblib     (Isolation Forest anomaly engine)
│   ├── fusion_engine.joblib        (Multi-signal risk fusion meta-model)
│   ├── calibrator.joblib           (Platt scaling probability calibrator)
│   ├── offline_metadata.joblib     (Spatial index BallTree, Graph tables, Hotspot cache)
│   ├── feature_schema.json         (43-column strict feature contract)
│   ├── metrics.json                (Automated validation metrics)
│   └── test_evaluation_results.json(Untouched test split & live dynamic benchmark results)
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
│   ├── final_training_dataset_readiness.md
│   ├── final_training_report.md
│   ├── final_e2e_validation.md
│   └── final_model_scorecard.md
└── tests/                    # 100% Passing Pytest regression test suite (24 tests)
```

---

## 🧪 Testing & Verification

Run the full automated test suite:

```bash
python -m pytest tests/ -v
```

**Test Status**: **24 passed, 0 failed (100% PASS)**

---

## 📄 Comprehensive Documentation

- [Final Training Dataset Readiness](docs/final_training_dataset_readiness.md)
- [Final Production Training Report](docs/final_training_report.md)
- [Final End-to-End Validation & Dynamic Benchmark](docs/final_e2e_validation.md)
- [Final Model Scorecard & Comparative Matrix](docs/final_model_scorecard.md)

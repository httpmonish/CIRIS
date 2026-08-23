# CIRIS — Predictive Cybercrime Analytics & ATM Cashout Interception System

**CIRIS** (SIH 2026 Edition) is an advanced predictive cybercrime analytics platform engineered to intercept cyber fraud financial cashouts at ATMs before withdrawals occur.

---

## 🚀 Key Highlights & Architecture

CIRIS ML V4 implements a point-in-time compliant, multi-stage predictive pipeline:

- **Stage -1**: Temporal Data Partitioning & Ground Truth Mapping
- **Stage 0**: Multi-Strategy Candidate ATM Retrieval Engine (Geospatial $100\text{ km}$, KNN-100, Hotspots-100, Mule Graph & Admin District Fallback)
- **Stage 1**: 36-Feature Point-in-Time Feature Engineering ($t < T$ Zero Leakage)
- **Stage 2**: ATM Candidate Ranking via LightGBM LambdaRank
- **Stage 3**: Time-to-Cashout Prediction (HistGBR Model)
- **Stage 4**: Isolation Forest Unsupervised Anomaly Detection
- **Stage 5**: Probability Calibration (Isotonic / Platt) & Multi-Signal Risk Fusion
- **Stage 6**: TreeSHAP Explainability & Temporal Graph Evidence Tracing

---

## 📊 Performance Scorecard vs Legacy V1 Baseline

| Metric | Legacy V1 Baseline | CIRIS ML V4 | Improvement |
| :--- | :---: | :---: | :---: |
| **Candidate Retrieval Recall** | 89.68% | **95.24%** | **+5.56%** |
| **End-to-End HitRate@5** | 11.90% | **17.46%** | **+5.56%** |
| **End-to-End HitRate@10** | 22.22% | **34.13%** | **+11.91% (1.5x)** |
| **End-to-End NDCG@10** | 0.1109 | **0.1685** | **+0.0576** |
| **End-to-End MRR** | 0.1071 | **0.1492** | **+0.0421** |
| **Average Latency** | 45.2 ms | **34.8 ms** | **-10.4 ms** |

---

## 📁 Repository Structure

```
├── src/ml/                   # CIRIS ML V4 Core Engine
│   ├── contracts/            # Data payloads & Pydantic schemas
│   ├── features/             # 36-feature point-in-time builder
│   ├── models/               # LambdaRanker, TimePredictor, AnomalyDetector, RiskFusion
│   ├── retrieval/            # SpatialIndex, HotspotCache, CandidateRetriever
│   ├── routing/              # Operational guardrails & risk policies
│   └── xai/                  # TreeSHAP explainer & graph tracing
├── docs/                     # System architecture & audit reports
├── datasets/                 # Development dataset & synthetic generation scripts
└── tests/                    # 100% Passing Pytest regression suite (18 tests)
```

---

## 🧪 Testing & Verification

Run the full automated test suite:

```bash
python -m pytest tests/
```

---

## 📄 Documentation Reports

- [Pre-Optimization Baseline](docs/cipher_v4_pre_optimization_baseline.md)
- [Retrieval Failure Mode Analysis](docs/candidate_retrieval_failure_analysis.md)
- [Retrieval Optimization Results](docs/retrieval_optimization_results.md)
- [Point-in-Time Feature Regression Audit](docs/feature_regression_audit.md)
- [Final Scorecard & Verification Certificate](docs/final_cipher_v4_scorecard.md)

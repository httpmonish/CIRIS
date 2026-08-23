# CIPHER-X v4 Pre-Optimization Baseline Benchmark Document

**Freeze Timestamp**: 2026-08-23  
**Target Repository**: `CIRIS-SIH2026`  
**Configuration Tag**: `CIPHER_V4_PRE_OPTIMIZATION_BASELINE`  

---

## 1. System Configuration Snapshot

- **Feature Schema**: 36 Point-in-Time Features (`FeatureBuilder.FEATURE_COLUMNS`)
- **Candidate Retriever Configuration**:
  - `geo_radius_km`: 50.0 km
  - `geo_fallback_knn`: 50 ATMs
  - `top_hotspots_count`: 50 ATMs
  - `graph_engine`: NetworkX $G_T$ Ego-Subgraphs as of prediction timestamp $T$
- **ATM Ranker Model**: LightGBM LambdaMART Ranker (`objective="lambdarank"`, `n_estimators=100`, `learning_rate=0.08`)
- **Time Model**: LightGBM Regressor (`withdrawal_delay_hours`) + LightGBM 5-Class Window Classifier
- **Anomaly Model**: Isolation Forest (`n_estimators=100`, `contamination=0.10`)
- **Probability Calibrator**: Platt Scaling Logistic Regressor fit on Validation Set
- **Risk Fusion Engine**: Multi-signal linear fusion ($\alpha=0.50, \beta=0.20, \gamma=0.15, \delta=0.15$)

---

## 2. Benchmark Metrics (126 Untouched Chronological Test Complaints)

### A. Candidate Retrieval Performance (Zero Forced Insertion)
- **Candidate Union Recall**: **89.68% (113 / 126)**
- **Missed-Retrieval Count**: **13 / 126 (10.32%)**
- **Average Candidate Count**: **105.95 ATMs / 400 ATMs** (**73.5% Search Space Reduction**)
- **Average Retrieval Latency**: **1.42 ms / complaint**

### B. True End-to-End Ranking Metrics (Strict Miss Penalty)
- **HitRate@1**: **3.97% (5 / 126)**
- **HitRate@5**: **11.90% (15 / 126)**
- **HitRate@10**: **22.22% (28 / 126)**
- **NDCG@5**: **0.0844**
- **NDCG@10**: **0.1109**
- **MRR**: **0.1071**
- **Median Geographic Error**: **470.52 km**
- **P90 Geographic Error**: **1174.32 km**

### C. Calibration & Time Model Metrics
- **Test Brier Score**: `0.00963`
- **Time Model MAE**: `3.83 hours`
- **Time Window Accuracy**: `30.16%` (Macro F1: `0.2610`)
- **Causal Lead Time Violations**: **0 / 126 (100% Causal Lead Time Guaranteed, Median Lead: 3.94h)**

---

## 3. Comparison Against Legacy Baseline

| Metric | Legacy Baseline (Exhaustive 400 ATMs) | CIPHER ML V4 Baseline (Pre-Optimization) | Status |
| :--- | :---: | :---: | :--- |
| **Search Space Size** | 400 ATMs | **105.95 ATMs** | **73.5% Computation Reduction** |
| **HitRate@1** | **5.56%** | 3.97% | -1.59% (Impacted by 13 Retrieval Misses) |
| **HitRate@5** | 11.11% | **11.90%** | **+0.79% Better** |
| **HitRate@10** | 21.43% | **22.22%** | **+0.79% Better** |
| **NDCG@5** | 0.0829 | **0.0844** | **+0.0015 Better** |
| **NDCG@10** | **0.1169** | 0.1109 | -0.0060 |
| **MRR** | **0.1156** | 0.1071 | -0.0085 |
| **P90 Geographic Error** | 1313.72 km | **1174.32 km** | **139.4 km Closer** |

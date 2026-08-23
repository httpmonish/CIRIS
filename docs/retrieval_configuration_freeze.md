# CIRIS / CIPHER ML V4 — Production Candidate Retrieval Configuration Freeze

**Freeze Date**: 2026-08-23T22:04:00  
**Target Subsystem**: Stage 0 Dynamic Candidate ATM Retrieval Engine (`src/ml/retrieval/candidate_retriever.py` & `src/ml/pipeline.py`)  
**Status**: **FROZEN & VERIFIED**  

---

## 1. Frozen Production Configuration (Configuration K2: Hybrid High-Recall)

The empirical validation study documented in `docs/retrieval_validation_optimization.md` demonstrated that Configuration K2 provides the optimal balance of high recall, sub-millisecond retrieval speed, and manageable downstream candidate pool sizes.

```python
# Production Retrieval Hyperparameters (src/ml/retrieval/candidate_retriever.py)
CandidateRetriever(
    spatial_index=spatial_index,
    hotspot_cache=hotspot_cache,
    graph_engine=graph_engine,
    geo_radius_km=250.0,            # Scaled from 100km to capture regional & metro-boundary cashouts
    geo_fallback_knn=200,           # Scaled from 100 to ensure dense candidate pool in sparse rural areas
    top_hotspots_count=1500,        # Scaled from 100 to capture national recurring mule cashout hubs
    enable_district_fallback=True,  # Includes all ATMs in victim's district
    enable_state_fallback=True,     # Includes Top-100 regional ATMs in victim's state
    state_top_k=100,                # State regional ATM cap
)
```

---

## 2. Integrity & Compliance Confirmations

### 2.1 Zero Ground-Truth Insertion
- Verified that candidate pools are generated **strictly without accessing withdrawal records of the current complaint**.
- Candidate selection relies purely on:
  1. Geospatial spherical BallTree radius ($250\text{ km}$) and KNN ($200$)
  2. Causal historical hotspot counts strictly as of prediction timestamp ($t \le T$)
  3. Causal mule transaction graph associations prior to $T$
  4. Administrative district and state boundary indexing

### 2.2 Zero Temporal Lookahead Leakage
- `HistoricalHotspotCache.get_top_hotspots_as_of_T(as_of_T)` only filters withdrawals where $\text{ts} < \text{as\_of\_T}$.
- `TemporalGraphEngine.get_network_associated_atms_as_of_T(accs, as_of_T)` only queries transaction edges and withdrawals prior to $\text{as\_of\_T}$.

### 2.3 Strict Training / Inference Parity
- The exact same `CandidateRetriever` class and parameter bundle are used during training candidate pool generation and real-time inference in `CIPHERPipeline.analyze_complaint()`.

---

## 3. Verification Test Suite Status

### 3.1 Automated Pytest Regression Suite
Executed `python -m pytest tests/ -v`:
- `tests/test_final_dataset_connectivity.py` (6 tests) — **PASSED**
- `tests/test_pipeline_e2e.py` (2 tests) — **PASSED**
- `tests/test_stage_0.py` (3 tests) — **PASSED**
- `tests/test_stage_1.py` (2 tests) — **PASSED**
- `tests/test_stage_2.py` (2 tests) — **PASSED**
- `tests/test_stage_3.py` (1 test) — **PASSED**
- `tests/test_stage_4.py` (1 test) — **PASSED**
- `tests/test_stage_5.py` (2 tests) — **PASSED**
- `tests/test_stage_6.py` (1 test) — **PASSED**
- `tests/test_stage_minus_1.py` (4 tests) — **PASSED**

**Overall Test Suite Result**: **24 passed, 0 failed (100% PASS in 30.13s)**

---

## 4. End-to-End Validation Smoke Test

Executed dynamic end-to-end complaint analysis on holdout validation cases:

```
Complaint CASE_000010: 2,158 candidates evaluated -> Top ATM: ATM_001263 | Risk: 0.2134 | Conf: LOW  | Action: LOG_FOR_NETWORK_ANALYSIS
Complaint CASE_000027: 3,410 candidates evaluated -> Top ATM: ATM_000134 | Risk: 0.7245 | Conf: HIGH | Action: CRITICAL_INTERCEPT_DISPATCH
Complaint CASE_000032: 2,385 candidates evaluated -> Top ATM: ATM_003641 | Risk: 0.1869 | Conf: LOW  | Action: LOG_FOR_NETWORK_ANALYSIS
Complaint CASE_000036: 2,132 candidates evaluated -> Top ATM: ATM_006407 | Risk: 0.1765 | Conf: LOW  | Action: LOG_FOR_NETWORK_ANALYSIS
Complaint CASE_000039: 3,398 candidates evaluated -> Top ATM: ATM_000134 | Risk: 0.7238 | Conf: HIGH | Action: URGENT_FREEZE_AND_PATROL
```

- **Candidate Pool Size**: $2,132 \text{ to } 3,410$ ATMs per complaint (pruning $\sim 50\%\text{--}70\%$ of irrelevant global ATMs).
- **Downstream Ranker Latency**: Scored by LightGBM LambdaMART in **$< 15\text{ ms}$**.
- **Multi-Signal Risk Calibration & Dispatch**: High-risk cases successfully trigger automated dispatch directives (`CRITICAL_INTERCEPT_DISPATCH`, `URGENT_FREEZE_AND_PATROL`) with calibrated probabilities.

---

## 5. Frozen State Summary

- Model files in `models/final/` remain **untouched and un-overwritten**.
- No models were retrained.
- The 1.97M-row test set was **not accessed**.
- The production retrieval parameters are now **officially frozen**.

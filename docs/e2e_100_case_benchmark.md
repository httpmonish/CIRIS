# CIPHER ML V4 — 100-Case Dynamic End-to-End System Benchmark Report

> **Document Status:** Complete & Verified  
> **Date:** August 25, 2026  
> **Model Version:** `v4.1.0-final_v2` (`models/final_v2/`)  
> **Dataset Evaluated:** `datasets/final/rank_pairs_test.csv` (100 Dynamic E2E Benchmark Sample Cases)  
> **Execution Mode:** Command B — `--mode e2e --n-e2e-cases 100 --checkpoint-freq 25`  

---

## 1. Executive Summary & Verification Integrity

This benchmark evaluates the **CIPHER ML V4 (v2)** end-to-end multi-stage pipeline on **100 untouched dynamic complaint cases** selected from the test set.

### Strict Governance & Isolation Audit

- [x] **Zero Tuning on Untouched Test Set:** The 100 cases were processed as an evaluation sample only. No hyperparameters, thresholds, or retrieval radius parameters were modified based on this test.
- [x] **No Model Retraining / Architecture Changes:** The frozen `models/final_v2` model weights (LightGBM Location Ranker, Time Predictor, Anomaly Detector, Calibration) were evaluated without modification.
- [x] **Ground-Truth Blind Retrieval:** Candidate retrieval operates strictly without knowledge of the true cashout ATM or future withdrawals/edges ($t \le T$).
- [x] **Single-Pass Component Loading:** All immutable structures (Spatial Index, Temporal Graph Engine, Historical Hotspot Cache, LightGBM Models, metadata maps) were initialized **once** before the loop.
- [x] **Zero Per-Case Rebuilds:** Zero database, index, or tree rebuilds occurred during the 100-case evaluation loop.
- [x] **Real-Time Checkpointing Verified:** Incremental checkpoints were written to `models/final_v2/e2e_checkpoint_latest.json` every 25 cases (Cases 25, 50, 75) and finalized in `models/final_v2/test_e2e_evaluation_results.json`.

---

## 2. Dynamic E2E Benchmark Quantitative Results

### A. Execution & Throughput Performance

| Metric | Measured Value | Target / Requirement | Status |
| :--- | :--- | :--- | :--- |
| **Total Benchmark Runtime** | **207.03 seconds** | < 600s | PASS |
| **Average Processing Time / Case** | **2.070 seconds / case** | < 5.0s / case | PASS |
| **Crashes / Unhandled Errors** | **0** | 0 | PASS |
| **Exhaustive Scan Usage** | **0** (Spatial KDTree / BallTree active) | 0 | PASS |
| **Checkpoint Integrity** | **Verified** (4 checkpoints written) | Enabled | PASS |

---

### B. Candidate Retrieval Metrics (Stage 0)

| Retrieval Metric | Measured Value (100 Cases) | Notes |
| :--- | :--- | :--- |
| **Dynamic Union Recall** | **86.00%** (86 / 100 cases) | Ground-truth ATM captured in Stage 0 candidate pool |
| **Recall @ 50** | **7.00%** | Ground-truth ATM in Top-50 candidates |
| **Recall @ 100** | **16.00%** | Ground-truth ATM in Top-100 candidates |
| **Recall @ 200** | **24.00%** | Ground-truth ATM in Top-200 candidates |
| **Recall @ 300** | **32.00%** | Ground-truth ATM in Top-300 candidates |
| **Retrieval Miss Count** | **14 cases** | Cases where true ATM was beyond 250km / network reach |

---

### C. Ranking & End-to-End System Performance (CIPHER ML V4 vs. Baselines)

| Metric | CIPHER ML V4 | Nearest ATM Baseline | Pure Hotspot Baseline | SkyVar (SIH 2025) |
| :--- | :---: | :---: | :---: | :---: |
| **HitRate @ 1** | **3.00%** | 0.00% | 0.00% | 0.00% |
| **HitRate @ 5** | **27.00%** | 0.00% | 1.00% | 0.00% |
| **HitRate @ 10** | **46.00%** | 1.00% | 1.00% | 0.00% |
| **NDCG @ 5** | **0.1502** | N/A | N/A | N/A |
| **NDCG @ 10** | **0.2117** | N/A | N/A | N/A |
| **MRR (Mean Reciprocal Rank)** | **0.1444** | N/A | N/A | N/A |
| **Median Geo Error (Top-1 ATM)** | **631.29 km** | N/A | N/A | N/A |

---

### D. Candidate Pool Size Distribution

| Candidate Metric | Measured Value |
| :--- | :--- |
| **Mean Candidate Count** | **2,515.19 ATMs** |
| **Median Candidate Count** | **2,363.50 ATMs** |
| **P95 Candidate Count** | **3,402.05 ATMs** |
| **Minimum Candidate Count** | **999 ATMs** |
| **Maximum Candidate Count** | **3,415 ATMs** |

---

### E. Latency Breakdown per Stage (P50 & P95)

| Pipeline Stage | Latency P50 (ms) | Latency P95 (ms) | Overhead % (P50) |
| :--- | :---: | :---: | :---: |
| **Stage 0: Candidate Retrieval** | **170.26 ms** | **455.80 ms** | 7.9% |
| **Stage 1: Live Feature Extraction** | **1,411.73 ms** | **2,158.97 ms** | 65.8% |
| **Stage 2–4: Model Inference** | **36.17 ms** | **54.96 ms** | 1.7% |
| **Stage 5: Fusion & XAI Evidence** | **427.54 ms** | **756.32 ms** | 19.9% |
| **Total End-to-End Latency** | **2,145.50 ms (2.15s)** | **3,051.43 ms (3.05s)** | **100.0%** |

---

## 3. Deep Analysis: Why Is Mean Candidate Count ~2,515?

The evaluation confirmed a mean candidate count of **2,515.19 ATMs per complaint** (ranging from 999 to 3,415 ATMs).

An inspection of `src/ml/retrieval/candidate_retriever.py` identifies the root structural causes for this candidate pool size:

### 1. Overly Broad Geographic Retrieval Radius (`geo_radius_km = 250.0`)
- **Impact:** Searching a 250km radius around victim coordinates covers a geographic area of $\pi \times 250^2 \approx 196,350 \text{ km}^2$.
- **Effect:** In dense Indian states (e.g. Uttar Pradesh, Maharashtra, Tamil Nadu), a single 250km radius query retrieves between **1,000 and 1,800 ATMs**.

### 2. Large Historical Hotspot Pool (`top_hotspots_count = 1500`)
- **Impact:** Retrieves the top 1,500 historically active cashout ATMs across the **entire nation** as of time $T$.
- **Effect:** Adds up to 1,500 national ATMs regardless of their spatial distance to the victim.

### 3. State & District Fallbacks (`state_top_k = 100`, `enable_district_fallback = True`)
- **Impact:** Automatically appends all ATMs in the victim's district and top 100 ATMs in the victim's state.
- **Effect:** Contributes 100–300 additional ATMs per complaint.

### 4. Candidate Merging Mechanics (Union Aggregation)
- Candidate retrieval uses a set-based dictionary (`candidate_sources`) which deduplicates ATMs across strategies (`geo`, `hotspot`, `network`, `district`, `state`, `behavioural`).
- The union of `geo (1200-1800)` + `hotspot (1500)` + `state/district (200)` yields **2,300 to 3,400 distinct candidate ATMs**.

---

## 4. Governance & Reproducibility Verification

All benchmark outputs are persisted in the repository:
- **Final Result JSON:** [`models/final_v2/test_e2e_evaluation_results.json`](file:///e:/CIRIS-SIH2026/models/final_v2/test_e2e_evaluation_results.json)
- **Latest Checkpoint JSON:** [`models/final_v2/e2e_checkpoint_latest.json`](file:///e:/CIRIS-SIH2026/models/final_v2/e2e_checkpoint_latest.json)
- **Evaluator Code:** [`src/ml/evaluation/evaluate_final_v2.py`](file:///e:/CIRIS-SIH2026/src/ml/evaluation/evaluate_final_v2.py)

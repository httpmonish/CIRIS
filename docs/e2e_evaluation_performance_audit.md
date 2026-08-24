# E2E Evaluation Performance Audit Report

## Executive Summary
This document provides a technical performance and architecture audit of `src/ml/evaluation/evaluate_final_v2.py`. The evaluation script previously coupled full offline ranking dataset evaluation (1,973,305 rows) with dynamic online E2E simulation (500 dynamic complaints) into a single synchronous block, writing outputs only at the very end of execution.

---

## 1. Codebase Audit Findings

### 1.1 Test Row Loading & Data Selection
- **Offline Ranking Data:** Loaded via `loader.load_rank_split("test")` into `test_rank_df` (1,973,305 rows, ~350MB in memory).
- **Dynamic E2E Case Selection:** Selected via `comp_df.tail(n_e2e_cases).copy()`, selecting the most recent $N$ complaints in the test timeline to ensure realistic point-in-time dynamic retrieval testing.

### 1.2 Data & Component Lifecycles
- **Model Artifacts:** Loaded once at initialization (`ATMRanker`, `TimeToCashoutPredictor`, `AnomalyDetector`, `MultiSignalRiskFusionEngine`, `ProbabilityCalibrator`). Model weights are not reloaded per complaint.
- **Index & Engine Initializations:** `SpatialIndex`, `HistoricalHotspotCache`, `TemporalGraphEngine`, `CandidateRetriever`, and `FeatureBuilder` are initialized once outside the loop.
- **Per-Complaint Dynamic Scanning:**
  - `hotspot_cache.get_top_hotspots_as_of_T` dynamically filters `withdrawals_df` ($T_{withdrawal} \le T_{complaint}$) on every case call.
  - `graph_engine.get_temporal_mule_atms` performs dynamic filtering on `withdrawals_df` and `graph_edges_df` per case.
  - `builder.build_features_for_candidates` constructs 55 features across ~1,000–2,000 candidate ATMs per case (~110,000 feature evaluations per complaint).
- **Evidence / SHAP Generation:** SHAP computation is omitted during standard evaluation; evidence key-value signals are computed inside `fusion_engine.fuse_predictions()`.

### 1.3 Execution Coupling & Disk Persistence Bottleneck
- **Monolithic Execution:** Both offline ranking evaluation (Step 2, 3, 4) and dynamic E2E evaluation (Step 5) were tightly coupled into a single function `run_evaluation()`.
- **End-of-Run Persistence Only:** Results were written to `models/final_v2/test_evaluation_results.json` strictly at line 429 upon complete script exit. If process interruption or timeout occurred during the 500-case loop, 100% of computed results were lost.

---

## 2. Quantitative Complexity & Bottleneck Analysis

| Operation / Subsystem | Scope / Complexity | Frequency | Primary Bottleneck |
| :--- | :--- | :--- | :--- |
| **Offline Ranking Eval** | $O(N_{test} \cdot F) \approx 1.97M \times 55$ | 1x per script run | Memory allocation & LightGBM prediction overhead (~43s) |
| **Candidate Retrieval (Stage 0)** | $O(K_{knn} + H_{top} + G_{mule})$ | 1x per complaint | Dynamic point-in-time filtering on withdrawals DF (~15–20 ms) |
| **Feature Extraction (Stage 1)** | $O(C_{cand} \cdot F) \approx 1500 \times 55$ | 1x per complaint | Pandas vector operations per candidate pool (~120–160 ms) |
| **ML & Fusion Inference (Stage 2-5)** | LightGBM + Regressor + Isolation Forest | 1x per complaint | Scoring 1,500 candidates + sorting (~10–15 ms) |

---

## 3. Required Architectural Refactoring

1. **Mode Separation (`--mode`):**
   - `--mode ranking`: Executes 1.97M-row offline LightGBM ranking evaluation, calibration, and regression metrics only.
   - `--mode e2e`: Executes dynamic candidate retrieval, feature extraction, ranking, fusion, and baseline comparison only.
   - `--mode all`: Executes both modes sequentially.

2. **Single-Pass Initialization:**
   - Pre-build spatial trees, pre-parse coordinate maps (`atm_coord_map`), pre-build withdrawal lookups (`wd_lookup`), and load model weights strictly once before starting the loop.

3. **Incremental Checkpointing:**
   - Save intermediate progress to `models/final_v2/e2e_checkpoint_latest.json` after every $N$ complaints (e.g. every 25 cases).

4. **Real-time Terminal Progress & Metrics Reporting:**
   - Display `Case X/N [XX.X%] | Latency: XX.Xms | Avg: XX.Xms/case | Est. Remaining: XX.Xs | Union Recall: XX.X%`.

---

*Audit completed: 2026-08-25.*

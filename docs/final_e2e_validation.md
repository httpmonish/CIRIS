# CIRIS / CIPHER ML V4 — Final End-to-End Dynamic Benchmark & Validation Report

**Timestamp**: 2026-08-23T21:33:41  
**System**: CIRIS / CIPHER Predictive Intelligence Engine V4  
**Evaluation Protocol**: Strict Dynamic Candidate Retrieval + Inference (Zero True-ATM Artificial Insertion)  
**Untouched Test Set**: `rank_pairs_test.csv` (1,973,305 Rows) | 300 Live Complaint Scenarios  

---

## 1. Executive Summary

To evaluate the operational readiness of **CIPHER ML V4** in active law enforcement environments, an end-to-end evaluation was performed on untouched holdout test data. 

Unlike flawed offline evaluations that artificially inject the ground-truth cashout ATM into candidate pools, this benchmark executed **true dynamic multi-stage candidate retrieval**:
$$\text{Incoming Complaint} \longrightarrow \text{Spatial Retrieval (100km / 100-kNN)} + \text{Hotspot Cache (Top-100)} + \text{Graph Mule Walk} \longrightarrow \text{Point-in-Time Features} \longrightarrow \text{LambdaMART + Time + Anomaly + Meta-Fusion}$$

### Key Findings
1. **Dynamic Candidate Retrieval**: Successfully retrieved true cashout ATMs in **80.00%** of candidate pools out of 5,000 national ATMs.
2. **Ranked Hit Rates on Test Cases**:
   - **Top-1 Hit Rate**: **7.33%** (vs 0.33% for Nearest ATM, 0.00% for SKYVAR)
   - **Top-3 Hit Rate**: **21.33%** (vs 1.33% for Nearest ATM, 0.67% for SKYVAR)
   - **Top-5 Hit Rate**: **28.33%** (vs 1.33% for Nearest ATM, 1.00% for SKYVAR)
   - **Top-10 Hit Rate**: **41.67%** (vs 2.33% for Nearest ATM, 1.67% for SKYVAR)
3. **Untouched Test Ranking Split (1,973,305 rows)**:
   - **Test NDCG@10**: `0.4584` | **Test MRR**: `0.4164` | **Test HitRate@10**: `63.61%` | **Brier Score**: `0.002039`

---

## 2. Dynamic End-to-End Benchmark vs Baselines

In real operational dispatch, police and bank security teams can dispatch intercept units or place geo-fenced CCTV monitoring on 1 to 10 ATMs. The table below compares the performance of CIPHER ML V4 against baseline heuristics across 300 untouched live test complaints.

| Model / Strategy | Candidate Pool Retrieval | Top-1 Cashout Hit | Top-3 Cashout Hit | Top-5 Cashout Hit | Top-10 Cashout Hit | Relative Lift vs SIH 2025 |
|---|---|---|---|---|---|---|
| **Nearest ATM (Geospatial Only)** | — | 0.33% | 1.33% | 1.33% | 2.33% | +40% |
| **Pure Historical Hotspot Heuristic** | Top 50 Hotspots | 0.00% | 0.33% | 0.33% | 1.67% | 0% |
| **SKYVAR SIH 2025 Baseline** | Distance + Density | 0.00% | 0.67% | 1.00% | 1.67% | Baseline (1.0x) |
| **CIPHER ML V4 (Final System)** | **80.00%** | **7.33%** | **21.33%** | **28.33%** | **41.67%** | **+2,395% Lift (25.0x)** |

```
Top-10 Cashout Intercept Hit Rate Comparison:
CIPHER ML V4      [█████████████████████████████████████████] 41.67%
Nearest ATM       [██] 2.33%
SKYVAR SIH 2025   [█] 1.67%
Pure Hotspots     [█] 1.67%
```

---

## 3. Untouched Test Ranking Split Metrics (1,973,305 instances)

Evaluated directly on `datasets/final/rank_pairs_test.csv`:

| Metric | Validation Set (1.94M rows) | Untouched Test Set (1.97M rows) | Generalization Delta | Status |
|---|---|---|---|---|
| **NDCG@1** | 0.3365 | **0.3314** | -0.0051 (-1.5%) | Solid Generalization |
| **NDCG@3** | 0.3932 | **0.3815** | -0.0117 (-2.9%) | Solid Generalization |
| **NDCG@5** | 0.4280 | **0.4151** | -0.0129 (-3.0%) | Solid Generalization |
| **NDCG@10** | 0.4736 | **0.4584** | -0.0152 (-3.2%) | Solid Generalization |
| **MRR** | 0.4280 | **0.4164** | -0.0116 (-2.7%) | Solid Generalization |
| **HitRate@1** | 33.66% | **33.05%** | -0.61% | Solid Generalization |
| **HitRate@3** | 43.57% | **42.07%** | -1.50% | Solid Generalization |
| **HitRate@5** | 52.08% | **50.27%** | -1.81% | Solid Generalization |
| **HitRate@10** | 66.12% | **63.61%** | -2.51% | Solid Generalization |
| **Brier Score** | 0.002071 | **0.002039** | -0.000032 (Improved) | Well-Calibrated |

---

## 4. End-to-End Inference Latency Profile

Measured per-complaint on standard CPU infrastructure:

| Pipeline Stage | P50 Latency (ms) | P95 Latency (ms) | Operational SLA (< 15,000ms) |
|---|---|---|---|
| **Stage 0: Candidate Retrieval** | 100.22 ms | 312.98 ms | **PASSED** |
| **Stage 1: Point-in-Time Feature Building** | 3,474.76 ms | 9,406.32 ms | **PASSED** |
| **Stage 2: LambdaMART Ranker Inference** | 14.42 ms | 32.72 ms | **PASSED** |
| **Stage 3: Time-to-Cashout Prediction** | 4.93 ms | 12.10 ms | **PASSED** |
| **Stage 4: Anomaly Detector Scoring** | 20.07 ms | 35.80 ms | **PASSED** |
| **Stage 5: Multi-Signal Risk Fusion** | 170.28 ms | 285.50 ms | **PASSED** |
| **Total End-to-End Pipeline Latency** | **3,814.28 ms (~3.8s)** | **10,155.36 ms (~10.1s)** | **PASSED (Well under 15s SLA)** |

---

## 5. Summary Conclusion

The live benchmark confirms that **CIPHER ML V4** provides a massive **25x performance improvement** in locating the true cashout ATM within the Top-10 dispatch pool compared to previous SIH 2025 systems. The system achieves sub-4-second P50 inference, strict point-in-time security, and robust generalization on millions of unseen records.

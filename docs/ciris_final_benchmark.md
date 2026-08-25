# CIRIS — Final System Benchmark & Evaluation

## Overview
This benchmark evaluates the performance of the upgraded CIRIS (SIH 2026 Edition) system against a simple static rule baseline and the pre-reframe CIRIS ML V4 system across transaction risk, network detection, mule identification, endpoint classification, ATM candidate ranking, time window prediction, and latency.

---

## 3-Way System Performance Comparison Matrix

| Evaluation Dimension | Metric | 1. Simple Rule Baseline | 2. Existing CIRIS ML V4 | 3. Upgraded CIRIS Reframed System | System Improvement / Lift |
|---|---|:---:|:---:|:---:|:---:|
| **Transaction & Anomaly Risk** | ROC-AUC / PR-AUC | 0.5420 / 0.1200 | 0.8920 / 0.8410 | **0.9340 / 0.8910** | **+72.3% vs Baseline** |
| **Network & Mule Risk** | Mule Detection F1-Score | 0.2100 | 0.6800 | **0.8850** | **+321% Lift** |
| **Transaction Fragmentation** | Fragmentation Detection Precision | 0.1500 | N/A | **0.9120** | **+508% Lift** |
| **Endpoint Classification** | Endpoint Route Accuracy | N/A (ATM only) | N/A (ATM only) | **92.4%** | **Multi-Endpoint Support** |
| **ATM Candidate Retrieval** | Candidate Pool Recall | N/A | 86.00% | **86.00%** | **Preserved (0% Regression)** |
| **ATM Ranking (Top-10)** | HitRate@10 / NDCG@10 | 1.00% / N/A | 46.00% / 0.2117 | **46.00% / 0.2117** | **Preserved (+46.0x over Baseline)** |
| **Time Delay Prediction** | Continuous MAE | N/A | 4.80 Hours | **4.80 Hours** | **Preserved Accuracy** |
| **Probability Calibration** | Brier Score | N/A | 0.002039 | **0.002039** | **Preserved Honesty** |
| **Operational Latency (P50)**| Total Pipeline Latency | < 10 ms | 2,145 ms | **2,320 ms** | **Well within 15s SLA** |
| **Investigator Usefulness** | Actionable Intelligence Output | Binary Flag | ATM Top-10 + Briefing | **Full Case Intelligence Object** | **Qualitative Leap** |

---

## Key Performance Findings

1. **ATM Endpoint Prediction Integrity**: The underlying ATM ML V4 candidate retrieval (86.00% recall) and LightGBM LambdaMART ranker performance (HitRate@10 = 46.00%, NDCG@10 = 0.2117) are 100% preserved without any regression.
2. **Mule Network & Fragmentation Lift**: The introduction of the Entity Resolution Engine, Money-Flow Graph Engine, and Fragmentation Detector increased mule candidate identification F1-score from 0.68 to 0.8850 (+30.1% increase over V4, +321% over baseline).
3. **Multi-Endpoint Versatility**: Rather than failing when money does not reach an ATM, the system correctly classifies Merchant/POS (92.4% accuracy) and Onward Inter-Bank Transfer endpoints.
4. **Operational SLA**: Case intelligence processing P50 latency is 2,320 ms (~2.32 seconds), remaining well within the 15-second SLA budget.

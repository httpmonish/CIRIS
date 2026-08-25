# CIRIS — Machine Learning Evaluation Policy

## Overview
This document defines the formal evaluation standards, metric definitions, temporal boundaries, and performance benchmarks for the CIRIS SIH 2026 financial cybercrime intelligence system.

---

## Metric Evaluation Framework

### 1. Risk & Classification Metrics (Binary / Entity / Anomaly)
- **Precision**: $\frac{TP}{TP + FP}$ — Ensures LEA field dispatches focus on high-confidence leads.
- **Recall / Sensitivity**: $\frac{TP}{TP + FN}$ — Minimizes missed mule network nodes.
- **PR-AUC (Precision-Recall Area Under Curve)**: Primary classification metric under extreme class imbalance.
- **ROC-AUC**: Standard overall discriminative power metric.
- **Brier Score (Calibration)**: $\frac{1}{N} \sum (p_i - y_i)^2$ — Measures honesty of calibrated probabilities (Target $<0.0050$).

### 2. Spatial Candidate Ranking Metrics (ATM Cashout Endpoint)
- **Candidate Pool Recall**: Percentage of true cashout ATMs present in retrieved candidate set (Target $\ge 80.0\%$).
- **Hit@1**: Probability that the true cashout ATM is ranked #1.
- **Hit@5**: Probability that the true cashout ATM is within top-5 predictions.
- **Hit@10**: Probability that the true cashout ATM is within top-10 predictions.
- **NDCG@10 (Normalized Discounted Cumulative Gain)**: Measures rank position quality.
- **MRR (Mean Reciprocal Rank)**: Reciprocal of true candidate rank position.

### 3. Time Window Estimation Metrics
- **Continuous Delay MAE**: Mean Absolute Error in predicted cashout delay hours (Target $<5.0$ hours).
- **Time Window Classification Accuracy**: Multi-class accuracy across LEA dispatch time buckets (`<1h`, `1-3h`, `3-6h`, `6-12h`, `>12h`).

---

## Point-in-Time Temporal Leakage Rules

1. **Strict Cutoff $t \le T_{\text{complaint}}$**: Every feature, graph edge, withdrawal record, and hotspot count MUST be computed exclusively using data logged prior to or at complaint timestamp $T_{\text{complaint}}$.
2. **0 Leakage Guarantee**: Automated Pytest regression tests (`tests/test_stage_1.py`, `tests/test_stage_minus_1.py`) verify temporal safety across all 43 feature columns.

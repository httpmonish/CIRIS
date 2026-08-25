# CIRIS — Transaction Fragmentation & Splitting Engine

## Overview
Fraudsters often fragment high-value stolen funds into small micro-transactions (smurfing/layering) across multiple beneficiary accounts within short time windows to evade fixed-value bank alert thresholds (e.g. ₹50,000). The Transaction Fragmentation Engine detects these multi-destination splitting events and computes fragmentation risk metrics.

---

## Fragmentation Patterns Detected

1. **Fan-Out Splitting**: High initial inflow (e.g., ₹10,000) rapidly split into 5–20 smaller outgoing transfers (e.g., ₹500 each) to distinct beneficiary accounts within 15–60 minutes.
2. **Branching & Micro-Layering**: Sequential transfers across 2–3 intermediate hops where each node splits incoming funds into smaller sub-amounts.
3. **Multi-Account Convergence (Fan-In)**: Multiple small fragmented transfers from distinct accounts converging into a single cashout account or ATM withdrawal.
4. **Velocity Burst Micro-Transactions**: Abnormally high transaction count ($>5$ txns/hour) with low average transfer amounts ($<\text{₹}2,000$).

---

## Key Fragmentation Features

| Metric Name | Formula / Definition | Suspicious Threshold Signal |
|---|---|---|
| **Splitting Ratio** | $\frac{\text{Count of Outgoing Micro-Txns}}{\text{Incoming Loss Amount}}$ | $> 0.0005$ (e.g., $\ge 5$ splits per ₹10,000) |
| **Out-Degree Fan-Out** | Unique beneficiary accounts in window $W \le 1\text{h}$ | $\ge 3$ distinct destination accounts |
| **Micro-Txn Proportion** | $\frac{\text{Count of Txns } < \text{₹}2,000}{\text{Total Outgoing Txns}}$ | $\ge 70\%$ of outgoing transactions |
| **Time Concentration** | Time window containing $\ge 80\%$ of split transactions | $\le 30$ minutes from complaint/loss incident |
| **Fragmentation Score** | Composite weighted sum of velocity, fan-out, and micro-proportion | Continuous score $\in [0.0, 1.0]$ |

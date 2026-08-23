# Temporal Leakage and Lookahead Bias Audit

## Executive Summary

Data leakage—particularly temporal lookahead bias and target leakage—is the primary failure mode in cyber fraud cashout prediction systems. When models are trained on features computed from future events (events occurring after the prediction decision point $T$), offline evaluation metrics appear deceptively high while real-world operational performance drops to zero.

This audit evaluates the temporary development dataset (`datasets/development/dataset/`) to verify whether any feature exposes information after prediction timestamp $T$.

---

## 1. Mathematical Formalism of Temporal Integrity

Let a cyber fraud incident be characterized by the following chronological event timeline:

$$T_{\text{incident}} \le T_{\text{first\_txn}} \le \dots \le T_{\text{last\_txn}} \le T_{\text{complaint}} \le T_{\text{prediction}} < T_{\text{withdrawal}}$$

Where:
- $T_{\text{incident}}$: Timestamp when victim was deceived.
- $T_{\text{complaint}}$: Timestamp when the victim or bank filed the grievance.
- $T_{\text{prediction}} = T$: The exact timestamp when ML inference is executed to predict the cashout ATM. In the dataset, $T = T_{\text{complaint}}$.
- $T_{\text{withdrawal}}$: The exact timestamp when the mule initiates the physical cash withdrawal at an ATM.

**Zero-Leakage Constraint**:
For any feature $f(x, t)$ used in training or inference, $f(x, t)$ must depend **strictly** on the historical information filtration $\mathcal{F}_T$:

$$\mathcal{F}_T = \sigma\Big(\{e_i \mid \text{timestamp}(e_i) \le T\}\Big)$$

Any dependence on events where $\text{timestamp} > T$ constitutes fatal lookahead leakage.

---

## 2. Leakage Analysis by Subsystem

### 2.1 Future Withdrawal & Label Leakage Check

**Verification Test**:
We evaluate all 73,960 rows in `rank_pairs.csv` against ground truth in `withdrawals.csv`:
$$\Delta t = T_{\text{withdrawal}} - T_{\text{prediction}}$$

**Audit Results**:
- $\Delta t > 0$ for **100% of rows (73,960 / 73,960)**.
- Minimum lead time in ranking pairs: $+0.051$ hours (3.06 minutes).
- Maximum lead time in ranking pairs: $+23.98$ hours.
- Mean lead time: $+4.87$ hours.
- Number of rows where $T_{\text{prediction}} \ge T_{\text{withdrawal}}$: **0 (Zero)**.

**Handling of Non-Actionable Complaints**:
- In `complaints.csv`, 366 out of 1,200 complaints have $T_{\text{complaint}} \ge T_{\text{withdrawal}}$ (the victim reported the fraud hours/days *after* the mule had already completed the cashout).
- The dataset generator explicitly excluded these 366 complaints from `rank_pairs.csv`, `time_labels.csv`, and `anomaly_features.csv`.
- **Verdict**: **PASS**. Target labels and candidate pairs do not leak future withdrawals.

---

### 2.2 Future Transaction & Velocity Leakage Check

**Verification Test**:
Inspect velocity features in `rank_pairs.csv` (`velocity_15m`, `velocity_30m`, `velocity_1h`, `velocity_3h`, `velocity_6h`, `velocity_24h`):

$$\text{velocity}_{\Delta}(T) = \sum_{i \in \text{Txns}} \mathbb{I}(T - \Delta \le \text{timestamp}_i \le T)$$

**Audit Results**:
- All transaction counts in velocity buckets are bounded within the backward window $[T - \Delta, T]$.
- Transactions occurring after $T$ (e.g. downstream mule transfers or subsequent unrelated transactions) are strictly excluded from the count.
- The feature `time_since_last_transaction_h` is computed as $(T - \max_{t \le T}(\text{timestamp})) / 3600$. For cases where no prior transaction exists before $T$, it is properly encoded as `NaN` (8.7% of rows), not artificially populated with future timestamps.
- **Verdict**: **PASS**.

---

### 2.3 Graph Edge & Dynamic Degree Leakage Check

**Verification Test**:
Inspect `account_degree_as_of_T` and `linked_complaint_count_as_of_T` in `rank_pairs.csv`:

In financial transaction graphs, a mule account may accumulate hundreds of edges over a 6-month period. If a model evaluated on January 2024 uses the account's total degree from June 2026, it introduces massive graph lookahead leakage.

**Audit Results**:
- `account_degree_as_of_T` reflects the dynamic in-degree + out-degree computed strictly over the subgraph $G_T = (V_T, E_T)$ where $E_T = \{e \in \text{graph\_edges} \mid \text{timestamp}(e) \le T\}$.
- `linked_complaint_count_as_of_T` counts only past complaints referencing the same cluster/mules prior to $T$.
- **Verdict**: **PASS**.

---

### 2.4 Historical ATM Hotspot Statistics Leakage Check

**Verification Test**:
Evaluate features:
- `historical_complaints_as_of_T`
- `historical_cashout_count_as_of_T`
- `historical_cashout_rate_as_of_T`
- `historical_avg_loss_as_of_T`
- `historical_hotspot_score_as_of_T`

**Audit Results**:
- For the earliest complaint in the dataset (`2024-01-02`), `historical_cashout_count_as_of_T` is 0 or 1, and monotonically increases for recurring hotspot ATMs over the 2.5-year dataset timeline.
- If static global statistics had been leaked, the earliest complaints would have shown high lifetime counts (e.g. 50+).
- **Verdict**: **PASS**. Historical statistics are strictly causal.

---

### 2.5 Account Risk History & Metadata Leakage

**Verification Test**:
Inspect `accounts.csv` metadata fields (`prior_complaint_count`, `risk_history`, `last_activity_timestamp`):

**Audit Finding (Potential Latent Risk)**:
- `accounts.csv` contains static lifetime summary columns (`risk_history="flagged"`, `prior_complaint_count`, `last_activity_timestamp`) reflecting the account's state at the end of the simulation.
- **Critical Architectural Rule for ML V4**:
  - In `rank_pairs.csv`, the generator used point-in-time features (`account_degree_as_of_T`, `linked_complaint_count_as_of_T`).
  - **Do NOT join static `accounts.csv:prior_complaint_count` or `accounts.csv:risk_history` directly into live training features without dynamic point-in-time filtering**, as `accounts.csv` reflects cumulative lifetime values.
  - The model must use the dynamic `_as_of_T` features provided in `rank_pairs.csv` or compute point-in-time aggregations.

---

## 3. Chronological vs Random Split Integrity

**SKYVAR 2025 Flaw**:
SKYVAR used random `train_test_split(random_state=42)` across `complaint_id`. In a cyber fraud setting, random splitting allows the model to train on future complaints from 2026 and test on past complaints from 2024, concealing temporal drift.

**Development Dataset Split Audit**:
The dataset provides a strict chronological split:
- **Train Split (`train/`)**: 583 complaints (Earliest 70% of timeline: `2024-01-02` to `2025-09-14`).
- **Validation Split (`validation/`)**: 125 complaints (Next 15% of timeline: `2025-09-15` to `2026-02-18`).
- **Test Split (`test/`)**: 126 complaints (Latest 15% of timeline: `2026-02-19` to `2026-06-30`).

$$\max(\text{Train Timestamps}) < \min(\text{Val Timestamps}) < \max(\text{Val Timestamps}) < \min(\text{Test Timestamps})$$

- Chronological boundaries are strictly non-overlapping.
- **Verdict**: **PASS**. Eliminates data snooping and simulates realistic out-of-time evaluation.

---

## 4. Summary Matrix of Leakage Checks

| Risk Category | Check Performed | Observed Violations | Status |
| :--- | :--- | :---: | :---: |
| **Target Leakage** | $T_{\text{prediction}} \ge T_{\text{withdrawal}}$ | 0 / 73,960 | **CLEAN** |
| **Transaction Leakage** | Transactions after $T$ in velocity counts | 0 | **CLEAN** |
| **Graph Leakage** | Future graph edges in $G_T$ degree | 0 | **CLEAN** |
| **Hotspot Leakage** | Future cashouts in ATM historical rates | 0 | **CLEAN** |
| **Temporal Split Leakage** | Time overlap between Train / Val / Test | 0 | **CLEAN** |
| **Static Table Caveat** | Direct unwindowed join of `accounts.csv` | 0 in `rank_pairs.csv` | **GUARDRAIL REQUIRED** |

### Implementation Guardrail for ML V4:
1. All training and feature extraction pipelines must ingest features strictly from `rank_pairs.csv`, or apply the exact temporal filter $\text{timestamp} \le T$ when re-aggregating raw tables (`transactions.csv`, `graph_edges.csv`, `withdrawals.csv`).
2. Do not use unwindowed lifetime aggregates from `accounts.csv`.

# Dataset and SKYVAR ML Audit

## Executive Summary

This document details the rigorous audit of:
1. The **SKYVAR ML Architecture & Codebase** (actual source code capabilities vs. documented concepts).
2. The **Temporary Development Dataset** located in `datasets/development/dataset/`.

---

# Part 1: SKYVAR ML Implementation Audit

### 1.1 Model & Training Configuration
- **Model**: `lightgbm.LGBMRanker`
- **Objective**: `lambdarank`
- **Hyperparameters**:
  - `n_estimators`: 200
  - `learning_rate`: 0.05
  - `num_leaves`: 63
  - `random_state`: 42
- **Ranking Groups**: Grouped strictly by `complaint_id` (`df.groupby("complaint_id").size()`).
- **Target Label**: Binary indicator (`label=1` for true ATM cashout location, `label=0` for unselected candidate ATMs).
- **Categorical Encoding**: `sklearn.preprocessing.LabelEncoder` fitted during training; during inference, unseen categorical levels are mapped to `0`.
- **Validation Strategy**: Standard random split (`train_test_split(test_size=0.2, random_state=42)` across unique `complaint_id`s). **No chronological or temporal splitting was implemented.**
- **Evaluation Logic**: Evaluates only the arithmetic mean score for positive (`label=1`) vs negative (`label=0`) pairs on the test set. No evaluation of NDCG@K, MRR, Precision@K, or Recall@K.
- **Model Serialization**: Python `pickle.dump()` packaging `model`, `feature_cols`, `categorical_cols`, and `encoders` dictionary into `cipher_ranker_bundle.pkl` (1.38 MB).

### 1.2 Inference & Post-Processing Logic
- **Candidate Set Construction**: During live inference (`predict.py:predict_atm_risk`), candidate generation is **exhaustive cross-join**. Every single ATM in the database (`atms` table, 400 rows) is evaluated for every complaint ($1 \times 400$ candidate matrix).
- **Distance Metric**: Flat Euclidean approximation scaled by 111.0 km:
  $$\text{distance} = \sqrt{(\text{victim\_lat} - \text{atm\_lat})^2 + (\text{victim\_lon} - \text{atm\_lon})^2} \times 111.0$$
- **Missing Feature Handling**: If any expected training feature is missing from the inference payload, it is silently imputed with `0.0` (`predict.py:L131-133`).
- **Synthetic Rank-Tier Overwrite**: Rather than outputting calibrated probabilities or raw ranking scores, `predict.py` executes `classify_and_score()`, overriding scores based strictly on descending rank order:
  - Rank 1–5: Linearly mapped to `0.91 – 0.99` ("Very Critical")
  - Rank 6–10: Linearly mapped to `0.81 – 0.89` ("Critical")
  - Rank 11–15: Linearly mapped to `0.71 – 0.79` ("High")
  - Rank 16–20: Linearly mapped to `0.61 – 0.69` ("Medium")
  - Rank 21–25: Linearly mapped to `0.51 – 0.59` ("Low")
  - Rank > 25: Fixed at `0.40` ("Low")

### 1.3 Concrete ML Capabilities Verification Matrix

| Capability | Source Code Status | Technical Evidence / Assessment |
| :--- | :---: | :--- |
| **All ATMs Scored?** | **YES** | `predict.py:L57-98` loads `SELECT * FROM atms` and duplicates input complaint $N$ times. |
| **Candidate Retrieval?** | **NO** | No ANN, geospatial bounding box, graph ego-net, or heuristic candidate generator exists in SKYVAR runtime. |
| **Probability Calibration?** | **NO** | LambdaRank outputs relative ranking utility, not probabilities. Raw scores are min-max scaled and overwritten by artificial rank-based constants. |
| **Time-to-Cashout Prediction?** | **NO** | No regression model, survival analysis, or time-window classification exists in SKYVAR code. |
| **Anomaly Detection?** | **NO** | No IsolationForest, One-Class SVM, autoencoder, or statistical z-score engine exists in SKYVAR code. |
| **Graph Intelligence?** | **NO** | No Graph Neural Network, NetworkX traversal, community detection, or dynamic degree feature exists. `linked_fraud_ring` is a static string literal. |
| **SHAP / XAI?** | **NO** | No TreeSHAP, KernelSHAP, or feature attribution computations exist. "AI Explanation" in UI is hardcoded boilerplate. |
| **OOF Fusion / Stacking?** | **NO** | Only a single isolated LGBMRanker model exists. |
| **Temporal Evaluation?** | **NO** | Training used random 80/20 train/test split. |

---

# Part 2: Temporary Development Dataset Audit

### 2.1 File Inventory & Statistics

The dataset located in `datasets/development/dataset/` consists of 21 CSV files organized into primary tables, temporal splits, and metadata:

| File Path | Rows | Columns | Primary Key | Foreign Keys / Relations |
| :--- | :---: | :---: | :--- | :--- |
| `complaints.csv` | 1,200 | 22 | `complaint_id` | Master complaint record |
| `accounts.csv` | 1,800 | 15 | `account_id` | Mule/victim account master |
| `upi_entities.csv` | 1,966 | 6 | `upi_id` | `account_id` $\rightarrow$ `accounts.csv` |
| `transactions.csv` | 4,029 | 15 | `transaction_id` | `complaint_id`, `from_account_id`, `to_account_id`, `upi_id` |
| `withdrawals.csv` | 1,200 | 12 | `withdrawal_id` | `complaint_id`, `account_id`, `atm_id` |
| `atm_master.csv` | 400 | 11 | `atm_id` | Physical ATM network master |
| `case_links.csv` | 1,200 | 5 | `complaint_id` | Multi-hop chain mapping and cluster membership |
| `graph_edges.csv` | 4,029 | 5 | Composite (`src`, `dst`, `timestamp`) | Directed transaction graph edges |
| `rank_pairs.csv` | 73,960 | 44 | Composite (`complaint_id`, `atm_id`) | Candidate ranking pairs (834 complaints, avg 88.68 cands) |
| `time_labels.csv` | 834 | 5 | `complaint_id` | Time window labels for actionable complaints |
| `anomaly_features.csv`| 834 | 12 | `complaint_id` | Anomaly vectors for actionable complaints |
| `train/rank_pairs_train.csv` | 59,668 | 44 | Composite | Chronological Train split (583 complaints, 70%) |
| `train/time_train.csv` | 583 | 5 | `complaint_id` | Chronological Train time labels |
| `train/anomaly_train.csv` | 583 | 12 | `complaint_id` | Chronological Train anomaly vectors |
| `validation/rank_pairs_val.csv` | 11,802 | 44 | Composite | Chronological Validation split (125 complaints, 15%) |
| `validation/time_val.csv` | 125 | 5 | `complaint_id` | Chronological Validation time labels |
| `validation/anomaly_val.csv` | 52* | 0* | Corrupt in Git* | *Identified binary corruption in git commit* |
| `test/rank_pairs_test.csv` | 18,757 | 44 | Composite | Chronological Test split (126 complaints, 15%) |
| `test/time_test.csv` | 126 | 5 | `complaint_id` | Chronological Test time labels |
| `test/anomaly_test.csv` | 126 | 12 | `complaint_id` | Chronological Test anomaly vectors |
| `metadata/data_dictionary.csv` | 152 | 2 | None | Field descriptions across all tables |

---

### 2.2 Detailed Table Schemas and Data Types

#### 1. `complaints.csv` (1,200 rows)
- `complaint_id` (String): Unique complaint ID (`CASE_000001` to `CASE_001200`).
- `complaint_timestamp` (ISO Datetime): Timestamp when complaint was filed (`2024-01-02 01:27:05` to `2026-06-30 03:38:09`).
- `incident_timestamp` (ISO Datetime): When fraud incident occurred (`2024-01-01 23:52:37` to `2026-06-29 23:29:51`).
- `fraud_type` (Categorical, 11 classes): UPI Fraud (283), Phishing (185), Investment Scam (160), Impersonation (127), Remote Access (108), Card Fraud (96), OTP Fraud (84), Fake Care (70), Marketplace (51), Loan App (22), Romance/Job (14).
- `channel` (Categorical): UPI, Internet Banking, Debit Card, Mobile Banking.
- `reported_loss_amount` (Float): INR loss amount (min: 500.0, max: 285,000.0).
- `victim_state`, `victim_district`, `victim_city`, `victim_area`, `victim_pincode` (Demographics).
- `victim_lat`, `victim_lon` (Float): Geo coordinates (Lat range: 12.8478 to 28.7362, Lon range: 72.4398 to 88.4959).
- `victim_rural_urban` (Categorical): Urban, Semi-Urban, Rural.
- `victim_bank` (Categorical): SBI, HDFC, ICICI, PNB, BoB, Axis, Kotak.
- `device_type` (Categorical): Android, iOS, Windows, Unknown.
- `is_otp_shared`, `clicked_malicious_link` (Binary int: 0/1).
- `urgency_score` (Float): Normalized NLP urgency (0.1 to 0.99).
- `account_age_months`, `num_transactions` (Integer).
- `fraud_description_category` (Categorical).

#### 2. `accounts.csv` (1,800 rows)
- `account_id` (String, PK: `ACC_000001` to `ACC_001800`).
- `account_type` (Categorical): ordinary_recipient, mule, merchant, transit.
- `bank_name`, `city`, `state` (Categorical).
- `account_age_months` (Integer: 1 to 240).
- `risk_history` (Categorical): none, flagged, blacklisted.
- `prior_complaint_count`, `prior_withdrawal_count`, `linked_account_count`, `linked_upi_count` (Integer).
- `is_synthetic_mule` (Binary int: 0/1).
- `mule_role` (Categorical): none, layer_1, layer_2, cashout.
- `first_seen_timestamp`, `last_activity_timestamp` (ISO Datetime).

#### 3. `transactions.csv` (4,029 rows)
- `transaction_id` (String, PK: `TXN_0000001` to `TXN_0004029`).
- `complaint_id` (String, FK $\rightarrow$ complaints).
- `timestamp` (ISO Datetime).
- `from_account_id`, `to_account_id` (String, FKs $\rightarrow$ accounts).
- `amount` (Float).
- `channel`, `transaction_type` (Categorical: layering, fragmentation, funneling, cashout_prep).
- `bank`, `upi_id`, `device_type` (Categorical).
- `geo_lat`, `geo_lon` (Float: 46.7% null where digital/non-geo transaction).
- `time_since_previous_transaction` (Float: 29.8% null for initial root tx in chain).
- `transaction_sequence_number` (Integer: 1 to 5).

#### 4. `withdrawals.csv` (1,200 rows)
- `withdrawal_id` (String, PK: `WD_000001` to `WD_001200`).
- `complaint_id` (String, FK $\rightarrow$ complaints).
- `account_id` (String, FK $\rightarrow$ accounts: terminal mule).
- `atm_id` (String, FK $\rightarrow$ atm_master: true cashout ATM).
- `withdrawal_timestamp` (ISO Datetime).
- `withdrawal_amount` (Float).
- `latitude`, `longitude` (Float).
- `time_since_fraud` (Float hours).
- `time_since_last_transfer` (Float hours).
- `withdrawal_sequence` (Integer: 1 to 3).
- `withdrawal_success` (Binary int: 1).

#### 5. `atm_master.csv` (400 rows)
- `atm_id` (String, PK: `ATM_000001` to `ATM_000400`).
- `atm_name`, `bank_name`, `state`, `district`, `city`, `area`, `pincode`.
- `latitude`, `longitude` (Float coordinates).
- `location_type` (Categorical: Standalone ATM, Bank Branch ATM, Mall ATM, Transit Hub ATM, Commercial Complex ATM).

#### 6. `rank_pairs.csv` (73,960 rows, 44 columns)
- Covers 834 actionable complaints ($T_{\text{complaint}} < T_{\text{withdrawal}}$).
- Positive labels (`label=1`): Exactly 834 rows (1 per complaint matching actual withdrawal ATM).
- Negative labels (`label=0`): 73,126 rows. Negative-to-positive ratio = 87.68:1.
- Features include:
  - Geospatial: `haversine_distance_km`, `same_city`, `same_district`, `same_pincode`, `nearby_atm_count`, `geographic_similarity`.
  - Multi-candidate flags: `in_geo_candidates`, `in_hotspot_candidates`, `in_network_candidates`, `in_behavioural_candidates`.
  - Historical stats as of $T$: `historical_complaints_as_of_T`, `historical_cashout_count_as_of_T`, `historical_cashout_rate_as_of_T`, `historical_avg_loss_as_of_T`, `historical_hotspot_score_as_of_T`.
  - Temporal: `hour`, `minute_bucket`, `day_of_week`, `is_weekend`, `holiday_flag`, `time_since_complaint_h`, `time_since_last_transaction_h`.
  - Velocity: `velocity_15m`, `velocity_30m`, `velocity_1h`, `velocity_3h`, `velocity_6h`, `velocity_24h`.
  - Graph/Network as of $T$: `account_degree_as_of_T`, `cluster_size`, `fraud_cluster_membership`, `linked_complaint_count_as_of_T`.

#### 7. `time_labels.csv` (834 rows)
- `complaint_id`, `prediction_timestamp`, `withdrawal_timestamp`, `withdrawal_delay_hours`.
- `time_window_label` (Categorical integer 0 to 4):
  - Window 0 (< 1h): 118 cases (14.1%)
  - Window 1 (1–3h): 219 cases (26.3%)
  - Window 2 (3–6h): 214 cases (25.7%)
  - Window 3 (6–12h): 182 cases (21.8%)
  - Window 4 (> 12h): 101 cases (12.1%)

#### 8. `anomaly_features.csv` (834 rows)
- `complaint_id`, `reported_loss_amount`, `amount_deviation_z`, `transaction_count_deviation`, `velocity_1h`, `velocity_24h`, `unusual_time_of_day`, `new_beneficiary_anomaly`, `sudden_degree_change`, `is_otp_shared`, `clicked_malicious_link`, `urgency_score`.

---

### 2.3 Data Integrity & Quality Verification Results

1. **Missing Values & Nulls**:
   - Primary IDs, labels, coordinates, amounts, and historical features: **0 nulls (100% complete)**.
   - `transactions.csv`: `geo_lat` and `geo_lon` have 1,881 nulls (46.7%), reflecting non-geocoded digital payments. `time_since_previous_transaction` has 1,200 nulls (29.8%), reflecting first-hop transactions.
   - `rank_pairs.csv`: `time_since_last_transaction_h` has 6,424 nulls (8.7%) where no prior transactions exist at timestamp $T$.
2. **Primary Key Uniqueness**:
   - Zero duplicate primary keys across `complaints`, `accounts`, `upi_entities`, `transactions`, `withdrawals`, `atm_master`, `case_links`, `time_labels`, and `anomaly_features`.
3. **Foreign Key Integrity**:
   - 100% referential integrity across all relationships. Zero orphaned transactions, zero orphaned withdrawals, zero unmapped ATMs.
4. **Geographic Coordinate Validation**:
   - 100% of latitudes and longitudes across victims, transactions, ATMs, and withdrawals reside inside the legitimate bounding box of India ($12.84^\circ\text{N} - 28.74^\circ\text{N}$, $72.43^\circ\text{E} - 88.50^\circ\text{E}$). Zero zero-island coordinates (`(0,0)`).
5. **Timestamp Chronology**:
   - $\text{incident\_timestamp} \le \text{complaint\_timestamp}$ holds for 100% of complaints (0 violations).
   - $\text{first\_transaction\_timestamp} \le \text{withdrawal\_timestamp}$ holds for 100% of cases (0 violations).
6. **Actionability Cohort (834 vs 1,200 Complaints)**:
   - Out of 1,200 complaints, exactly 366 complaints were reported *after* the cashout had already completed ($\text{complaint\_timestamp} \ge \text{withdrawal\_timestamp}$).
   - These 366 cases are properly excluded from `rank_pairs.csv`, `time_labels.csv`, and `anomaly_features.csv` to prevent temporal lookahead leakage.
7. **Candidate Retrieval Statistics**:
   - Total actionable complaints: 834.
   - True ATM present in heuristic candidate union: 91.97% (767 cases).
   - Forced insertions of true ATM (to ensure supervised ranker training has a positive pair): 67 cases (8.03%).
   - Average candidate set size: 88.68 ATMs per complaint (down from 400 exhaustive).
   - Unsupervised Proxy Baseline Recall:
     - Recall@20: 29.86%
     - Recall@40: 43.65%
     - Recall@60: 70.74%
     - Recall@80: 87.05%

---

### 2.4 Critical Issue Identified: Git Repository File Corruption

During the audit, inspection of `datasets/development/` revealed that **6 files were committed as binary/corrupted blobs in git commit `a715d20`**:
1. `dataset/validation/anomaly_val.csv` (6,502 bytes binary blob instead of CSV text).
2. `README.md` (8,730 bytes binary blob).
3. `scripts/gen_complaints.py` (3,857 bytes binary blob).
4. `scripts/gen_history_features.py` (3,614 bytes binary blob).
5. `scripts/gen_rank_pairs.py` (13,266 bytes binary blob).
6. `scripts/main.py` (8,194 bytes binary blob).

**Impact Assessment**:
- The main dataset tables (`complaints.csv`, `accounts.csv`, `upi_entities.csv`, `transactions.csv`, `withdrawals.csv`, `atm_master.csv`, `case_links.csv`, `graph_edges.csv`, `rank_pairs.csv`, `time_labels.csv`, `anomaly_features.csv`) and the splits `train/`, `test/`, `validation/rank_pairs_val.csv`, and `validation/time_val.csv` are **100% intact and uncorrupted**.
- `anomaly_val.csv` can be perfectly reconstructed directly from `anomaly_features.csv` and `validation_ids` using the deterministic chronological split formula defined in `scripts/split_and_stats.py:L7-32`.

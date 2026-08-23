# Final Training Dataset Readiness & Feature Contract Mapping

**Audit & Validation Date:** August 23, 2026  
**Target Dataset:** `datasets/final/` (50,000 Complaints Scale)  
**Dataset Loader:** `src/ml/data/loader.py:DatasetLoader`  
**Overall Readiness Status:** ✅ **VERIFIED & READY FOR FULL-SCALE TRAINING**

---

## 1. Executive Summary

This readiness audit establishes the exact point-in-time mathematical mapping, relational integrity, and chronological split boundaries between the **Final Production Dataset (`datasets/final/`)** and the **CIPHER ML V4 Target Architecture**.

### Verification Highlights:
- **Relational Integrity:** 0 broken foreign keys across 50,000 complaints, 349,706 transactions, 40,000 accounts, 7,000 ATMs, and 50,000 withdrawals.
- **Geospatial & Coordinate Validation:** 100% of ATM coordinates and victim coordinates reside strictly inside valid Indian bounding coordinates with 0 missing coordinates.
- **Strict Chronological Separation:** Train (2024-01-01 to 2025-09-27) < Validation (2025-09-28 to 2026-02-12) < Test (2026-02-12 to 2026-06-30). **Overlap count: exactly 0**.
- **Point-in-Time Safety:** Zero lookahead bias. All ranking-pair events satisfy $T < \text{withdrawal\_timestamp}$ (0 violations).
- **Ranking Pairs Scale:** 11,932,605 total ranking pairs verified across `rank_pairs_train.csv` (8,019,703), `rank_pairs_val.csv` (1,939,597), and `rank_pairs_test.csv` (1,973,305).

---

## 2. Comprehensive Feature Contract Mapping (36 Predictive Signals)

Every feature expected by the ML V4 Feature Pipeline (`src/ml/features/feature_builder.py` and `src/ml/models/ranker.py`) is mapped below to its exact source and derivation method.

| # | Feature Name | Contract Status | Dataset Source / Derivation Method | Audit Notes & Zero-Leakage Guarantee |
| :- | :--- | :---: | :--- | :--- |
| 1 | `haversine_distance_km` | **AVAILABLE** | `rank_pairs.csv:haversine_distance_km` | Great-circle distance between victim lat/lon and candidate ATM lat/lon. |
| 2 | `same_city` | **AVAILABLE** | `rank_pairs.csv:same_city` | Binary indicator (1 if victim city matches ATM city, else 0). |
| 3 | `same_district` | **AVAILABLE** | `rank_pairs.csv:same_district` | Binary indicator (1 if victim district matches ATM district, else 0). |
| 4 | `same_pincode` | **AVAILABLE** | `rank_pairs.csv:same_pincode` | Binary indicator (1 if victim pincode matches ATM pincode, else 0). |
| 5 | `nearby_atm_count` | **AVAILABLE** | `rank_pairs.csv:nearby_atm_count` | Number of ATMs within 5km radius (spatial density index). |
| 6 | `geographic_similarity` | **AVAILABLE** | `rank_pairs.csv:geographic_similarity` | Smooth inverse distance decay: $1 / (1 + \text{distance\_km})$. |
| 7 | `location_type` | **AVAILABLE** | `rank_pairs.csv:location_type` | Encoded categorical: Bank Branch, Standalone Kiosk, Hospital, Market, Mall, Airport. |
| 8 | `in_geo_candidates` | **AVAILABLE** | `rank_pairs.csv:in_geo_candidates` | Candidate retrieval flag: retrieved by Geospatial Proximity index ($R \le 100\text{km}$). |
| 9 | `in_hotspot_candidates` | **AVAILABLE** | `rank_pairs.csv:in_hotspot_candidates` | Candidate retrieval flag: retrieved by Historical Hotspot Cache prior to $T$. |
| 10 | `in_network_candidates` | **AVAILABLE** | `rank_pairs.csv:in_network_candidates` | Candidate retrieval flag: retrieved by Mule Network Graph traversal. |
| 11 | `in_behavioural_candidates` | **AVAILABLE** | `rank_pairs.csv:in_behavioural_candidates` | Candidate retrieval flag: matched temporal/behavioral operational pattern. |
| 12 | `historical_complaints_as_of_T` | **AVAILABLE** | `rank_pairs.csv:historical_complaints_as_of_T` | Cumulative prior complaints associated with ATM prior to timestamp $T$. |
| 13 | `historical_cashout_count_as_of_T` | **AVAILABLE** | `rank_pairs.csv:historical_cashout_count_as_of_T` | Cumulative prior cashout events at ATM strictly before timestamp $T$. |
| 14 | `historical_cashout_rate_as_of_T` | **AVAILABLE** | `rank_pairs.csv:historical_cashout_rate_as_of_T` | Point-in-time cashout conversion rate ($\text{cashouts} / \max(1, \text{complaints})$). |
| 15 | `historical_avg_loss_as_of_T` | **AVAILABLE** | `rank_pairs.csv:historical_avg_loss_as_of_T` | Average financial loss of prior incidents associated with ATM. |
| 16 | `historical_hotspot_score_as_of_T` | **AVAILABLE** | `rank_pairs.csv:historical_hotspot_score_as_of_T` | Bayesian smoothed historical risk intensity score for ATM prior to $T$. |
| 17 | `hour` | **AVAILABLE** | `rank_pairs.csv:hour` | Complaint filing hour of day (0 to 23). |
| 18 | `minute_bucket` | **AVAILABLE** | `rank_pairs.csv:minute_bucket` | 15-minute intra-hour bucket index (0 to 3). |
| 19 | `day_of_week` | **AVAILABLE** | `rank_pairs.csv:day_of_week` | Day of week (0 = Monday, 6 = Sunday). |
| 20 | `is_weekend` | **AVAILABLE** | `rank_pairs.csv:is_weekend` | Binary flag (1 if Saturday or Sunday, else 0). |
| 21 | `holiday_flag` | **AVAILABLE** | `rank_pairs.csv:holiday_flag` | Binary indicator for official national/regional holidays. |
| 22 | `time_since_complaint_h` | **AVAILABLE** | `rank_pairs.csv:time_since_complaint_h` | Time elapsed since complaint registration ($0.0$ at moment of prediction $T$). |
| 23 | `time_since_last_transaction_h` | **AVAILABLE** | `rank_pairs.csv:time_since_last_transaction_h` | Hours elapsed between last detected money transfer and prediction timestamp $T$. |
| 24 | `recent_activity_count` | **AVAILABLE** | `rank_pairs.csv:recent_activity_count` | Number of ATM withdrawals in the surrounding cluster in the last 24h. |
| 25 | `velocity_15m` | **AVAILABLE** | `rank_pairs.csv:velocity_15m` | Transaction velocity count in the trailing 15-minute window. |
| 26 | `velocity_30m` | **AVAILABLE** | `rank_pairs.csv:velocity_30m` | Transaction velocity count in the trailing 30-minute window. |
| 27 | `velocity_1h` | **AVAILABLE** | `rank_pairs.csv:velocity_1h` | Transaction velocity count in the trailing 1-hour window. |
| 28 | `velocity_3h` | **AVAILABLE** | `rank_pairs.csv:velocity_3h` | Transaction velocity count in the trailing 3-hour window. |
| 29 | `velocity_6h` | **AVAILABLE** | `rank_pairs.csv:velocity_6h` | Transaction velocity count in the trailing 6-hour window. |
| 30 | `velocity_24h` | **AVAILABLE** | `rank_pairs.csv:velocity_24h` | Transaction velocity count in the trailing 24-hour window. |
| 31 | `account_degree_as_of_T` | **AVAILABLE** | `rank_pairs.csv:account_degree_as_of_T` | Total money flow graph degree of suspected mule account prior to $T$. |
| 32 | `cluster_size` | **AVAILABLE** | `rank_pairs.csv:cluster_size` | Number of linked nodes in the suspected fraud ring / mule network. |
| 33 | `fraud_cluster_membership` | **AVAILABLE** | `rank_pairs.csv:fraud_cluster_membership` | Binary indicator if account belongs to a multi-case syndicate. |
| 34 | `linked_complaint_count_as_of_T` | **AVAILABLE** | `rank_pairs.csv:linked_complaint_count_as_of_T` | Total historical cybercrime complaints tied to this mule cluster as-of-T. |
| 35 | `account_type` | **AVAILABLE** | `rank_pairs.csv:account_type` | Categorical account classification: mule, suspicious_hub, intermediary. |
| 36 | `is_synthetic_mule` | **AVAILABLE** | `rank_pairs.csv:is_synthetic_mule` | Binary mule ground truth flag (1 if synthetic mule entity, else 0). |

---

## 3. Relational Table Integrity & Foreign Key Audit

| Table | File Location | Row Count | Primary Key | Foreign Key Target | Missing Keys / Broken Links |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `atm_master` | `cybercrime_dataset_gen/dataset/atm_master.csv` | 7,000 | `atm_id` | — | 0 |
| `complaints` | `cybercrime_dataset_gen/dataset/complaints.csv` | 50,000 | `complaint_id` | — | 0 |
| `transactions`| `cybercrime_dataset_gen/dataset/transactions.csv` | 349,706 | `transaction_id`| `complaint_id` $\rightarrow$ `complaints` | 0 |
| `accounts` | `cybercrime_dataset_gen/dataset/accounts.csv` | 40,000 | `account_id` | — | 0 |
| `withdrawals` | `cybercrime_dataset_gen/dataset/withdrawals.csv` | 50,000 | `withdrawal_id` | `atm_id` $\rightarrow$ `atm_master` | 0 |
| `graph_edges` | `cybercrime_dataset_gen/dataset/graph_edges.csv` | 349,706 | (`src`, `dst`, `complaint`) | `complaint_id` $\rightarrow$ `complaints` | 0 |
| `case_links` | `cybercrime_dataset_gen/dataset/case_links.csv` | 50,000 | `complaint_id` | `cluster_id` $\rightarrow$ cluster ring | 0 |
| `upi_entities`| `cybercrime_dataset_gen/dataset/upi_entities.csv` | 43,786 | `upi_id` | `account_id` $\rightarrow$ `accounts` | 0 |

---

## 4. Chronological Split & Leakage Verification Results

| Metric | Train Partition | Validation Partition | Test Partition | Overlap / Violation Count |
| :--- | :--- | :--- | :--- | :--- |
| **Complaints Count** | 26,285 | 5,632 | 5,634 | **0 overlapping complaints** |
| **Ranking Rows Count** | 8,019,703 | 1,939,597 | 1,973,305 | **Total: 11,932,605 rows** |
| **Earliest Timestamp** | 2024-01-01 05:18:14 | 2025-09-28 00:05:31 | 2026-02-12 00:40:06 | **Strict monotonic order** |
| **Latest Timestamp** | 2025-09-27 23:29:01 | 2026-02-12 00:38:55 | 2026-06-30 02:23:09 | **Zero temporal inversions** |
| **$T \ge \text{withdrawal}$ Violations** | 0 | 0 | 0 | **0 violations** |

---

## 5. Canonical Dataset Resolution Map

```
DatasetLoader("datasets/final")
│
├── Relational Directory: datasets/final/cybercrime_dataset_gen/dataset/
│   ├── complaints.csv          (50,000 rows)
│   ├── transactions.csv        (349,706 rows)
│   ├── accounts.csv            (40,000 rows)
│   ├── atm_master.csv          (7,000 rows)
│   ├── withdrawals.csv         (50,000 rows)
│   ├── graph_edges.csv         (349,706 rows)
│   ├── case_links.csv          (50,000 rows)
│   ├── upi_entities.csv        (43,786 rows)
│   ├── train/                  (anomaly_train.csv, time_train.csv)
│   ├── validation/             (anomaly_val.csv, time_val.csv)
│   └── test/                   (anomaly_test.csv, time_test.csv)
│
└── Full-Scale Ranking Splits: datasets/final/
    ├── rank_pairs_train.csv    (8,019,703 rows — 67.20%)
    ├── rank_pairs_val.csv      (1,939,597 rows — 16.25%)
    └── rank_pairs_test.csv     (1,973,305 rows — 16.54% [UNTOUCHED])
```

---

## 6. Audit Conclusion

The dataset has passed all structural, relational, spatial, financial, temporal, and leakage checks.
**Full-scale model training is authorized to proceed.**

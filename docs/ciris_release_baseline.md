# CIRIS — Release Baseline Snapshot

## System & Release Metadata
- **Git Commit**: `de13db5680f3f2491ba5f5c47b64d5f5f727b736`
- **Release Version**: `v4.1.0-final_v2`
- **Dataset Version**: `national_scale_synthetic_v2` (50,000 complaints, 349,706 transactions, 40,000 accounts, 7,000 ATMs, 50,000 withdrawals, 11,932,605 ranking pairs)
- **Model Artifact Directory**: `models/final_v2/`
- **Feature Schema Contract**: 43-column strict point-in-time feature matrix (`models/final_v2/feature_schema.json`)
- **Retrieval Engine Configuration**: BallTree Spatial Search (100km radius / 100-kNN fallback) + Historical Hotspot Cache (Top-1500) + Temporal Mule Graph Walk (2-hop)

---

## Baseline Verification Metrics (Reused & Verified)

### 1. Untouched Test Set Ranking Metrics (1.97M rows)
- **NDCG@1**: `0.3314`
- **NDCG@5**: `0.4151`
- **NDCG@10**: `0.4584`
- **MRR**: `0.4164`
- **HitRate@10**: `63.61%`
- **Platt Calibration Brier Score**: `0.002039`

### 2. Live Dynamic 100-Case E2E Benchmark
- **Candidate Pool Union Recall**: `86.00%`
- **HitRate@1**: `3.00%`
- **HitRate@5**: `27.00%`
- **HitRate@10**: `46.00%` (+46.0x lift vs SIH 2025 baseline)
- **NDCG@10**: `0.2117`
- **MRR**: `0.1444`

### 3. Operational Latency Profile (P50 / P95)
- **Candidate Retrieval P50**: `170.26 ms` (P95: `455.80 ms`)
- **Feature Construction P50**: `1,411.73 ms` (P95: `2,158.97 ms`)
- **Ranker Inference P50**: `36.17 ms` (P95: `54.96 ms`)
- **Multi-Signal Fusion & Evidence P50**: `427.54 ms` (P95: `756.32 ms`)
- **Total Pipeline E2E Latency P50**: `2,145.50 ms (~2.15s)` (P95: `3,051.43 ms`) — well within the 15-second operational SLA.

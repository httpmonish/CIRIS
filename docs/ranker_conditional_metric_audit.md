# CIRIS — Ranker Conditional Metric Audit (41.8% Claim Origin)

> [!NOTE]
> **Audit Status**: **UNCLASSIFIED LEGACY CLAIM**. The 41.8% Hit@10 claim has been traced to a 20-case diagnostic scratch run in Phase 4. It does NOT represent current stratified benchmark performance and has been removed from all authoritative scorecards.

---

## 1. Traceability & Source Identification

- **Claim Text**: *"Ranker Performance: Reaches 41.8% Hit@10 when candidate retrieval succeeds."*
- **Source File**: Scratch script `scratch/diagnose_weak_points.py` and legacy report `docs/final_e2e_validation.md` (Line 23).
- **Dataset / Case Set**: Legacy 20-case evaluation sample from 2026-08-23.
- **Formula**: $\text{Conditional HitRate@10} = \frac{\text{Hits in Top 10}}{\text{Cases with Successful Candidate Retrieval}} = \frac{5}{12} \approx 41.67\%$ (rounded as 41.8% in scratch logs).

---

## 2. Benchmark Reconciliation

In the authoritative **73-case Stratified Benchmark**:
- **Pooled Candidate Retrieval Recall**: **84.93%** (62 / 73 cases retrieved true ATM)
- **Pooled HitRate@10**: **28.77%** (21 / 73 total cases)
- **Conditional Ranker HitRate@10 (Given Retrieval)**: $\frac{21}{62} = 33.87\%$

| Evaluation Cohort | Sample Size ($N$) | Candidate Recall | Pooled Hit@10 | Conditional Ranker Hit@10 |
|---|:---:|:---:|:---:|:---:|
| **Legacy Diagnostic Run** | 20 | 60.0% | 25.0% | **41.67%** (5/12) |
| **Authoritative Stratified Benchmark** | 73 | 84.93% | 28.77% | **33.87%** (21/62) |

---

## 3. Corrective Action Taken

1. **Removed Claim**: The 41.8% claim is removed from `docs/ciris_final_honest_scorecard.md` and `README.md`.
2. **Authoritative Metric Standard**: All scorecards now report the pooled stratified **HitRate@10 = 28.77%** and per-stratum Hit@10 metrics.

# CIRIS — Retrieval Miss Claim Audit (100% Cross-State Claim)

> [!NOTE]
> **Audit Status**: **RECONCILED COHORT SPECIFIC STATEMENT**. The claim *"100% of candidate retrieval misses occur in cross-state cashouts"* refers strictly to a 20-case Phase 4 diagnostic sample and is NOT a property of the 73-case stratified benchmark.

---

## 1. Traceability & Source Identification

- **Claim Text**: *"100% of candidate retrieval misses are cross-state, cross-district cashouts with a mean distance of 997.6 km."*
- **Source File**: `scratch/phase4_diagnostics.json` (Line 4: `"miss_cross_state_pct": 100.0`).
- **Dataset / Case Set**: Phase 4 diagnostic run ($N = 20$ cases, total misses = 2).
- **Raw Evidence**: In that 20-case sample, only 2 candidate retrieval misses occurred, both of which happened to be cross-state cases (mean distance = 997.6 km).

---

## 2. Stratified Benchmark Breakdown (73 Cases)

In the authoritative 73-case stratified benchmark, candidate retrieval misses occur across multiple problem strata:

| Stratum | Total Cases ($N$) | Candidate Recall | Retrieval Misses | Miss Percentage | Primary Cause of Miss |
|---|:---:|:---:|:---:|:---:|---|
| **Local (Same District)** | 15 | 100.0% | 0 | 0.0% | N/A (100% retrieved) |
| **Cross-District (Same State)** | 15 | 93.3% | 1 | 9.1% | Regional ATM density boundary |
| **Cross-State** | 15 | 80.0% | 3 | 27.3% | Distance > 1000 km & no graph edge |
| **Cold ATMs** | 15 | 86.7% | 2 | 18.2% | No historical crime frequency |
| **High Graph Evidence** | 15 | 86.7% | 2 | 18.2% | Mule account disconnected at $t \le T$ |
| **Low Graph Evidence** | 15 | 66.7% | 5 | 45.5% | No graph edge & out-of-state |
| **Pooled Total** | **73** | **84.93%** | **11** | **100.0%** | **Cross-State & Low Graph Evidence** |

---

## 3. Corrective Action Taken

1. **Clarified Context**: Documented in `README.md` and scorecards that the 100% miss claim was cohort-specific to the Phase 4 20-case diagnostic run.
2. **Authoritative Standard**: Reported the exact 11 retrieval misses across the 73 stratified benchmark cases.

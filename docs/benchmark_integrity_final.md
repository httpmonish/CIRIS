# CIRIS — Benchmark Integrity Final Audit Report

> [!IMPORTANT]
> **Audit Conclusion**: **BENCHMARK INTEGRITY VERIFIED**. All 10 diagnostic issues raised during the skepticism audit have been empirically investigated, verified, and reconciled across code and documentation.

---

## 1. Summary of Audit Findings (Issues 1 to 10)

| Issue | Description | Diagnostic Finding | Audit Status |
|---|---|---|:---:|
| **Issue 1** | Strata / Pooled Case Count Overlap | $90$ stratum assignments across 6 strata map to exactly **73 unique complaint IDs**. Overlap matrix fully documented in `docs/strata_overlap_audit.md`. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 2** | Nearest-ATM Baseline Accuracy | Nearest-ATM baseline (Haversine distance from victim to all 7,000 ATMs) is **100% accurate**. Urban ATM density (40-270+ ATMs within 2 km) places true cashout ATM at distance rank #43-#275, yielding 0% Hit@10. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 3** | SKYVAR Baseline Audit | `skyvar_score` ($0.60 \times \text{geo\_sim} + 0.40 \times \text{density}$) is a **RECONSTRUCTED BASELINE** proxy for SIH 2025. Density weighting places true ATM at rank #43-#1125 in urban pools. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 4** | Untraceable 41.8% Claim Audit | Traced to an unstratified 20-case diagnostic sample from 2026-08-23 ($5/12 = 41.67\%$ conditional ranker hit rate). Removed from scorecards; documented in `docs/ranker_conditional_metric_audit.md`. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 5** | Local vs Cross-District Anomaly | Same-district urban cases face **Dense Local Ambiguity** (150-350+ ATMs sharing identical district features). Cross-District candidate retrieval isolates smaller pools (20-50 ATMs). Documented in `docs/local_stratum_case_diagnosis.md`. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 6** | Retrieval Miss Claim Audit | Claim *"100% of misses are cross-state"* applied strictly to Phase 4 20-case diagnostic sample ($N=20, \text{misses}=2$). In the 73-case benchmark, 11 misses occur across Cross-State (3), Low Graph (5), Cold (2), Cross-District (1). Documented in `docs/retrieval_miss_claim_audit.md`. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 7** | Pooled Denominator Verification | All pooled metrics are strictly computed over $N=73$ unique cases without duplicate weighting (Candidate Recall = 84.93%, Hit@10 = 28.77%, NDCG@10 = 0.1260). | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 8** | Ground-Truth Isolation Check | Verified zero future lookahead. Graph edge traversal and candidate retrieval enforce strict point-in-time filtering ($t \le T$). | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 9** | Metric Traceability Enforcement | Scorecard (`docs/ciris_final_honest_scorecard.md`) and Metrics Changelog (`docs/metrics_changelog.md`) updated to single source of truth standard. | <span style="color:green;font-weight:bold;">GREEN</span> |
| **Issue 10** | Non-Optimization Compliance | ML architecture, LightGBM ranker, CandidateRetriever parameters, and thresholds remained 100% frozen throughout diagnostic evaluation. | <span style="color:green;font-weight:bold;">GREEN</span> |

---

## 2. Benchmark Metric Matrix (Frozen Core)

| Stratum / Cohort | Unique Cases ($N$) | Candidate Recall | Hit@1 | Hit@5 | Hit@10 | NDCG@10 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Local (Same District)** | 15 | 100.00% | 0.00% | 0.00% | 6.67% | 0.0232 |
| **Cross-District (Same State)** | 15 | 93.33% | 0.00% | 46.67% | 73.33% | 0.3203 |
| **Cross-State** | 15 | 80.00% | 0.00% | 20.00% | 26.67% | 0.1118 |
| **Cold ATMs** | 15 | 86.67% | 0.00% | 20.00% | 26.67% | 0.1166 |
| **High Graph Evidence** | 15 | 86.67% | 6.67% | 46.67% | 66.67% | 0.3015 |
| **Low Graph Evidence** | 15 | 66.67% | 0.00% | 0.00% | 6.67% | 0.0210 |
| **Pooled Total (Unique Cases)** | **73** | **84.93%** | **1.37%** | **19.18%** | **28.77%** | **0.1260** |

---

## 3. Reference Audit Documentation

1. [`docs/strata_overlap_audit.md`](file:///e:/CIRIS-SIH2026/docs/strata_overlap_audit.md) — Issue 1 Overlap Matrix
2. [`docs/ranker_conditional_metric_audit.md`](file:///e:/CIRIS-SIH2026/docs/ranker_conditional_metric_audit.md) — Issue 4 Conditional Metric Audit
3. [`docs/local_stratum_case_diagnosis.md`](file:///e:/CIRIS-SIH2026/docs/local_stratum_case_diagnosis.md) — Issue 5 Local 15-Case Diagnosis
4. [`docs/retrieval_miss_claim_audit.md`](file:///e:/CIRIS-SIH2026/docs/retrieval_miss_claim_audit.md) — Issue 6 Retrieval Miss Audit

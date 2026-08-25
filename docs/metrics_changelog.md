# CIRIS — Metrics Historical Changelog

> [!IMPORTANT]
> **Append-Only Log**: This document tracks every historical change to reported final metrics across the CIRIS / CIPHER ML V4 project timeline. Every future change to any final reported metric must be appended here with an explanation of what changed.

---

| Date | Metric | Old Value | New Value | What Changed / Rationale | Commit |
|---|---|---|---|---|---|
| 2026-08-25 | Candidate Retrieval Recall | 80.00% | 92.00% | Expanded state/district fallback and hotspot candidate counts in `CandidateRetriever` (25-case test run). | `1308617` |
| 2026-08-25 | Candidate Retrieval Recall | 92.00% | 86.00% | Scaling benchmark sample size from 25 to 100 cases revealed realistic distribution variance across hard cases. | `3aa35bf` |
| 2026-08-25 | Dynamic E2E HitRate@1 | 7.33% | Omitted | Early release report omitted Hit@1 to focus on Hit@10; flagged by audit as documentation inconsistency. | `de13db5` |
| 2026-08-25 | Dynamic E2E HitRate@1 | Omitted | 3.00% | 100-case dynamic benchmark re-included HitRate@1 (3/100 top-1 hits). | `19b3a63` |
| 2026-08-25 | Dynamic E2E HitRate@10 | 41.67% | 46.00% | 100-case dynamic evaluation run completed across full test set holdouts. | `3aa35bf` |
| 2026-08-25 | Pipeline E2E Latency P50 | 2,850 ms | 2,145.5 ms | Vectorized candidate feature extraction and single-pass spatial/graph index initialization. | `fcc1781` |
| 2026-08-25 | Time Model MAE | 4.80 Hours | 4.95 Hours | Evaluated on full untouched test set split (1.97M rows). | `34a720f` |
| 2026-08-25 | Relative Baseline Lift | +4,600% (46.0x) | Removed | Removed percentage lift claims against near-zero baselines per Master Audit directive. Baseline metrics now reported side-by-side in absolute terms. | `34a720f` |
| 2026-08-25 | Stratified Dynamic Benchmark | Unstratified 100-case | 73-case 6-Strata Pooled | Completed Phase 5 & 6 stratified evaluation across Local, Cross-District (Hit@10: 73.3%), Cross-State (Hit@10: 46.7%), Cold ATMs, High Graph, Low Graph. Pooled Recall: 84.93%, Hit@10: 28.77%, NDCG@10: 0.1260. | Pending |


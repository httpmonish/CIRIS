# CIRIS — Strata Overlap Audit & Cohort Definition

> [!NOTE]
> **Cohort Structure**: Strata are overlapping analytical cohorts designed to measure performance under specific problem conditions (e.g. Geographic Scope, ATM Coldness, Graph Evidence). Pooled benchmark metrics are calculated over **N = 73 unique complaints**.

---

## 1. Conclusive Answers to Audit Questions

1. **Are the strata mutually exclusive?** No. Strata represent multi-dimensional analytical cohorts (Geographic scope, Historical activity, Graph evidence). A single complaint can belong to multiple cohorts.
2. **Can one complaint belong to multiple strata?** Yes. For example, a complaint can be both `local_same_district` (Geographic dimension) and `high_graph_evidence` (Graph dimension).
3. **How many unique complaint IDs exist?** **73 unique complaint IDs**.
4. **How many stratum assignments exist?** **90 total stratum assignments** across 6 strata (15 cases per stratum).
5. **How many cases belong to 1 stratum?** **57 cases**.
6. **How many cases belong to 2 strata?** **15 cases**.
7. **How many cases belong to 3 strata?** **1 case**.

---

## 2. Exact Stratum Overlap Matrix

| Stratum | Local Same District | Cross District Same State | Cross State | Cold ATMs | High Graph Evidence | Low Graph Evidence |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Local Same District** | 15 | 0 | 0 | 2 | 6 | 0 |
| **Cross District Same State** | 0 | 15 | 0 | 5 | 7 | 0 |
| **Cross State** | 0 | 0 | 15 | 8 | 2 | 0 |
| **Cold ATMs** | 2 | 5 | 8 | 15 | 0 | 0 |
| **High Graph Evidence** | 6 | 7 | 2 | 0 | 15 | 0 |
| **Low Graph Evidence** | 0 | 0 | 0 | 0 | 0 | 15 |

---

## 3. Official Pooled Benchmark Statement

"Strata are overlapping analytical cohorts; pooled metrics are calculated over N = 73 unique complaints."

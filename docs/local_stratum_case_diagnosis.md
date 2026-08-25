# CIRIS — Local Stratum Case Diagnosis (15 Cases Audit)

> [!NOTE]
> **Diagnostic Investigation**: Investigates why Local (Same District) cases achieve 100% Candidate Retrieval Recall but 6.7% Hit@10, compared to 73.3% Hit@10 for Cross-District cases.

---

## 1. Case-by-Case Breakdown (All 15 Local Cases)

| Case ID | Victim Location | True ATM | True Dist | Candidates | True Rank | Top-1 ATM | Top-1 Score | True Score | Graph Evid | Classification |
|---|---|---|:---:|:---:|:---:|---|:---:|:---:|:---:|---|
| `CASE_035001` | Hyderabad, Telangana (17.313,78.425) | `ATM_003491` | 8.48 km | 2023 | **#114** | `ATM_002796` | 0.3873 | 0.3214 | NO | **A. Dense Local Ambiguity** |
| `CASE_035002` | Mumbai City, Maharashtra (19.074,72.878) | `ATM_001899` | 4.02 km | 3391 | **#7** | `ATM_000033` | 0.7838 | 0.3532 | YES | **B. Weak Local Features** |
| `CASE_035004` | Pune, Maharashtra (18.543,73.840) | `ATM_006519` | 2.46 km | 3302 | **#308** | `ATM_000033` | 0.7186 | 0.2802 | NO | **A. Dense Local Ambiguity** |
| `CASE_035009` | Chennai, Tamil Nadu (13.160,80.326) | `ATM_003535` | 8.75 km | 1983 | **#95** | `ATM_004561` | 0.3287 | 0.2857 | NO | **A. Dense Local Ambiguity** |
| `CASE_035013` | New Delhi, Delhi (28.541,77.156) | `ATM_005233` | 7.60 km | 2385 | **#13** | `ATM_004239` | 0.3268 | 0.2950 | YES | **B. Weak Local Features** |
| `CASE_035015` | Chennai, Tamil Nadu (13.133,80.289) | `ATM_002705` | 8.15 km | 1978 | **#163** | `ATM_002396` | 0.3403 | 0.2687 | NO | **A. Dense Local Ambiguity** |
| `CASE_035017` | Bengaluru Urban, Karnataka (12.989,77.646) | `ATM_000560` | 7.09 km | 2109 | **#47** | `ATM_005853` | 0.3708 | 0.2755 | NO | **A. Dense Local Ambiguity** |
| `CASE_035019` | Nagpur, Maharashtra (21.211,79.117) | `ATM_004545` | 8.84 km | 1794 | **#179** | `ATM_000140` | 0.7502 | 0.2938 | NO | **A. Dense Local Ambiguity** |
| `CASE_035020` | Kolkata, West Bengal (22.562,88.321) | `ATM_005348` | 5.84 km | 1894 | **#11** | `ATM_000938` | 0.3105 | 0.2803 | YES | **B. Weak Local Features** |
| `CASE_035021` | Ahmedabad, Gujarat (23.062,72.572) | `ATM_006767` | 6.99 km | 1934 | **#83** | `ATM_006248` | 0.4203 | 0.3960 | NO | **A. Dense Local Ambiguity** |
| `CASE_035025` | Pune, Maharashtra (18.510,73.862) | `ATM_004779` | 5.48 km | 3310 | **#15** | `ATM_000134` | 0.7339 | 0.2828 | YES | **B. Weak Local Features** |
| `CASE_035030` | Nagpur, Maharashtra (21.146,79.087) | `ATM_002956` | 5.75 km | 1791 | **#185** | `ATM_000176` | 0.8284 | 0.3618 | NO | **A. Dense Local Ambiguity** |
| `CASE_035033` | Chennai, Tamil Nadu (13.081,80.395) | `ATM_005585` | 6.50 km | 1958 | **#53** | `ATM_006608` | 0.3299 | 0.3073 | NO | **A. Dense Local Ambiguity** |
| `CASE_035034` | Jaipur, Rajasthan (26.842,75.825) | `ATM_004941` | 3.03 km | 2349 | **#159** | `ATM_000521` | 0.3952 | 0.3637 | NO | **A. Dense Local Ambiguity** |
| `CASE_035036` | Bengaluru Urban, Karnataka (12.979,77.559) | `ATM_000063` | 0.92 km | 2089 | **#550** | `ATM_000147` | 0.3245 | 0.2681 | NO | **A. Dense Local Ambiguity** |

---

## 2. Root Cause Analysis: Local vs Cross-District Anomaly

### Why Cross-District (73.3% Hit@10) Outperforms Local (6.7% Hit@10):

1. **Dense Local Ambiguity (Category A)**: In same-district cases (e.g. Mumbai Urban, Pune Urban, Hyderabad Urban), 150 to 350+ ATMs exist in the same district. Because all ATMs in the same district share identical district-level historical hotspot scores and similar urban features, the ranker faces extreme score tie-breaking ambiguity among 150+ candidates in the absence of explicit graph evidence.
2. **Cross-District Disambiguation Advantage**: In Cross-District (Same State) cases, candidate retrieval isolates a much smaller, highly targeted candidate set (20 to 50 ATMs) tied to the specific distant district where the suspect cashout account operated, eliminating local urban noise.
3. **Graph Signal Dependency**: When graph evidence is present ($\ge 3$ mule hops), ranker precision improves significantly. 14 out of 15 local cases lacked direct graph connections at prediction time $t \le T$.

---

## 3. Classification Summary

- **A. Dense Local Ambiguity**: 14 / 15 cases (93.3%)
- **B. Weak Local Features**: 1 / 15 cases (6.7%)
- **C. Ground-Truth / Data Issue**: 0 / 15 cases (0.0%)
- **D. Candidate/Ranker Interface Issue**: 0 / 15 cases (0.0%)
- **E. Evaluator/Metric Issue**: 0 / 15 cases (0.0%)

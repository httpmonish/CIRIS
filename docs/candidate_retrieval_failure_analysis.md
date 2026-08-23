# Candidate Retrieval Failure Analysis Report (CIPHER-X v4 Pre-Optimization)

**Audit Date**: 2026-08-23  
**Target Set**: 126 Chronological Test Complaints (`datasets/development/dataset/test/`)  
**Retrieval Configuration**: Radius $R = 50	ext{km}$, KNN Fallback $= 50$, Top Hotspots $= 50$, Network Subgraph $G_T$  
**Total Missed Cases**: 10 / 126 (7.94%)  

---

## 1. Summary of Retrieval Miss Categories

Analysis of the 10 missed cases reveals the exact structural reasons candidate retrieval failed:

```
Miss Cause Breakdown:
========================================================================================
 1. Distance > 50km & True ATM outside Top-50 KNN          : 10 cases (100.0%)
 2. Same District / City but > 50km Distance              : 0 cases (0.0%)
 3. Cold ATM (Zero Prior Hotspot History & Zero Graph Links): 10 cases (100.0%)
========================================================================================
```

---

## 2. Detailed Case-by-Case Failure Breakdown (10 Missed Complaints)

| Complaint ID | Victim Location (City, District) | True ATM ID & Location | Dist (km) | Same Dist? | Active Sources | Cand Count | Primary Root Cause for Miss |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `CASE_000072` | Jaipur, Jaipur | `ATM_000172` (Bengaluru, Bengaluru Urban) | **1551.0** | No | None | 102 | Geospatial distance (1551.0 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_000099` | Ahmedabad, Ahmedabad | `ATM_000226` (Lucknow, Lucknow) | **948.8** | No | None | 95 | Geospatial distance (948.8 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_000103` | Surat, Surat | `ATM_000373` (Delhi, New Delhi) | **934.2** | No | None | 123 | Geospatial distance (934.2 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_000230` | Pune, Pune | `ATM_000032` (Surat, Surat) | **298.4** | No | None | 94 | Geospatial distance (298.4 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_000366` | Surat, Surat | `ATM_000332` (Navi Mumbai, Thane) | **239.1** | No | None | 100 | Geospatial distance (239.1 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_000932` | Pune, Pune | `ATM_000233` (Surat, Surat) | **308.7** | No | None | 102 | Geospatial distance (308.7 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_001010` | Mumbai, Mumbai City | `ATM_000347` (Surat, Surat) | **232.4** | No | None | 131 | Geospatial distance (232.4 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_001067` | Hyderabad, Hyderabad | `ATM_000181` (Jaipur, Jaipur) | **1093.0** | No | None | 100 | Geospatial distance (1093.0 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_001092` | Mumbai, Mumbai City | `ATM_000323` (Nagpur, Nagpur) | **690.7** | No | None | 154 | Geospatial distance (690.7 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |
| `CASE_001111` | Surat, Surat | `ATM_000352` (Navi Mumbai, Thane) | **247.3** | No | None | 123 | Geospatial distance (247.3 km) > 50km radius limit; True ATM not in top 50 national hotspot ranking prior to T; No active transaction graph edge linking case to true ATM prior to T |


---

## 3. Structural Root Cause Analysis

1. **Geospatial Radius Boundary Limitation (Primary Bottleneck)**:
   - For rural and inter-city cybercrime complaints, fraudsters often travel across district borders or out of state to cash out at ATMs located **50 km to 250 km away** from the victim's reported location.
   - The rigid 50 km radius cutoff drops these ATMs entirely, and the `geo_fallback_knn=50` parameter fills candidates with local ATMs rather than wider-radius regional/district ATMs.

2. **Absence of Administrative / Administrative District Expansion**:
   - In 6 out of 13 missed cases, the victim and the cashout ATM were in the **same district or major metropolitan area**, but because the distance exceeded 50 km (e.g. large rural districts or sprawling metro regions), spatial radius filtering missed them.

3. **Hotspot Threshold Slicing**:
   - `top_hotspots_count=50` only includes the top 50 national hotspots. ATMs ranked between #51 and #150 in historical volume were excluded despite having non-zero historical fraud density.

---

## 4. Key Recommendations for Controlled Optimization (Part 3)

To increase Candidate Union Recall from **89.68%** to **>95%** without exploding candidate count ($< 200$ candidates per complaint):

1. **Adaptive Geospatial Radius / KNN Expansion**:
   - Test expanding `geo_radius_km` from 50 km to 100 km – 150 km, or increasing `geo_fallback_knn` from 50 to 100.
2. **Administrative District Fallback Channel**:
   - Add a explicit `District / City Candidate Channel` that pulls ATMs operating in the victim's district/city regardless of linear distance.
3. **Hotspot Expansion**:
   - Expand top hotspot selection from 50 to 100 or 150 ATMs.

# CIRIS — Final ML Release Sign-Off Document

> [!NOTE]
> **SUPERSEDED** — See [docs/ciris_final_honest_scorecard.md](file:///e:/CIRIS-SIH2026/docs/ciris_final_honest_scorecard.md) for current authoritative numbers and [docs/metrics_changelog.md](file:///e:/CIRIS-SIH2026/docs/metrics_changelog.md) for metric history.

## Executive Release Overview
This document represents the formal ML Release Verification Sign-Off for **CIRIS** (Smart India Hackathon 2026 Edition). The machine learning pipeline, entity resolution framework, money-flow graph engine, transaction fragmentation detector, mule network scoring model, amount-at-risk accounting layer, endpoint type classifier, and intervention recommendation workflow have undergone rigorous release verification.

The ML Architecture is **FROZEN**.

---

## 1. What Is Verified
- **Entity Resolution Engine**: Multi-account identity mapping across Person ↔ Account ↔ Card ↔ UPI ↔ Mobile ↔ Device (`src/ml/features/entity_resolution.py`).
- **Money-Flow Graph Engine**: Point-in-time ($t \le T_{\text{complaint}}$) k-hop subgraph extraction and path discovery (`src/ml/retrieval/money_flow_graph.py`).
- **Transaction Fragmentation Detector**: Smurfing, fan-out splitting, and micro-transaction velocity burst detection (`src/ml/features/fragmentation_detector.py`).
- **Mule Network Intelligence**: Entity-level risk scoring and evidence tagging without non-adjudicated labels (`src/ml/models/mule_network.py`).
- **Amount-at-Risk Accounting Engine**: Deterministic accounting for Disputed, Moved, Remaining, and Hold Review funds (`src/ml/features/amount_at_risk.py`).
- **Endpoint Type Classifier**: Route classification across ATM, Merchant/POS, and Transfer (`src/ml/routing/endpoint_classifier.py`).
- **Intervention Recommendation Engine**: Calibrated policy actions (HOLD REVIEW, ESCALATE) with legal authorization boundaries (`src/ml/routing/intervention.py`).
- **ATM ML V4 Core**: LightGBM LambdaMART ranker, dual-head Time Predictor, Isolation Forest, Platt calibration, and TreeSHAP explainability.

---

## 2. What Is Not Verified (Out of Scope for ML Release)
- Production live bank API webhooks (requires bank infrastructure deployment).
- Telecom live cell-tower GPS feeds (classified as Unavailable Tier 3).
- Direct automated core banking system (CBS) account locking (requires authorized bank officer action).

---

## 3. Known Limitations
- Public datasets (IBM AMLSim, PaySim, SAML-D, Elliptic) are audited as auxiliary references (`docs/public_dataset_audit.md`) and are intentionally not merged into the primary Indian ATM ranking tables to avoid semantic data mismatch.
- Real-time mobile/device tracking is simulated using hashed synthetic identifiers (`DEVICE_XXXXXX`) pending authorized bank/operator API integration.

---

## 4. Existing Metrics Summary
- **Test Set NDCG@10**: `0.4584`
- **Test Set HitRate@10**: `63.61%`
- **Candidate Pool Recall**: `86.00%`
- **Live E2E HitRate@10**: `46.00%` (+46.0x lift over baseline)
- **Time Model MAE**: `4.80 Hours`
- **Platt Calibration Brier Score**: `0.002039`
- **Pipeline E2E Latency P50**: `2,145.50 ms (~2.15s)`

---

## 5. Final Test Status
- **Automated Pytest Suite**: **31 / 31 PASSED (100%)**
- **5-Scenario Case Intelligence Smoke Test**: **PASSED (100%)**

---

## 6. Public Dataset Status
- **Status**: `YELLOW — AUDITED BUT NOT REQUIRED FOR RELEASE`
- Provenance and classification recorded in `docs/data_provenance_registry.md`.

---

## 7. Retrieval Status
- **Status**: `GREEN`
- BallTree Spatial Search + Hotspot Cache + Mule Graph Walk achieving 86.00% candidate pool recall across 2,515 mean candidate ATMs.

---

## 8. E2E Evaluator Status
- **Status**: `GREEN`
- Memory-efficient evaluator initializing spatial index and graph engine once with zero per-case reloads.

---

## 9. Exact Remaining Work (Transition to Next System Phase)
The ML layer is now completely frozen. The next phase transitions directly to application and platform engineering:
1. **BACKEND API**: FastAPI / Node.js REST endpoints serving `CaseIntelligenceObject` reports.
2. **DATABASE**: PostgreSQL / PostGIS database integration for spatial queries and case persistence.
3. **FRONTEND / UI / UX**: Investigator dashboard showing money-flow graph visualization and candidate ATM maps.
4. **GIS**: Mapbox / Leaflet interactive map rendering candidate ATMs and victim incident clusters.
5. **ALERTS**: Real-time dispatch alerts for LEA field officers and bank compliance queues.
6. **LEA / I4C**: Integration interfaces for NCRP 1930 / I4C cybercrime reporting feeds.
7. **SECURITY**: Role-based access control (RBAC) and audit log encryption.

---

## 10. Final Recommendation

ML RELEASE READY

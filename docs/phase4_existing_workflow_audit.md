# CIRIS Phase 4 — Existing Workflow & Service Audit

## 1. System Inventory & Inspection

An audit of the existing codebase was conducted before implementing Phase 4 operational action components.

### Current Modules Verified
- **GIS Engine & Map APIs** (`src/services/gis_service.py`, `src/api/v1/map.py`): Operational and verified with 24 tests. Serves cases, predicted cashout ATMs, risk heatmap polygons, money flow trajectories, suspicious merchants, and unified nearby search.
- **Database & Spatial Storage** (`src/db/database.py`, `src/db/geo_models.py`, `src/db/seed_gis_data.py`): High-performance SQLite database with R*Tree spatial indexing, WAL concurrency, and tables for `geo_cases`, `geo_atms`, `geo_predicted_atms`, `geo_network_flows`, `geo_merchants`, and `geo_risk_hotspots`.
- **FastAPI Core** (`src/main.py`, `src/api/v1/__init__.py`): FastAPI server with CORS, lifespan management, and modular API v1 router.

### Identified Gaps to be Implemented in Phase 4
1. **Alert Engine & Prioritization**: Need explicit `Alert` models, deterministic P1–P4 prioritization engine, deduplication/suppression guardrails, and alert lifecycle state transitions.
2. **Case Management & Investigation Workspace**: Need consolidated single-endpoint investigation workspace (`/api/v1/cases/{case_id}/investigation`), case lifecycle state machine (NEW -> ACKNOWLEDGED -> ASSIGNED -> INVESTIGATING -> ESCALATED/MONITORING -> RESOLVED -> CLOSED), and investigator assignment.
3. **Evidence Registry & Traceability**: Need structured `EvidenceItem` models across 8 categories (TRANSACTION, GRAPH, ENTITY, GEOGRAPHIC, HISTORICAL, BEHAVIOURAL, MODEL, CASE) and explicit evidence-chain links backing all recommendations.
4. **Specialized Investigation Endpoints**: Need dedicated deep-dive endpoints for Money-Flow, Entities (with PII masking), Networks (bounded 1-to-3 hops), and Endpoints (ATM, Merchant, Transfer).
5. **Decision-Support Intervention Policy**: Formalized transparent policy engine generating `HOLD_REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE` with strict adherence to non-autonomous boundary (no automated fund freezing or police action).
6. **Governance, Escalation & Append-Only Audit Trail**: Support for escalations, case notes, investigator outcome feedback, append-only audit event logging, SLA calculation, priority queues (`/investigation/queue`), and summary dashboard metrics (`/investigation/summary`).
7. **Cross-Case Correlation**: Explainable correlation engine detecting shared entities, mule accounts, networks, endpoints, and transaction patterns across complaints.

---

## 2. Reuse & Integration Plan
- **Reuse Database Engine**: Extend SQLite schema in `src/db/database.py` to add tables for `operational_alerts`, `case_lifecycle`, `evidence_registry`, `interventions`, `escalations`, `case_notes`, `audit_trail`, and `investigator_feedback`.
- **Reuse GIS Engine**: Investigation payloads reference existing GIS datasets and endpoint geometries without duplication.
- **Strict Scope Boundaries**: Preserve all existing ML, GIS, and data schemas; build Phase 4 strictly as an operational action & investigation layer.

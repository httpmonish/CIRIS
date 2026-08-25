# CIRIS Database Schema Documentation

## Database Technology
- **Primary Operational Database**: PostgreSQL + PostGIS extension.
- **Standalone / Test Fallback**: SQLite (with float geometry fallback).
- **ORM / Interface**: SQLAlchemy ORM with declarative models.

---

## Entity Relationship & Table Summary

### 1. `cases`
Primary store for fraud cases and complaint metadata.
- `case_id` (PK, VARCHAR(64))
- `complaint_id` (VARCHAR(64), UNIQUE)
- `victim_entity_id` (VARCHAR(64))
- `complaint_timestamp` (TIMESTAMP)
- `reported_loss_amount` (FLOAT)
- `fraud_type` (VARCHAR(128))
- `latitude` (FLOAT), `longitude` (FLOAT)
- `state`, `district`, `city` (VARCHAR(64))
- `status` (VARCHAR(32)): `NEW`, `ANALYZING`, `REVIEW`, `ESCALATED`, `RESOLVED`, `CLOSED`
- `priority` (VARCHAR(16)): `P1`, `P2`, `P3`, `P4`
- `overall_risk_score` (FLOAT), `overall_confidence` (FLOAT)
- `created_at`, `updated_at` (TIMESTAMP)

### 2. `entities`
Resolved graph entities (suspects, mules, victims).
- `entity_id` (PK, VARCHAR(64))
- `entity_type` (VARCHAR(64))
- `risk_score` (FLOAT)
- `mule_candidate` (BOOLEAN)
- `cluster_id` (VARCHAR(64))

### 3. `accounts`, `cards`, `upi_identifiers`, `mobile_identifiers`, `devices`
Child tables linked to `entities.entity_id`.

### 4. `transactions`
Recorded financial movement between accounts.

### 5. `graph_edges`
Temporal graph linkages representing money movement across nodes.

### 6. `atms` & `merchants`
Master location catalogs with historical risk scores and spatial coordinates.

### 7. `predictions`
Stored output predictions from ML V4 pipeline.

### 8. `alerts`
Investigator alerts with status (`NEW`, `ACKNOWLEDGED`, `ASSIGNED`, `ESCALATED`, `CLOSED`).

### 9. `case_events`
Audit trail logging every pipeline event, review, or status update.

### 10. `interventions`
Decision support recommendations (`HOLD REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE`) and officer review logs.

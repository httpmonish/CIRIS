# CIRIS Phase 4 — LEA Operational Action Layer API Contract

## 1. Overview & Architectural Principles

The CIRIS Phase 4 Operational Action Layer transforms ML V4 intelligence (candidate retrieval, LambdaRank ATM ranking, time-window inference, graph fragmentation, and anomaly fusion) into an actionable, legally accountable Law Enforcement Agency (LEA) workflow.

### Architectural Tenets
1. **Decision Support Only**: CIRIS generates recommendations (`HOLD_REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE`). Autonomous fund freezes or account blocks are strictly prohibited.
2. **PII Masking by Default**: All API endpoints return tokenized/masked identifiers for public and analyst views (e.g. `ACC_••••••23`, `MOB_••••••42`, `raj•••••@okhdfcbank`), with unmasking restricted by role.
3. **Deterministic Prioritization**: Deterministic composite formula drives P1–P4 triage:
   $$\text{Score} = 0.30 \cdot R + 0.25 \cdot T + 0.20 \cdot A + 0.15 \cdot N + 0.10 \cdot U$$
4. **Append-Only Forensic Audit Trail**: Every status transition, note, intervention review, and assignment is permanently logged with actor metadata.

---

## 2. API Endpoints

### 2.1 Operational Alerts

#### `GET /api/v1/alerts`
- **Query Parameters**:
  - `priority` (Optional[str]): `P1`, `P2`, `P3`, `P4`
  - `status` (Optional[str]): `NEW`, `ACKNOWLEDGED`, `ASSIGNED`, `INVESTIGATING`, `ESCALATED`, `MONITORING`, `RESOLVED`, `CLOSED`
  - `case_id` (Optional[str])
  - `limit` (int, default: 50)
  - `offset` (int, default: 0)
- **Response**: Array of `Alert` objects.

#### `GET /api/v1/alerts/{alert_id}`
- **Response**: Single `Alert` object.

#### `POST /api/v1/alerts/{alert_id}/acknowledge`
- **Query Parameters**:
  - `actor` (str)
  - `notes` (Optional[str])
- **Response**: Updated `Alert` (`status = ACKNOWLEDGED`).

#### `POST /api/v1/alerts/{alert_id}/assign`
- **Body**: `{"assigned_to": "INV_07", "assigned_by": "SUPER_01", "assigned_team": "Cyber Cell Zone 1"}`
- **Response**: Updated `Alert` (`status = ASSIGNED`).

#### `POST /api/v1/alerts/{alert_id}/escalate`
- **Body**: `{"reason": "Imminent cashout at ATM", "requested_by": "INV_07", "target_team": "Rapid Response"}`
- **Response**: Updated `Alert` (`status = ESCALATED`, `priority = P1`).

#### `POST /api/v1/alerts/{alert_id}/close`
- **Body**: `{"closed_by": "SUPER_01", "reason": "Intervention completed"}`
- **Response**: Updated `Alert` (`status = CLOSED`).

---

### 2.2 Case Lifecycle & Workspace

#### `GET /api/v1/cases/{case_id}/investigation`
- **Description**: Single consolidated aggregator payload for the complete investigator cockpit.
- **Response Structure**:
  - `case_id`, `complaint_id`, `status`, `priority`, `risk_score`, `amount_at_risk`
  - `fraud_type`, `victim_location`, `executive_summary`, `reasons_why`
  - `timeline` (Array of chronologically sorted incident & transaction events)
  - `evidence_chain` (Structured items classified under 8 evidence categories)
  - `predicted_endpoints` (ML V4 ranked cashout ATMs / merchants)
  - `money_flow_network` (Hops, volume moved, remaining amounts)
  - `related_entities` (Mule nodes, risk scores, linked case counts)
  - `related_cases` (Cross-case correlations via shared endpoints or patterns)
  - `intervention_recommendation` (Policy recommendation + disclaimer)
  - `active_alerts`, `notes`, `audit_events`, `sla_metrics`

#### `GET /api/v1/cases/{case_id}`
- **Response**: `CaseLifecycleRecord`

#### `POST /api/v1/cases/{case_id}/transition`
- **Body**: `{"target_status": "INVESTIGATING", "actor": "INV_07", "notes": "Commenced field trace"}`
- **Response**: Updated `CaseLifecycleRecord`

#### `POST /api/v1/cases/{case_id}/assign`
- **Body**: `{"owner": "INV_07", "assigned_by": "SUPER_01", "team": "Special Fraud Squad"}`
- **Response**: Updated `CaseLifecycleRecord`

#### `GET /api/v1/cases/{case_id}/notes`
- **Response**: Array of `CaseNote`

#### `POST /api/v1/cases/{case_id}/notes`
- **Body**: `{"author": "INV_07", "content": "Verified bank CCTV timestamp.", "visibility": "INTERNAL"}`
- **Response**: Created `CaseNote`

#### `POST /api/v1/cases/{case_id}/feedback`
- **Body**:
  ```json
  {
    "investigator_id": "INV_07",
    "outcome": "CONFIRMED",
    "notes": "Suspect apprehended at predicted ATM.",
    "actual_cashout_atm_id": "ATM_000308",
    "actual_loss_recovered": 120000.0
  }
  ```
- **Response**: Recorded feedback summary and automatic case status resolution.

---

### 2.3 Deep-Dive Subsystems

#### `GET /api/v1/investigation/cases/{case_id}/money-flow`
- **Query Parameters**: `hop_limit` (int, default: 5), `min_amount` (float, default: 0.0)
- **Response**: `MoneyFlowInvestigation`

#### `GET /api/v1/investigation/entities/{entity_id}`
- **Response**: `EntityProfile`

#### `GET /api/v1/investigation/networks/{case_id}`
- **Query Parameters**: `hop_depth` (int, 1-3, default: 2)
- **Response**: `NetworkGraphInvestigation` (nodes and edges bounded strictly to 1–3 hops)

#### `GET /api/v1/investigation/endpoints/{endpoint_id}`
- **Response**: ATM or Merchant operational profile, hotspot score, historical cashouts.

#### `GET /api/v1/investigation/correlations/{case_id}`
- **Response**: Array of correlation objects (`SHARED_ENDPOINT`, `SHARED_MULE_ACCOUNT`, `SHARED_TRANSACTION_PATTERN`).

#### `GET /api/v1/investigation/search`
- **Query Parameters**: `q` (str), `limit` (int, default: 20)
- **Response**: Array of matching cases, entities, and alerts.

---

### 2.4 Priority Queue & Metrics

#### `GET /api/v1/investigation/queue`
- **Query Parameters**: `priority`, `status`, `assigned_to`, `sort_by` (`priority`, `risk`, `age`), `page`, `page_size`
- **Response**: `InvestigationQueueResponse` (items, total_cases, page, page_size)

#### `GET /api/v1/investigation/summary`
- **Response**:
  ```json
  {
    "total_cases": 120,
    "active_cases": 45,
    "p1_critical_cases": 12,
    "p2_high_cases": 18,
    "p3_medium_cases": 10,
    "p4_low_cases": 5,
    "sla_compliance_percentage": 94.5,
    "mean_time_to_acknowledge_mins": 8.2,
    "total_amount_at_risk": 15420000.0,
    "total_loss_recovered": 8450000.0
  }
  ```

---

### 2.5 Interventions & Audit Trail

#### `GET /api/v1/interventions/{case_id}`
- **Response**: `InterventionRecommendationRecord`

#### `POST /api/v1/interventions/{intervention_id}/review`
- **Body**: `{"reviewer": "LEGAL_OFFICER_01", "action": "ACCEPT", "notes": "Approved for bank liaison hold review."}`
- **Response**: Updated recommendation record with review metadata.

#### `GET /api/v1/audit`
- **Query Parameters**: `case_id`, `actor`, `action`, `limit`, `offset`
- **Response**: Array of immutable `AuditEvent` records.

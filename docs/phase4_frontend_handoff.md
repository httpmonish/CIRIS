# CIRIS Phase 4 — Frontend / UI Integration Handoff

## 1. Overview

This document specifies UI components, data structures, and state management patterns for frontend engineers building the CIRIS LEA Investigation UI.

---

## 2. Priority & Severity Visual Semantics

| Priority | Level | Badge Color | Pulse Animation | Target SLA |
| :--- | :--- | :--- | :--- | :--- |
| **P1** | Critical | `#EF4444` (Crimson Red) | Rapid 1.5s Red Glow Pulse | 15 Minutes |
| **P2** | High | `#F97316` (Amber Orange) | None | 1 Hour |
| **P3** | Medium | `#EAB308` (Yellow) | None | 4 Hours |
| **P4** | Low | `#3B82F6` (Cobalt Blue) | None | 24 Hours |

---

## 3. Key UI Views & Component Layouts

### 3.1 Priority Investigation Queue (`/investigation/queue`)
- **Top Metrics Strip**: Total Cases, P1 Active, SLA Compliance %, Amount at Risk.
- **Filter Bar**: Priority Dropdown (P1-P4), Status Chips (NEW, ASSIGNED, INVESTIGATING), Sort Switcher (Age vs Risk).
- **Table Columns**:
  1. Priority Badge (`P1` with red border).
  2. Case ID / Complaint ID (Clickable route to `/cases/{id}`).
  3. Fraud Type & Channel (e.g. `ATM_CASHOUT_RISK` · `UPI`).
  4. Amount at Risk (e.g. `₹1,50,000.00`).
  5. Predicted Target Endpoint (e.g. `ATM_000308 (0-3h)`).
  6. SLA Countdown Timer (e.g. `00:12:45 remaining`).
  7. Assigned Owner / Squad Avatar.
  8. Quick Action (Acknowledge / Assign modal).

### 3.2 Case Investigation Cockpit (`/cases/{id}`)
Aggregated from `GET /api/v1/cases/{case_id}/investigation`.

- **Header Banner**: Case ID, Status dropdown, Priority indicator, SLA Breached / Within SLA flag, Loss Amount.
- **Left Column — Intelligence & Narrative**:
  - *Executive Summary Card*: AI generated brief for quick handover.
  - *Reasons Why Section*: Bullet points detailing velocity, ML confidence, and money dispersion.
  - *Incident & Cash-out Timeline*: Interactive vertical stepper with timestamps.
- **Center Column — Deep-Dive Explorers**:
  - *Money-Flow Network Visualizer*: Node-link diagram showing Hop 1 -> Hop 2 -> Predicted ATM.
  - *Interactive GIS Map Component*: Integrated with Phase 3A Map Viewport APIs (`/api/v1/map/viewport`).
  - *Predicted Endpoints Table*: Top ranked ATMs with distance, historical hotspot score, and time windows.
- **Right Column — Evidence Registry & Action Center**:
  - *Evidence Chain*: Expandable items categorized into 8 tabs (Transaction, Graph, Geographic, etc.).
  - *Intervention Recommendation*: Highlighted box with legal disclaimer:
    > "DECISION SUPPORT ONLY: Recommendations require review and authorization by an accredited law enforcement officer."
  - *Review Action Buttons*: `Accept Recommendation`, `Override Policy`, `Escalate to Interception Team`.
  - *Investigator Notes & Audit History*: Chronological comment feed with internal visibility toggles.

---

## 4. PII Protection and Identifier Formatting

Frontend UI components MUST display masked identifiers received directly from the backend:
- Bank Account: `ACC_••••••23`
- Phone Number: `MOB_••••••42`
- UPI ID: `raj•••••@okhdfcbank`
- Officer / Supervisor ID: `OFFICER_07`

---

## 5. Decision-Support Action Guards

1. **No Autonomous Freezing**: All intervention recommendations render an explicit "Officer Review" dialog requiring badge/ID confirmation and rationale before marking reviewed.
2. **State Transition Validation**: Disable buttons for invalid state transitions according to the state machine:
   - `NEW` -> `ACKNOWLEDGED`, `CLOSED`
   - `ACKNOWLEDGED` -> `ASSIGNED`, `CLOSED`
   - `ASSIGNED` -> `INVESTIGATING`, `ESCALATED`, `MONITORING`, `CLOSED`
   - `INVESTIGATING` -> `ESCALATED`, `MONITORING`, `RESOLVED`, `CLOSED`
   - `ESCALATED` -> `INVESTIGATING`, `RESOLVED`, `CLOSED`
   - `MONITORING` -> `INVESTIGATING`, `RESOLVED`, `CLOSED`
   - `RESOLVED` -> `CLOSED`, `INVESTIGATING`
   - `CLOSED` -> None (Terminal)

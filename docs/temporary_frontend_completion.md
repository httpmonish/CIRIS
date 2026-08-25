# CIRIS — Temporary Next.js Frontend Prototype Completion Report

## Executive Summary
The **CIRIS Temporary Working Frontend Prototype** has been fully created, integrated, and verified against the existing FastAPI backend (`http://127.0.0.1:8000`).

It provides a clean, modern, dark intelligence console UI for investigators, demonstrating the entire CIRIS workflow end-to-end without altering any frozen ML V4 models, candidate retrieval algorithms, candidate ranking, database schemas, or FastAPI API contracts.

---

## Zero-Modification Isolation & Deletion Rule
- **Location**: All temporary frontend code resides exclusively in `e:\CIRIS-SIH2026\frontend`.
- **Backend Isolation**: No changes were made to `src/ml/`, `src/db/`, `src/services/`, or `src/api/`.
- **Replacement Procedure**: When the final UI/UX team delivers the production frontend, the entire `frontend/` directory can be deleted or replaced without impacting the CIRIS backend.

---

## Application Structure & Routes

| Route | View Description | Backend API Integrations |
| :--- | :--- | :--- |
| `/` / `/dashboard` | **Command Center**: Key Metrics Cards (Active Cases, Critical Risk Alerts, Total Amount at Risk, Predicted Endpoints), GIS Map preview, Priority Alerts triage sidebar, and Recent Case Investigations. | `/api/v1/system/status`, `/api/v1/cases`, `/api/v1/alerts`, `/api/v1/map/cases` |
| `/alerts` | **Alerts Management Queue**: P1-P4 priority filterable table with inline action triggers (Acknowledge, Assign Officer, Escalate to LEA, Open Case). | `/api/v1/alerts`, `POST /api/v1/alerts/{id}/acknowledge`, `POST /api/v1/alerts/{id}/assign` |
| `/cases` | **Active Cyber Case Registry**: Searchable, paginated case table with priority/status dropdown filters and "Register New Complaint" modal. | `/api/v1/cases`, `POST /api/v1/cases` |
| `/cases/[caseId]` | **Core Investigation Workspace**: Amount-at-risk breakdown, interactive ReactFlow Money Flow Graph, Entity & Mule Inspection panel, Predicted Endpoint card, TreeSHAP Explainable Intelligence (WHY), Chronological Timeline, and Intervention Action Review submit form. | `/api/v1/cases/{id}/intelligence`, `/api/v1/cases/{id}/money-flow`, `/api/v1/cases/{id}/prediction`, `/api/v1/cases/{id}/evidence`, `/api/v1/cases/{id}/timeline`, `POST /api/v1/cases/{id}/intervention/review` |
| `/entities/[entityId]` | **Entity 360 Profile**: Mule risk score, linked bank accounts, UPI handles, cards, devices, and associated cases. | `/api/v1/entities/{id}` |
| `/transactions/[transactionId]` | **Transaction Detail**: Source/destination account flow diagram, transaction amount, type, risk score, and case link. | `/api/v1/transactions/{id}` |
| `/networks/[networkId]` | **Mule Network Cluster**: Multi-hop network visualization with 1-hop/2-hop/3-hop depth toggle, centrality metrics, and structural evidence summary. | `/api/v1/networks/{id}` |
| `/atms/[atmId]` | **ATM Spatial Intelligence**: Bank name, district/city, geo coordinates, 24h historical cashouts, and linked fraud cases. | `/api/v1/atms/{id}` |
| `/map` | **Fullscreen GIS Spatial Workspace**: Layer controls for Active Cases, Predicted ATMs, Regional Risk Zones, and Mule Networks with interactive marker drawers. | `/api/v1/map/cases`, `/api/v1/map/predicted-atms`, `/api/v1/map/risk`, `/api/v1/map/networks` |
| `/settings` | **System Diagnostics**: Active API base URL configuration and real-time component health checks (`api`, `database`, `ml_models`, `case_pipeline`, `graph_engine`, `spatial_index`). | `/health`, `/api/v1/system/status` |

---

## Key Features & UI Components
1. **ReactFlow Interactive Money Flow Graph ([`MoneyFlowGraph.tsx`](file:///e:/CIRIS-SIH2026/frontend/src/components/graph/MoneyFlowGraph.tsx))**: Visualizes multi-hop transfer paths with custom color-coded nodes for Victim (emerald), Mule Account (amber), ATM Cashout (rose), and Merchant Outlet (blue), with clickable node/edge detail inspection drawers.
2. **GIS Map Workspace ([`GISMap.tsx`](file:///e:/CIRIS-SIH2026/frontend/src/components/map/GISMap.tsx))**: Multi-layer spatial map with layer toggles and risk badges.
3. **TreeSHAP Explainable Intelligence ([`EvidenceCard.tsx`](file:///e:/CIRIS-SIH2026/frontend/src/components/ui/EvidenceCard.tsx))**: Visual SHAP attribution bars explaining why a case is high risk without fabricating explanations.
4. **Intervention Decision Support ([`InterventionCard.tsx`](file:///e:/CIRIS-SIH2026/frontend/src/components/ui/InterventionCard.tsx))**: Actionable recommendation panel for officer reviews (`APPROVE HOLD REVIEW`, `MONITOR`, `DECLINE`, `ESCALATE`) respecting real-world compliance boundaries.
5. **Demo Presentation Mode**: Direct launch buttons in header for `CASE-DEMO-001` (ATM Cashout) and `CASE-DEMO-002` (Merchant Outlet).

---

## Verification & Build Results
- **Next.js Production Build**: `npm run build` completed with 0 errors across all 9 routes.
- **API Endpoint Verification**: `node frontend/tests/verify_frontend.js` verified 14/14 API endpoints returning HTTP 200 payloads cleanly consumed by the frontend.

---

## How to Run the Prototype
1. **Start Backend Server**:
   ```bash
   python -m src.main
   ```
2. **Start Next.js Frontend**:
   ```bash
   npm run dev --prefix frontend
   ```
3. Open `http://127.0.0.1:3000` in Chrome.

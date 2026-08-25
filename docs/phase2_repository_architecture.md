# CIRIS Phase 2 — Repository Architecture & Technical Audit

## Overview
This document outlines the Phase 2 productization architecture for CIRIS. The core predictive and intelligence algorithms developed in Phase 1 (CIRIS ML V4) are fully preserved and frozen. Phase 2 introduces an enterprise-grade REST API backend powered by FastAPI, PostgreSQL + PostGIS ORM persistence, an alert and intervention engine, structured logging, audit trails, and GIS endpoints.

---

## 1. Preserved Core Intelligence Layer (`src/ml/`)

The frozen intelligence pipeline is loaded via `src/ml/pipeline.py` (`CIPHERPipeline`) from pre-built joblib model artifacts in `models_serialized/`. No ML algorithms, hyperparameters, candidate retrievers, or features are modified.

### Key Components Reused:
- **`CIPHERPipeline`** (`src/ml/pipeline.py`): Primary orchestrator combining candidate retrieval, LightGBM ranking, time prediction, anomaly detection, probability calibration, TreeSHAP explainability, entity resolution, money flow graph, fragmentation detection, mule network intelligence, amount-at-risk calculation, endpoint classification, and intervention recommendations.
- **`CaseIntelligenceObject`** (`src/ml/contracts/case_intelligence.py`): Unified data contract representing the full investigative intelligence output for a case.
- **`ComplaintPayload` & `IntelligenceReport`** (`src/ml/contracts/schemas.py`): Input and output schemas for base ATM prediction and ML features.
- **`SpatialIndex` & `CandidateRetriever`** (`src/ml/retrieval/`): KD-Tree spatial index and hybrid candidate generator.
- **`MoneyFlowGraphEngine`** (`src/ml/retrieval/money_flow_graph.py`): Temporal transaction graph tracing money paths across accounts.
- **`EntityResolutionEngine`** (`src/ml/features/entity_resolution.py`): Graph entity resolution clustering accounts, UPI IDs, cards, and mobile numbers.
- **`AmountAtRiskEngine`** (`src/ml/features/amount_at_risk.py`): Accounting engine balancing disputed, moved, and remaining balances.
- **`EndpointTypeClassifier`** (`src/ml/routing/endpoint_classifier.py`): Multi-endpoint classification routing cases to ATM, Merchant, or Onward Transfer.
- **`InterventionRecommendationEngine`** (`src/ml/routing/intervention.py`): Decision support engine for `HOLD REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE`.

---

## 2. Phase 2 Productization Backend (`src/`)

Phase 2 adds the following layer around the frozen ML core:

```
src/
├── api/                   # FastAPI REST API endpoints
│   ├── v1/
│   │   ├── cases.py       # Case management & intelligence endpoints
│   │   ├── entities.py    # Entity & account lookup endpoints
│   │   ├── transactions.py# Transaction inspection endpoints
│   │   ├── atms.py        # ATM details & prediction endpoints
│   │   ├── alerts.py      # Investigator alert workflow endpoints
│   │   ├── intervention.py# Intervention decision & review endpoints
│   │   ├── gis.py         # GeoJSON spatial endpoints for maps
│   │   ├── networks.py    # Multi-hop network exploration endpoints
│   │   └── system.py      # Health & system status endpoints
│   └── dependencies.py    # FastAPI dependencies & service accessors
├── db/                    # Operational Database & Persistence Layer
│   ├── models.py          # SQLAlchemy ORM models (PostgreSQL/PostGIS + SQLite)
│   ├── session.py         # DB session engine & dual-mode connection pool
│   └── schema.py          # Table initialization & migration utilities
├── services/              # Business Logic & Service Layer
│   ├── case_service.py    # Case CRUD, status, timeline, audit logs
│   ├── intelligence_service.py # Singleton ML pipeline manager & intelligence cache
│   ├── entity_service.py  # Entity resolution & profile details
│   ├── money_flow_service.py   # Money flow graph formatting (nodes & edges)
│   ├── prediction_service.py  # Prediction extraction & SHAP attributions
│   ├── alert_service.py   # Alert lifecycle, assignment & priority scoring
│   ├── intervention_service.py # Intervention review & escalation management
│   └── gis_service.py     # GeoJSON feature collection generators
├── main.py                # FastAPI application entry point, CORS, logging
```

---

## 3. Data & Persistence Boundary

- **Operational Database (PostgreSQL + PostGIS / SQLite dual-mode)**: Stores cases, entities, accounts, cards, UPI IDs, devices, transactions, graph edges, predictions, alerts, audit events, evidence, and intervention records.
- **ML Dataset Storage (`datasets/final` & `models_serialized/`)**: Stores the heavy offline training data and serialized models. Read-only by the backend.

---

## 4. Security & Compliance Boundaries

- **Role-Based Design**: Enforces role access (`INVESTIGATOR`, `BANK_ANALYST`, `LEA_OFFICER`, `I4C_ANALYST`, `ADMIN`).
- **Intervention Boundaries**: CIRIS provides predictive intelligence and recommendations. Actual account holds/freezes are executed by authorized bank/LEA systems (NCRP, CFCFRMS, 1930, Samanvaya).

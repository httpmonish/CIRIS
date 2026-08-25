# CIRIS Phase 2 — System Architecture & Performance Bounds

## System Overview
CIRIS Phase 2 transforms frozen ML V4 intelligence models into an operational, enterprise-grade backend API service.

```
USER / LEA / INVESTIGATOR FRONTEND
              │
        HTTP / REST API
              ▼
       FastAPI BACKEND (src/main.py)
              │
    ┌─────────┴─────────────────────────────────────────┐
    ▼                                                   ▼
API ROUTERS (src/api/v1/)                      DATABASE PERSISTENCE (src/db/)
  - Cases Router                                 - PostgreSQL + PostGIS ORM
  - Entities Router                              - SQLite Dual-Mode Engine
  - Money Flow Router                            - Cases & Predictions
  - Predictions Router                           - Alerts & Audit Events
  - Alerts Router                                - Entity Resolution Nodes
  - Intervention Router
  - GIS Router (GeoJSON)
  - Networks Router
    │
    ▼
BUSINESS SERVICES LAYER (src/services/)
  - CaseService
  - IntelligenceService (Singleton Pipeline Manager)
  - EntityService
  - MoneyFlowService
  - PredictionService
  - AlertService
  - InterventionService
  - GISService
    │
    ▼
FROZEN CIRIS ML V4 INTELLIGENCE CORE (src/ml/)
  - Serialized Model Artifacts (models_serialized/)
  - TreeSHAP Explainer & Fusion Engine
  - Money Flow & Entity Resolution Engines
  - AmountAtRisk & Intervention Recommendation Engines
```

---

## Performance & Optimization Bounds

- **Simple Read Latency**: Target < 300 ms for ordinary case, entity, transaction, and alert lookups.
- **Model Loading**: Models loaded once at application startup into memory (`IntelligenceService`). Zero model reloads per HTTP request.
- **Intelligence Caching**: In-memory read-through cache stores calculated `CaseIntelligenceObject` outputs per case ID.
- **Spatial Map Queries**: Bounding box / viewport filtering (`min_lat`, `max_lat`, `min_lng`, `max_lng`) and pagination limit GeoJSON features to 100 per response, avoiding browser rendering lag.

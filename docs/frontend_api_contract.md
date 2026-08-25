# CIRIS Frontend API Contract Specification

## Overview
This document specifies the REST API endpoints provided by the CIRIS FastAPI backend for frontend integration.

Base URL: `http://127.0.0.1:8000/api/v1`
Interactive OpenAPI Swagger Docs: `http://127.0.0.1:8000/docs`

---

## Endpoint Summary Table

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/cases` | Submit complaint & trigger case intelligence | Case creation status |
| `GET` | `/api/v1/cases` | List paginated cases (filters: status, priority, risk, search) | Case list summary |
| `GET` | `/api/v1/cases/{case_id}` | Get case summary by ID | Case record |
| `GET` | `/api/v1/cases/{case_id}/intelligence` | Get full unified CaseIntelligenceObject | Full intelligence JSON |
| `GET` | `/api/v1/cases/{case_id}/money-flow` | Get nodes & edges for graph visualizer | Graph JSON (`nodes`, `edges`) |
| `GET` | `/api/v1/cases/{case_id}/prediction` | Get primary ATM prediction & SHAP attributions | ATM prediction payload |
| `GET` | `/api/v1/cases/{case_id}/endpoints` | Get candidate endpoint classifications | Endpoints array |
| `GET` | `/api/v1/cases/{case_id}/amount-at-risk` | Get disputed vs remaining accounting | Amount-at-risk summary |
| `GET` | `/api/v1/cases/{case_id}/evidence` | Get categorized evidence attributions | Categorized evidence |
| `GET` | `/api/v1/cases/{case_id}/timeline` | Get chronological case timeline | Timeline events list |
| `GET` | `/api/v1/entities/{entity_id}` | Get entity profile, accounts, UPIs, cards, devices | Entity profile object |
| `GET` | `/api/v1/transactions/{transaction_id}` | Get transaction details and risk score | Transaction record |
| `GET` | `/api/v1/atms/{atm_id}` | Get ATM location details & risk context | ATM record |
| `GET` | `/api/v1/alerts` | List alerts (filters: status, priority, assigned_to) | Alert list summary |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge investigator alert | Status payload |
| `POST` | `/api/v1/alerts/{id}/assign` | Assign alert to investigator/analyst | Status payload |
| `POST` | `/api/v1/alerts/{id}/escalate` | Escalate alert priority to P1 | Status payload |
| `GET` | `/api/v1/cases/{id}/intervention` | Get intervention recommendation & boundary | Intervention object |
| `POST` | `/api/v1/cases/{id}/intervention/review` | Submit officer review decision | Updated intervention |
| `POST` | `/api/v1/cases/{id}/intervention/escalate` | Escalate intervention priority | Updated intervention |
| `GET` | `/api/v1/map/risk` | Get GeoJSON FeatureCollection of risk hotspots | GeoJSON FeatureCollection |
| `GET` | `/api/v1/map/predicted-atms` | Get GeoJSON FeatureCollection of predicted ATMs | GeoJSON FeatureCollection |
| `GET` | `/api/v1/map/networks` | Get GeoJSON FeatureCollection of network nodes | GeoJSON FeatureCollection |
| `GET` | `/api/v1/map/cases` | Get GeoJSON FeatureCollection of cases | GeoJSON FeatureCollection |
| `GET` | `/api/v1/networks/{network_id}` | Get multi-hop network details (hop depth 1-3) | Network cluster object |
| `GET` | `/health` | Health check endpoint | System health status |
| `GET` | `/api/v1/system/status` | Comprehensive component status audit | System status object |

---

## Sample Request Body (`POST /api/v1/cases`)

```json
{
  "complaint_id": "CMP_2026_0099",
  "complaint_timestamp": "2026-08-25T18:00:00Z",
  "reported_loss_amount": 75000.0,
  "fraud_type": "Investment Cyber Fraud",
  "victim_location": {
    "state": "Maharashtra",
    "district": "Mumbai",
    "city": "Mumbai",
    "latitude": 19.1136,
    "longitude": 72.8697
  }
}
```

---

## Standard Error Format
All errors return clean JSON without exposing internal stack traces:

```json
{
  "error_code": "INTERNAL_SERVER_ERROR",
  "message": "Detailed human-readable error description.",
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

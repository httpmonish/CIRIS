# CIRIS — Entity Resolution Model & Schema

## Overview
This document specifies the Entity Resolution framework for CIRIS, enabling cross-case identity resolution, multi-account cluster mapping, and device/linkage correlation without violating privacy boundaries or assuming unavailable telecom/GPS data.

---

## Entity Hierarchy & Relationship Graph

```
                   ┌───────────────────┐
                   │   PERSON / ENTITY │
                   │  (ENTITY_XXXXXX)  │
                   └─────────┬─────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   ┌─────────────────┐               ┌─────────────────┐
   │ ACCOUNT (BANK A)│               │ ACCOUNT (BANK B)│
   │  (ACC_XXXXXX)   │               │  (ACC_XXXXXX)   │
   └────────┬────────┘               └────────┬────────┘
            │                                 │
   ┌────────┴────────┐               ┌────────┴────────┐
   ▼                 ▼               ▼                 ▼
┌───────┐       ┌─────────┐     ┌─────────┐       ┌─────────┐
│ CARD  │       │  UPI ID │     │ MOBILE* │       │ DEVICE* │
│(CARD_)│       │ (UPI_)  │     │(MOB_...)│       │(DEV_...)│
└───────┘       └─────────┘     └─────────┘       └─────────┘
```

---

## Field Availability Classification

| Field Tier | Fields Included | Data Source / Realism | CIRIS Usage Policy |
|---|---|---|---|
| **AVAILABLE (Tier 1)** | `account_id`, `upi_id`, `bank_name`, `transaction_timestamp`, `amount`, `complaint_id`, `pincode`, `city`, `state`, `atm_id` | Standard banking complaint logs, NPCI UPI settlement data, NCRP reports. | Always available for primary point-in-time feature construction and graph building. |
| **OPTIONAL AUTHORIZED (Tier 2)** | `card_masked_pan`, `mobile_hash`, `device_fingerprint_hash`, `linked_account_count` | Available when bank/operator shares authorized hashed metadata during joint investigation. | Used when present; fallback logic applied when absent. |
| **UNAVAILABLE (Tier 3)** | Real-time telecom cell tower GPS, live device IMEI, unhashed personal Aadhaar/PAN, raw IP geo-location | Requires live warrant / telecom surveillance stream. | **NEVER assumed or required** for standard model inference. |

---

## Entity Resolution Algorithm Logic

1. **Exact Deterministic Match**: Links accounts sharing the same `upi_id`, `mobile_hash`, or `device_fingerprint_hash`.
2. **Probabilistic Cluster Linkage**: Groups accounts exhibiting matching transaction velocity bursts, identical pincode/city cashout patterns, and mutual transfer links within $T \le T_{\text{complaint}}$.
3. **Synthetic Anonymization**: All real-world PII is strictly mapped to synthetic identifiers (`ENTITY_XXXXXX`, `ACC_XXXXXX`, `CARD_XXXXXX`, `UPI_XXXXXX@bank`).

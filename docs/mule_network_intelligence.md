# CIRIS — Mule & Network Intelligence Engine

## Overview
The Mule & Network Intelligence Engine computes objective entity-level risk scores for suspect accounts. It identifies money mule candidates using point-in-time graph topology, velocity bursts, counterparty diversity, and cross-case complaints.

---

## Ethical & Nomenclature Standard

> [!IMPORTANT]
> The engine produces objective risk scores and evidence attributions for field investigator decision support. It explicitly tags entities as **"High-Risk Entity / Mule Candidate"** and **NEVER** labels any person as a criminal.

---

## Risk Scoring Formula & Signals

$$\text{Mule Risk Score} = \min\left(1.0, w_1 \cdot \text{Degree} + w_2 \cdot \text{Velocity} + w_3 \cdot \text{Fragmentation} + w_4 \cdot \text{CaseLinks} + w_5 \cdot \text{Centrality}\right)$$

### Signal Breakdown

| Signal Name | Weight | Evidence Rationale Tag |
|---|---|---|
| **Multi-Hop Degree Centrality** | $0.25$ | `HIGH_NETWORK_CONNECTIVITY` (Degree $> 5$) |
| **Transaction Velocity Burst** | $0.25$ | `RAPID_VELOCITY_SURGE` ($\ge 3$ txns in 1 hour) |
| **Micro-Fragmentation Outflow** | $0.20$ | `FRAGMENTED_SPLITTING_PATTERN` ($\ge 3$ unique destinations) |
| **Cross-Case Complaint Links** | $0.20$ | `MULTI_CASE_COMPLAINT_LINKAGE` (Linked to $\ge 2$ complaints) |
| **Short Fund Holding Time** | $0.10$ | `RAPID_IN_OUT_PASS_THROUGH` (Funds moved within $<30$ min) |

---

## Output Structure

```json
{
  "entity_id": "ENTITY_000234",
  "account_id": "ACC_000234",
  "mule_risk_score": 0.84,
  "confidence": "HIGH",
  "evidence_tags": [
    "HIGH_NETWORK_CONNECTIVITY",
    "RAPID_VELOCITY_SURGE",
    "MULTI_CASE_COMPLAINT_LINKAGE"
  ],
  "cluster_size": 7,
  "degree_centrality": 8,
  "is_unflagged_related": true
}
```

# CIRIS — Data Provenance & Governance Registry

## Overview
This registry records the data lineage, source attribution, schema definitions, transformation rules, and privacy compliance for all data assets utilized within the CIRIS SIH 2026 financial cybercrime intelligence platform.

---

## Data Asset Provenance Table

| Asset ID | Asset Name | Source | Licence | Record Count | Primary Purpose | Synthetic / Real | Privacy & PII Safeguards |
|---|---|---|---|---|---|---|---|
| `DS-001` | **CIRIS Primary Complaints** | Internal Generator (`dataset/cybercrime_dataset_gen`) | Proprietary / SIH 2026 | 50,000 | Core complaint ingestion, victim location, loss amount, & incident timing. | Synthetic | Synthetic names/locations, zero real PII. |
| `DS-002` | **CIRIS ATM Master Registry** | Indian Spatial ATM Benchmark | Public Domain / Open Data | 7,000 | Physical ATM locations, pincodes, bank operators, & lat/lon index. | Real Geolocation / Synthetic Operators | Publicly available physical ATM locations. |
| `DS-003` | **CIRIS Transaction Graph** | Internal Generator (`dataset/cybercrime_dataset_gen`) | Proprietary / SIH 2026 | 349,706 | Multi-hop transfer topology, fragmentation, velocity, & mule graph. | Synthetic | Synthetic account IDs (`ACC_...`, `UPI_...`). |
| `DS-004` | **CIRIS Withdrawals Log** | Internal Generator (`dataset/cybercrime_dataset_gen`) | Proprietary / SIH 2026 | 50,000 | Ground-truth ATM cashouts for point-in-time ranking & evaluation. | Synthetic | Synthetic transaction hashes & ATM IDs. |
| `DS-005` | **PaySim Auxiliary Set** | NTNU / Kaggle | CC BY-SA 4.0 | 6,362,620 | Auxiliary training for mobile money transfer vs cashout behavior. | Synthetic | Anonymized mobile wallet logs. |
| `DS-006` | **IBM AMLSim Graph Benchmark** | IBM Research | Apache 2.0 | 500,000 | Graph engine validation for smurfing, fan-out, & gathering typologies. | Synthetic | Agent-based simulated graph. |

---

## Transformation & Data Lineage Flow

```
RAW SYNTHETIC SOURCES (DS-001 to DS-004)
        ↓
CANONICAL DATASET LOADER (src/ml/data/loader.py)
        ↓
POINT-IN-TIME PARTITIONER (t <= T_complaint filter)
        ↓
ENTITY RESOLUTION ENGINE (src/ml/features/entity_resolution.py)
        ↓
MONEY-FLOW GRAPH ENGINE (src/ml/retrieval/money_flow_graph.py)
        ↓
FEATURE PIPELINE & MODEL TRAINERS (src/ml/pipeline.py)
```

---

## Governance & Privacy Directives

1. **Zero PII Exposure**: All entity identifiers follow strict synthetic formats (`ENTITY_XXXXXX`, `ACC_XXXXXX`, `CARD_XXXXXX`, `UPI_XXXXXX@bank`, `DEVICE_XXXXXX`).
2. **Point-in-Time Integrity**: Every transaction, graph edge, and withdrawal record undergoes strict temporal filtering against the complaint timestamp $T_{\text{complaint}}$ to ensure zero lookahead data leakage.
3. **Auxiliary Data Isolation**: External public datasets (`DS-005`, `DS-006`) are used exclusively for algorithm validation and auxiliary feature benchmarking. They are never mixed directly with primary Indian geographic ranking tables.

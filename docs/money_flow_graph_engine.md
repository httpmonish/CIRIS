# CIRIS — Money-Flow Graph Engine Architecture

## Overview
The Money-Flow Graph Engine upgrades CIRIS from simple 1-hop Account→ATM lookups into a generalized multi-hop financial graph system. It extracts time-bounded directed subgraphs, identifies money splitting/fragmentation paths, discovers connected mule clusters, and traces funds across intermediate hops to ultimate endpoints (ATM, Merchant, or Onward Transfer).

---

## Graph Model Topology

```
                  ┌──────────────────────┐
                  │ VICTIM COMPLAINT (C) │
                  └──────────┬───────────┘
                             │ Disputed Loss (₹10,000)
                             ▼
                  ┌──────────────────────┐
                  │  ACCOUNT A (Mule 1)  │
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            │ Splitting                       │ Splitting
            ▼ (₹5,000)                        ▼ (₹5,000)
┌──────────────────────┐            ┌──────────────────────┐
│  ACCOUNT B (Mule 2)  │            │  ACCOUNT C (Mule 3)  │
└──────────┬───────────┘            └──────────┬───────────┘
           │ Cashout                           │ Onward Transfer
           ▼                                   ▼
┌──────────────────────┐            ┌──────────────────────┐
│     ATM ENDPOINT     │            │  ACCOUNT D (Mule 4)  │
│      (ATM_0234)      │            └──────────┬───────────┘
└──────────────────────┘                       │ Merchant Spend
                                               ▼
                                    ┌──────────────────────┐
                                    │  MERCHANT ENDPOINT   │
                                    │    (POS_MERCHANT)    │
                                    └──────────────────────┘
```

---

## Graph Extraction & Analytics Capabilities

1. **Point-in-Time Subgraph Extraction ($t \le T_{\text{complaint}}$)**: Strictly filters edges created before or at the complaint timestamp $T_{\text{complaint}}$ to ensure 0 temporal leakage.
2. **K-Hop Directed Path Traversal**: Traces forward flow paths up to $k=3$ hops from seed victim/mule accounts.
3. **Connected Component & Cluster Risk**: Identifies strongly and weakly connected components, measuring network density, account degree, and cluster size.
4. **Branching & Fan-Out Analysis**: Measures out-degree velocity and splitting ratios to flag structured smurfing typologies.
5. **Multi-Endpoint Classification**: Identifies leaf nodes in the path and classifies them into physical ATM cashout, online/POS merchant spending, or onward inter-bank transfer.

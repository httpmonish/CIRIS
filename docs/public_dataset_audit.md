# CIRIS — Public Dataset Availability & Suitability Audit

## Overview
This document evaluates public financial fraud, transaction network, anti-money laundering (AML), and money mule datasets. It assesses their structural attributes, privacy terms, geographic relevance, and suitability for integration into the CIRIS SIH 2026 financial cybercrime intelligence platform.

---

## Public Dataset Evaluation Matrix

### 1. IBM AMLSim (Agent-Based AML Synthetic Simulator)
- **Official Source**: IBM Research (GitHub: `ibm-messaging/amlsim`)
- **Licence**: Apache License 2.0
- **Record Count**: Configurable (typically 500k to 10M transactions, 10k–100k accounts)
- **Fields**: `step`, `action`, `amount`, `nameOrig`, `oldbalanceOrg`, `newbalanceOrig`, `nameDest`, `oldbalanceDest`, `newbalanceDest`, `isFraud`, `isSAR`
- **Labels**: Binary fraud/SAR labels (`isFraud`, `isSAR`) for laundering patterns (fan-in, fan-out, cycle, gather-scatter)
- **Account/Entity IDs**: Synthetic IDs (`nameOrig`, `nameDest`)
- **Transaction Relationships**: Direct account-to-account directed graph edges
- **Timestamp**: Simulated step ticks (hourly/daily resolution)
- **Geography**: Generic/Abstract (no geographic coordinates or Indian administrative hierarchy)
- **Graph Suitability**: High (engineered specifically for graph typology benchmarking)
- **Fraud/Mule Suitability**: High for money laundering & mule fan-out/fan-in typology detection
- **ATM Suitability**: None (does not simulate physical cashout locations or ATMs)
- **Merchant Suitability**: Low (focuses on account-to-account transfers)
- **Indian Context Suitability**: Low (generic currencies and synthetic topologies)
- **Privacy Limitations**: None (100% synthetic)
- **Redistribution/Use**: Permitted under Apache 2.0
- **Classification**: **C. GRAPH/ALGORITHM BENCHMARK**

---

### 2. IBM Financial Peer-to-Peer AML Dataset (HI-Small / HI-Large)
- **Official Source**: IBM Research / Kaggle / IEEE DataPort
- **Licence**: CC BY-SA 4.0
- **Record Count**: ~5.2 million transactions (HI-Small: ~5M, HI-Large: ~18M)
- **Fields**: `Timestamp`, `From Bank`, `From Account`, `To Bank`, `To Account`, `Amount Received`, `Receiving Currency`, `Amount Paid`, `Payment Currency`, `Payment Format`, `Is Laundering`
- **Labels**: Binary `Is Laundering` flag based on synthetic typologies
- **Account/Entity IDs**: Synthetic Bank and Account IDs
- **Transaction Relationships**: Multi-bank account-to-account transfer graph
- **Timestamp**: Unix timestamps / explicit datetime strings
- **Geography**: Generic multi-currency (USD, EUR, etc., no Indian lat/lon or pincodes)
- **Graph Suitability**: Very High (complex multi-hop financial transaction networks)
- **Fraud/Mule Suitability**: High for detecting multi-hop money routing across financial institutions
- **ATM Suitability**: Low (Payment formats include Wire, ACH, Cheque, Credit Card, Cash, but no specific ATM IDs or lat/lon)
- **Merchant Suitability**: Moderate (contains payment format breakdown)
- **Indian Context Suitability**: Moderate (multi-bank concept translates, but lacks Indian geography)
- **Privacy Limitations**: None (synthetic multi-bank data)
- **Redistribution/Use**: Permitted under CC BY-SA 4.0
- **Classification**: **B. AUXILIARY TRAINING** & **C. GRAPH/ALGORITHM BENCHMARK**

---

### 3. Elliptic Bitcoin Transaction Dataset
- **Official Source**: Elliptic / Kaggle / Zenodo
- **Licence**: CC BY-NC-SA 4.0
- **Record Count**: 203,769 node transactions, 234,355 directed graph edges
- **Fields**: `txId`, `time_step`, `class` (licit, illicit, unknown), 166 local/aggregate graph features
- **Labels**: `1` (illicit), `2` (licit), `unknown`
- **Account/Entity IDs**: Bitcoin Transaction Hashes (mapped to integer IDs)
- **Transaction Relationships**: Directed Acyclic Graph (DAG) of crypto transactions
- **Timestamp**: Discrete time steps (1 to 49)
- **Geography**: None (blockchain network)
- **Graph Suitability**: Exceptional (standard benchmark for graph neural networks and node classification)
- **Fraud/Mule Suitability**: High for graph topology learning, low for traditional banking UI/UPI
- **ATM Suitability**: None
- **Merchant Suitability**: None
- **Indian Context Suitability**: Low (crypto transactions vs Indian UPI/IMPS/NEFT)
- **Privacy Limitations**: None (anonymized public blockchain data)
- **Redistribution/Use**: Non-commercial use only (CC BY-NC-SA 4.0)
- **Classification**: **D. VALIDATION REFERENCE** (Algorithm benchmark for graph features)

---

### 4. PaySim Synthetic Mobile Money Dataset
- **Official Source**: Kaggle / NTNU (Edgar Lopez-Rojas)
- **Licence**: CC BY-SA 4.0
- **Record Count**: 6,362,620 transactions
- **Fields**: `step`, `type` (PAYMENT, TRANSFER, CASH_OUT, DEBIT, CASH_IN), `amount`, `nameOrig`, `oldbalanceOrg`, `newbalanceOrig`, `nameDest`, `oldbalanceDest`, `newbalanceDest`, `isFraud`, `isFlaggedFraud`
- **Labels**: `isFraud` (1/0), `isFlaggedFraud` (1/0)
- **Account/Entity IDs**: Synthetic IDs (`C...` for customer, `M...` for merchant)
- **Transaction Relationships**: Single-hop source to destination
- **Timestamp**: Hourly steps (1 step = 1 hour, 744 steps total = 31 days)
- **Geography**: None
- **Graph Suitability**: Moderate (bipartite customer-to-merchant/customer-to-customer transfers)
- **Fraud/Mule Suitability**: High for cash-out vs transfer classification and velocity anomalies
- **ATM Suitability**: Low (has generic CASH_OUT type, but no physical ATM metadata)
- **Merchant Suitability**: High (has `M...` merchant accounts and PAYMENT type)
- **Indian Context Suitability**: Moderate (mobile wallet transfer flow resembles UPI wallet cashouts)
- **Privacy Limitations**: None (synthetic based on financial logs from a mobile money service in an African country)
- **Redistribution/Use**: Permitted under CC BY-SA 4.0
- **Classification**: **B. AUXILIARY TRAINING**

---

### 5. SAML-D (Synthetic Anti-Money Laundering Dataset for Financial Crime)
- **Official Source**: IEEE DataPort / GitHub (`SAML-D`)
- **Licence**: Open Data Commons Attribution License (ODC-By)
- **Record Count**: ~9.5 million transactions
- **Fields**: `Timestamp`, `From Bank`, `From Account`, `To Bank`, `To Account`, `Amount`, `Currency`, `Payment Format`, `Is Laundering`, `Laundering Typology`
- **Labels**: Explicit multi-label typologies (Structuring, Smurfing, Layering, Rapid In-Out, Gathering)
- **Account/Entity IDs**: Synthetic identifiers
- **Transaction Relationships**: Multi-hop directed financial graph
- **Timestamp**: Fine-grained timestamps
- **Geography**: None (abstract financial system)
- **Graph Suitability**: High (multi-hop smurfing and structuring patterns)
- **Fraud/Mule Suitability**: Exceptional for fragmentation, splitting, and smurfing detection
- **ATM Suitability**: Low
- **Merchant Suitability**: Moderate
- **Indian Context Suitability**: Moderate
- **Privacy Limitations**: None (synthetic)
- **Redistribution/Use**: Open Data Commons
- **Classification**: **B. AUXILIARY TRAINING** & **C. GRAPH/ALGORITHM BENCHMARK**

---

## Integration Strategy & Classification Summary

| Dataset | Role Classification | Strategic Purpose in CIRIS |
|---|---|---|
| **CIRIS National Benchmark Data** | **A. PRIMARY** | Primary dataset for Indian geography, 5,000 ATMs, 50k complaints, 350k txns, pincodes, lat/lon, and ranking evaluation. |
| **PaySim Mobile Fraud Data** | **B. AUXILIARY TRAINING** | Pre-training/benchmarking velocity anomalies and merchant vs cash-out flow patterns. |
| **IBM AMLSim / SAML-D** | **B. AUXILIARY / C. BENCHMARK** | Benchmarking transaction fragmentation (smurfing/layering) and graph centrality algorithms. |
| **Elliptic Bitcoin Dataset** | **D. VALIDATION REFERENCE** | Algorithm baseline validation for multi-hop graph node risk scoring. |

---

## Strict Policy Enforcement

1. **No Data Mismatch**: Public datasets with different transaction schemas or currencies are **NOT** blindly merged into the primary Indian ATM ranking dataset.
2. **Provenance Disclosure**: Any auxiliary feature model trained or validated using public datasets is explicitly attributed in `docs/data_provenance_registry.md`.
3. **No False Claims**: The primary CIRIS dataset is explicitly described as a *high-fidelity national-scale synthetic benchmark dataset matching Indian banking, geography, and cybercrime reporting structures*, never as "real raw bank PII data".

# CIRIS — Existing Bank & AML System Gap Analysis

## Executive Summary

A critical mentor feedback item highlighted that existing banking Rule-Based Transaction Monitoring Systems (TMS) and Anti-Money Laundering (AML) software already track individual customer accounts, card numbers, transaction amounts, timestamps, and account histories. 

CIRIS does **NOT** claim to discover a victim's or fraudster's single account when a bank cannot. Instead, CIRIS fills the strategic gap between isolated bank controls and national-level cybercrime intelligence by unifying **cross-entity resolution, multi-case correlation, multi-hop money flow graph tracing, unflagged related account discovery, and proactive next-endpoint interception prediction**.

---

## Capabilities Comparison: Bank / AML Controls vs. CIRIS

| Control Dimension | Existing Bank / AML Systems | CIRIS Cybercrime Intelligence Platform |
|---|---|---|
| **Scope of View** | **Single Institution / Single Account**: Limited to transactions originating or terminating within the specific bank. | **Cross-Institution & Multi-Case**: Unifies complaints, multi-bank UPI/IMPS flows, and cross-case linkages across police & banking portals. |
| **Detection Basis** | **Static Threshold Rules & Historical Profiling**: Triggers alerts on single transaction amounts exceeding thresholds (e.g. >₹50,000) or velocity anomalies. | **Dynamic Graph & Typology Intelligence**: Detects multi-destination splitting, rapid smurfing, fan-out/fan-in chains, and mule network centralities. |
| **Account Discovery** | **Known Flagged Account Only**: Knows the immediate beneficiary account of a reported transaction if already flagged. | **Unflagged Related Entity Expansion**: Traces multi-hop transfers to identify previously unflagged mule accounts and linked identity clusters. |
| **Endpoint Perspective** | **Reactive Post-Transaction Logging**: Records an ATM withdrawal or POS transfer after it completes. | **Proactive Predictive Interception**: Predicts the specific candidate ATM or merchant endpoint and time window *before* cashout occurs. |
| **Response Action** | **Automated Account Freeze / Lien**: Directly freezes an account per internal risk algorithms. | **Investigator Decision Support**: Computes amount-at-risk, generates SHAP attributions and graph evidence, and recommends policy interventions (HOLD REVIEW, ESCALATE) requiring human authorization. |

---

## What CIRIS Does NOT Replace

1. **Core Banking System (CBS) Transaction Processing**: CIRIS is an intelligence layer operating above CBS; it does not replace core ledger processing.
2. **Standard AML Compliance & Regulatory Reporting**: CIRIS does not replace statutory Suspicious Transaction Reports (STR) or Currency Transaction Reports (CTR).
3. **Legal Account Freezing Authority**: CIRIS does not assert unauthorized automated account freezing; statutory freezing remains under legal bank/LEA authority.

---

## What CIRIS Uniquely Delivers

```
REPORTED FRAUD COMPLAINT
        ↓
CROSS-CASE LINKAGE (Connects isolated complaints across districts/states)
        ↓
MULTI-HOP MONEY FLOW TRACING (Traces funds across Account A → B → C → D)
        ↓
UNFLAGGED MULE DISCOVERY (Identifies intermediate mule entities B & C)
        ↓
AMOUNT-AT-RISK ACCOUNTING (Separates moved funds vs remaining balances)
        ↓
NEXT-ENDPOINT PREDICTION (Rank-orders candidate ATMs & estimates cashout window)
        ↓
EXPLAINABLE INTERVENTION BRIEFING (SHAP evidence + LEA officer briefing)
```

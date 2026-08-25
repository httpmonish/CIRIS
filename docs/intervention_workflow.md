# CIRIS — Investigator Intervention Workflow

## Overview
CIRIS generates policy-compliant, evidence-backed intervention recommendations for authorized Law Enforcement Officers (LEA) and Bank Fraud Control Units. The system operates as a decision support intelligence platform; it does **not** perform unauthorized automated account freezes.

---

## Intervention Hierarchy & Matrix

| Intervention Action | Trigger Criteria | Potential Hold Review Amount | Target Recipient | Legal / Authorization Boundary |
|---|---|---|---|---|
| **ESCALATE** | Highest risk cashout predicted (fused score $\ge 0.75$), high confidence mule cluster ($\ge 5$ nodes), or high loss ($>\text{₹}100,000$). | Full remaining observed disputed amount | LEA Field Officer & Bank Head Office Fraud Desk | Rapid emergency dispatch / priority freeze request to designated bank officer. |
| **HOLD REVIEW** | Intermediate risk ($0.50 \le \text{Score} < 0.75$), unflagged mule account detected with remaining balance. | Observed remaining disputed amount in account | Bank Branch Fraud Officer / Compliance Desk | Administrative hold review request placed in bank queue for human authorization. |
| **INVESTIGATE** | Low-to-medium risk ($0.30 \le \text{Score} < 0.50$), suspicious velocity surge or fragmentation pattern. | Zero (Surveillance status) | LEA Analyst / Cyber Crime Cell Investigator | Case added to active surveillance board for cross-case intelligence gathering. |
| **MONITOR** | Standard complaint, low fused score ($<0.30$), or insufficient candidate evidence. | Zero (Audit status) | Automated Log Queue | System logs complaint and continues background monitoring. |

---

## Investigator Workflow Lifecycle

```
INCOMING FRAUD COMPLAINT
        ↓
CIRIS CASE INTELLIGENCE COMPILATION
        ↓
CALCULATE AMOUNT AT RISK (Disputed vs Moved vs Remaining)
        ↓
GENERATE INTERVENTION RECOMMENDATION (HOLD REVIEW / ESCALATE)
        ↓
PRESENT TO AUTHORIZED OFFICER (Investigator Dashboard)
        ↓
HUMAN DECISION & LEGAL AUTHORIZATION (Officer approves/rejects hold)
        ↓
OFFICIAL BANK / LEA ACTION EXECUTED (CBS lien / LEA field dispatch)
        ↓
CASE OUTCOME FEEDBACK LOOP (Outcome recorded in CIRIS database)
```

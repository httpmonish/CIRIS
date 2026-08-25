# CIRIS Demo Scenarios Walkthrough

## Overview
CIRIS Phase 2 includes two deterministic, pre-seeded demo cases designed to demonstrate full investigative capabilities in 3 to 5 minutes.

---

## Scenario 1: `CASE-DEMO-001` (Primary ATM Cash-Out Prediction)

### Flow Step-by-Step:
1. **Complaint Received**: Victim reports Investment Cyber Fraud loss of INR 50,000 in Mumbai (Pincode: 400053).
2. **Case Creation**: Backend receives complaint (`POST /api/v1/cases`), initializes case `CASE-DEMO-001`, and sets status to `ANALYZING`.
3. **Money Flow & Entity Resolution**: Money flow graph traces instant IMPS transfer of INR 50,000 from victim account to primary mule account `ACC_MULE_001` linked to entity `ENT_001`.
4. **Amount at Risk**: Deterministic accounting calculates INR 35,000 moved to withdrawal stage, with INR 15,000 unwithdrawn balance remaining in `ACC_MULE_001`.
5. **ATM Risk Prediction**: CIRIS ML V4 predicts high-probability ATM cashout at **SBI ATM - Andheri West (`ATM_9981`)** with fused risk score **0.88** and predicted time window **3-6h** (3.5h delay).
6. **TreeSHAP Evidence**: Top feature importance highlights spatial proximity (< 4.2 km) and rapid in-out flow velocity (< 30 min).
7. **Intervention Recommendation**: Recommends `HOLD REVIEW` for INR 15,000 remaining in `ACC_MULE_001`.
8. **Investigator Action**: Investigator acknowledges alert `ALT-DEMO-001` and reviews intervention `INT-DEMO-001`.

---

## Scenario 2: `CASE-DEMO-002` (Merchant / Transfer Endpoint)

### Flow Step-by-Step:
1. **Complaint Received**: Victim reports Digital Voucher / E-Commerce Scam loss of INR 120,000 in New Delhi.
2. **Endpoint Classification**: Multi-endpoint classifier determines cashout route is NOT a physical ATM. Routes to **Merchant Endpoint (`MERCH_GOLD_EXCHANGE`)** with probability **0.72**.
3. **Intervention Recommendation**: Recommends `MONITOR` on onward settlement account.
4. **Demonstration Goal**: Proves CIRIS can reason about non-ATM alternative endpoints without building a separate model.

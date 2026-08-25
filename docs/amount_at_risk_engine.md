# CIRIS — Amount-at-Risk Accounting Engine

## Overview
The Amount-at-Risk Accounting Engine provides deterministic financial accounting for reported cybercrime funds. It tracks the exact flow of disputed funds from initial victim loss through intermediate mule accounts, calculating observed moved funds vs observed remaining balances.

---

## Accounting Formulae

$$\text{Disputed Amount} = \text{Reported Loss Amount from Victim Complaint}$$

$$\text{Observed Moved Amount} = \sum \text{Outgoing Point-in-Time Transfers from Immediate Mule Accounts}$$

$$\text{Observed Remaining Amount} = \max\left(0, \text{Disputed Amount} - \text{Observed Moved Amount}\right)$$

$$\text{Unresolved Amount} = \text{Disputed Amount} - (\text{Observed Moved Amount} + \text{Observed Remaining Amount})$$

$$\text{Hold Review Recommended Amount} = \min\left(\text{Observed Remaining Amount}, \text{Current Point-in-Time Mule Balance}\right)$$

---

## Strict Accounting Principles

> [!CAUTION]
> The engine never automatically asserts that an account's total balance belongs to stolen fraud proceeds. It restricts hold recommendations strictly to the **observed remaining disputed funds** linked to the specific complaint flow.

---

## Accounting Breakdown Example

```
Victim Disputed Loss:    ₹10,000.00
-----------------------------------------
Forwarded to Mule B:      ₹4,000.00  (Observed Moved)
Forwarded to Mule C:      ₹3,000.00  (Observed Moved)
Remaining in Mule A:      ₹3,000.00  (Observed Remaining)
-----------------------------------------
Total Accounted:         ₹10,000.00  (Unresolved: ₹0.00)
Recommended Hold Review:  ₹3,000.00  (Mule A Account)
```

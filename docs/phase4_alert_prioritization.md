# CIRIS Phase 4 — Alert Prioritization Framework & Decision Rules

## 1. Executive Overview

The CIRIS Alert Engine evaluates multi-dimensional cybercrime signals to assign deterministic, explainable priority tiers (**P1, P2, P3, P4**) and severities (**CRITICAL, HIGH, MEDIUM, LOW**). 

Priority is **never** assigned based on an opaque weight or a single weak signal. Every tier maps directly to an operational investigation SLA and actionable LEA protocol.

---

## 2. Priority Tiers & SLA Standards

| Priority Tier | Description | Target SLA Deadline | Recommended Action Protocol |
|---|---|---|---|
| **P1** | **Immediate Intervention Potential**<br>High amount at risk, imminent cash-out window (0–3h), high-confidence ML target, or rapid fragmentation in progress. | **15 minutes** | Priority alert dispatch to Field LEA Unit / Rapid ATM Cashout Interception Desk. |
| **P2** | **High-Risk Active Investigation**<br>Active multi-hop mule network, substantial financial loss, or confirmed high-degree mule account. | **1 hour** | Case assignment to Cyber Crime Investigation Cell for account linkage and mule tracking. |
| **P3** | **Requires Review / Secondary Investigation**<br>Standard fraud complaint, medium urgency score, or moderate fragmentation volume. | **4 hours** | Review by investigating officer, transaction statement reconciliation. |
| **P4** | **Informational / Passive Monitoring**<br>Low financial impact, historical/delayed complaint, or low risk anomaly score. | **24 hours** | Monitored in automated intelligence pool, correlated for recurring patterns. |

---

## 3. Mathematical Priority Scoring Formula

The Composite Operational Priority Score $S_{\text{priority}} \in [0.0, 1.0]$ is computed as:

$$
S_{\text{priority}} = 0.30 \cdot R_{\text{calibrated}} + 0.25 \cdot T_{\text{imminence}} + 0.20 \cdot A_{\text{normalized}} + 0.15 \cdot N_{\text{evidence}} + 0.10 \cdot U_{\text{urgency}}
$$

Where:
1. **$R_{\text{calibrated}}$ (Calibrated ML Risk Score)**: Fused model prediction score $[0.0, 1.0]$.
2. **$T_{\text{imminence}}$ (Endpoint Imminence Score)**:
   - $1.00$ if predicted withdrawal time window is `0-3h` or delay $< 3$ hours.
   - $0.70$ if predicted withdrawal time window is `3-6h`.
   - $0.40$ if predicted withdrawal time window is `6-24h` or $> 24$ hours.
3. **$A_{\text{normalized}}$ (Amount at Risk Factor)**:
   $$A_{\text{normalized}} = \min\left(1.0, \frac{\text{Amount at Risk (₹)}}{500,000}\right)$$
4. **$N_{\text{evidence}}$ (Network & Fragmentation Evidence)**:
   - $+0.40$ if multi-hop transaction chain detected ($\ge 2$ hops).
   - $+0.30$ if high-volume fragmentation pattern verified.
   - $+0.30$ if connected to a known synthetic mule cluster.
5. **$U_{\text{urgency}}$ (Complaint Urgency Score)**: Victim-reported urgency and rapid reporting score $[0.0, 1.0]$.

---

## 4. Priority Tier Thresholds & Deterministic Rules

### Rule P1 (Immediate Intervention)
Assigned if:
- $S_{\text{priority}} \ge 0.75$, **OR**
- $\text{Amount at Risk} \ge ₹200,000$ **AND** $T_{\text{imminence}} = 1.0$ (0–3h cashout window) **AND** $R_{\text{calibrated}} \ge 0.70$.

### Rule P2 (High-Risk Investigation)
Assigned if:
- $0.55 \le S_{\text{priority}} < 0.75$, **OR**
- Multi-hop mule network verified with $\ge 3$ transaction hops and loss $\ge ₹50,000$.

### Rule P3 (Standard Review)
Assigned if:
- $0.35 \le S_{\text{priority}} < 0.55$.

### Rule P4 (Monitor / Informational)
Assigned if:
- $S_{\text{priority}} < 0.35$.

---

## 5. Alert Deduplication, Cooldown & Suppression Guardrails

To prevent alert fatigue and redundant LEA dispatch:
1. **Deterministic Deduplication Hash**:
   $$\text{dedup\_hash} = \text{SHA256}(\text{case\_id} + \text{alert\_type} + \text{endpoint\_id} + \text{time\_bucket\_15m})$$
2. **Case-Level Aggregation**: If multiple transactions occur within a 15-minute window for the same complaint, they are appended as supporting evidence items under a single master alert rather than creating separate P1 dispatches.
3. **Cooldown Window**: A 1-hour suppression cooldown is enforced per complaint ID unless a higher severity tier is triggered (e.g. escalating from P3 to P1 upon rapid ATM cash-out prediction).

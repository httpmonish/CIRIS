# CIRIS Phase 4 — Legal & Forensic Auditability

## 1. Statutory Compliance & Evidentiary Standard

The CIRIS Phase 4 Operational Action Layer is designed to meet strict evidentiary standards required for financial crime prosecution (e.g. Indian IT Act Section 65B, Prevention of Money Laundering Act, and international digital forensics norms).

---

## 2. Append-Only Audit Architecture

### 2.1 Immutability
All forensic events are written to the `audit_trail` table. The schema enforces append-only semantics:
- `UPDATE` or `DELETE` operations on `audit_trail` are strictly prohibited at the application layer.
- Each event contains a millisecond-precision UTC timestamp and a unique `event_id` (`AUD_YYYYMMDDHHMMSS_XXXXX`).

### 2.2 Forensic Event Types

| Event Action | Trigger | Captured Metadata |
| :--- | :--- | :--- |
| `ALERT_CREATED` | System intelligence detection | Alert ID, Priority, Severity, Risk Score, Amount at Risk |
| `ALERT_ACKNOWLEDGED`| Investigator triage | Alert ID, Acknowledged By, Triage Notes |
| `ALERT_ASSIGNED` | Supervisor allocation | Assigned To, Assigned Team, Assigned By |
| `ALERT_ESCALATED` | High-risk pattern detected | Escalation Reason, Target Team, Escalated By |
| `ALERT_CLOSED` | Investigation completed | Close Reason, Closed By |
| `CASE_CREATED` | System or complaint registration| Complaint ID, Priority, Amount at Risk |
| `CASE_ACKNOWLEDGED` | First review by officer | Officer ID, Timestamp |
| `CASE_ASSIGNED` | Case delegation | Owner, Squad/Team, Delegator |
| `CASE_INVESTIGATING`| Field work initiated | Investigator ID, Surveillance plan |
| `CASE_RESOLVED` | Outcome determined | Outcome (`CONFIRMED`, `FALSE_POSITIVE`, `RECOVERED`), Recovered Amount |
| `INTERVENTION_RECOMMENDED`| Policy decision generated | Recommendation (`HOLD_REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE`), Model Confidence |
| `INTERVENTION_REVIEWED` | Human-in-the-loop signoff | Reviewer Badge ID, Action (`ACCEPT`, `REJECT`, `OVERRIDE`), Review Rationale |
| `NOTE_ADDED` | Case file update | Author ID, Content, Visibility level |
| `FEEDBACK_SUBMITTED` | Continuous learning telemetry| Investigator ID, Outcome, Actual ATM ID, Recovered Loss |

---

## 3. Human-in-the-Loop Decision Boundary

1. **Strict Authorization Barrier**: The CIRIS platform operates solely as a Decision-Support System (DSS). Automated execution of financial account freezing, lien imposition, or physical asset seizure is blocked at the core service level.
2. **Review Accountability**: Every policy intervention record (`interventions` table) stores the exact timestamp and officer identifier when reviewed, ensuring a clear chain of custody from automated detection to human judicial action.

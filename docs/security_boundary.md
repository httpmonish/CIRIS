# CIRIS Security & Authorization Boundary Specification

## Security Architecture

1. **Environment Variables & Secrets Handling**:
   - Secrets (database credentials, JWT secret keys, API tokens) are strictly read from environment variables or `.env` file.
   - Sample configuration template provided in `.env.example`.
   - Hardcoded production credentials or wildcards in CORS (`allow_origins=["*"]`) are strictly prohibited in production configurations.

2. **Role-Based Access Control (RBAC) Interface**:
   The API layer is designed to support role enforcement:
   - `INVESTIGATOR`: Full view of case intelligence, timeline, and alerts; submit intervention reviews.
   - `BANK_ANALYST`: View money flow, mule account risk, and hold review recommendations.
   - `LEA_OFFICER`: Escalate intervention recommendations, view geographic prediction maps and ATM dispatch details.
   - `I4C_ANALYST`: Cross-case network analysis and suspect registry verification.
   - `ADMIN`: Alert assignment, user role management, system health inspection.

3. **Structured Logging & Data Privacy**:
   - PII protection: Raw sensitive personal data, full un-hashed card numbers, or real phone numbers are never logged in application traces.
   - Synthetic IDs (`ENT_0001`, `ACC_0001`, `CARD_0001`, `MOB_0001`, `DEV_0001`) are used across prototype datasets.
   - Every API request is logged with a unique `X-Request-ID` header. Stack traces are never exposed to API callers in HTTP responses.

---

## Authoritative Real-World Boundaries

> [!IMPORTANT]
> **Boundary Notice**:
> CIRIS provides predictive cybercrime intelligence, money flow graph analysis, and intervention decision support.
>
> CIRIS DOES NOT claim to perform autonomous bank account freezing, account holding, or law enforcement actions.
>
> Actual account freezing or lien actions belong strictly to authorized bank and LEA workflows (NCRP, CFCFRMS/1930, Samanvaya, Pratibimb, I4C Suspect Registry). CIRIS intervention outputs (`HOLD REVIEW`, `MONITOR`, `INVESTIGATE`, `ESCALATE`) are structured recommendations produced for authorized human decision-makers.

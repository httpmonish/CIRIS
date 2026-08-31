# CIRIS — SIH 2026 Live Website Presentation & Demo Script
**Step-by-Step Interactive Demo Walkthrough for http://localhost:8000/**

---

## ⏱️ 3-to-5 Minute Judge Presentation Script

### 🎬 ACT 1: The Landing Page & Role-Based Access Control (0:00 – 0:45)

> **Speaker Script**:
> *"Good morning respected judges. Digital financial fraud in India leaves victims helpless within minutes as stolen funds splinter across mule accounts and cash out at physical ATMs. Today we present **CIRIS** — Cybercrime Intelligence & ATM Cash-Out Interception System.*
> 
> *As per strict SIH guidelines, our landing page strictly enforces **Role-Based Access Control (RBAC)** across three portals: Citizens, Bank Nodal Officers, and Government/I4C Super-Admins."*

**Actions on Screen**:
1. Open `http://localhost:8000/`.
2. Point out the **Quick Demo Access** bar at the top of the auth card (`Citizen`, `Bank Nodal`, `Govt / I4C`).
3. Click the 3 portal tabs (`Citizen`, `Bank`, `Govt`) to show role description updates.

---

### 🛡️ ACT 2: The Citizen Dispute Journey (0:45 – 1:30)

> **Speaker Script**:
> *"Let's start with the Citizen experience. A victim of a ₹14,500 UPI scam logs into the Citizen Portal."*

**Actions on Screen**:
1. Click **`Citizen`** quick login button (Logs in as `citizen@ciris.gov.in`).
2. Show the **4-Step Live Dispute Stepper**:
   - `Step 1: Dispute Lodged (T+0m)`
   - `Step 2: Bank Scrutiny (T+8m)`
   - `Step 3: Mule Account Frozen (T+19m)`
   - `Step 4: ATM Interception ACTIVE`
3. Click **`Lodge New Dispute`** button.
4. Enter Amount `₹25,000`, Bank `ICICI`, RRN `402910481920`, City `Mumbai`, and click **Submit**.
5. Show the toast notification (`Dispute lodged successfully!`) and the new complaint instantly rendering in the complaint list.

---

### 🏦 ACT 3: Bank Nodal Officer Isolation & CBS Hold (1:30 – 2:15)

> **Speaker Script**:
> *"Now let's switch to a Bank Nodal Officer at ICICI Bank. Under DPDP 2023 multi-tenant isolation, bank officials only see disputes targeting their institution."*

**Actions on Screen**:
1. Click **`Logout`** in top right corner.
2. Click **`Bank Nodal`** quick login button (Logs in as `nodal.icici@bank.in`).
3. Show the **Institution Dispute Queue** filtered strictly for ICICI Bank.
4. Point out the confidence tier badges (`AUTO-FREEZE`, `LEA ALERT`).
5. Click **`Freeze`** (triggers instant CBS Account Hold with green toast confirmation).
6. Click **`Escalate`** (escalates dispute directly to I4C Cybercrime Cell).

---

### 🏛️ ACT 4: Government / I4C Master GIS Intelligence Console (2:15 – 3:45)

> **Speaker Script**:
> *"Now let's step into the main command center — the Government and I4C Super-Admin Console."*

**Actions on Screen**:
1. Click **`Logout`** and click **`Govt / I4C`** quick login button (Logs in as `officer.i4c@mha.gov.in`).
2. Point out the **Hero Metric Strip**:
   - **84.93% Candidate Recall** (250km BallTree Indexing)
   - **63.61% Top-10 Shortlist Hit Rate**
   - **99.85% Search-Space Reduction** (7,000 ATMs $\rightarrow$ Top-10)
   - **<50ms Inference Latency** (CPU)
3. Hover over the **5 Actionable Output Cards** (*WHERE, WHEN, WHY, CONFIDENCE, ACTION*) to demonstrate macOS spring physics, glass gloss highlights, and expandable detail panels.
4. Point to the **Case Inspector**:
   - Click **`CASE_000001`** preset button (Thane UPI Splintering, ₹4,505.94).
   - Show the interactive **Leaflet GIS Map**: Point out red victim marker, purple candidate ATM markers, and dashed spatial vector line.
   - Point out the **Top-10 Shortlist Table** on the right.
   - Click any candidate row to expand the **TreeExplainer SHAP Panel** (`+0.44 Anomaly`, `+0.31 Proximity`) and the **Section 65B Cryptographic Audit Hash**.
   - Click **`CASE_ANOMALY_01`** (Isolation Forest clean mule detection).

---

### ⚡ ACT 5: Live Incident Simulation & Dispatch Telemetry (3:45 – 5:00)

> **Speaker Script**:
> *"Let's test live real-time ingestion by simulating an emergency incident call from NCRP 1930."*

**Actions on Screen**:
1. Click **`⚡ Simulate Live Incident`** button in the top bar.
2. Watch the **4-Stage High-Tech Dispatch Telemetry Modal**:
   - `Stage 1: Ingestion (T=0 Point-in-Time Lock)`
   - `Stage 2: Mule Graph Traversal (sub-₹50k splintering detected)`
   - `Stage 3: 250km BallTree Candidate Retrieval (200 candidates in 2.7ms)`
   - `Stage 4: LambdaMART Rank #1 Target Locked (95.0% probability)`
3. Show the green completion card (`Target Locked & Beat Dispatched`) and click **Dismiss**.
4. Scroll down to **Alert Feeds & Dispatches**:
   - Click **`Inspect Case`** on any alert card.
   - Show how the screen smoothly scrolls back up to the **Case Inspector** with toast notification.
5. Click **`Data Provenance`** in the left sidebar to show judges the transparent dataset disclosure (50,000 cases, 7,000 ATMs, 150,000 graph edges, zero PII exposure).

> **Closing Statement**:
> *"CIRIS turns reactive 48-hour post-mortems into sub-50ms proactive interceptions before cash exits banking rails. Thank you, we are open for questions!"*

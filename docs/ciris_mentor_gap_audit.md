# CIRIS — Comprehensive Mentor Gap Audit

## Overview
This document performs a line-item audit of the 12 key mentor concerns raised regarding the CIRIS SIH 2026 system. For each concern, it evaluates the current implementation, identifies the architectural and functional gap, details the required code/doc changes, lists affected files, defines validation tests, and assigns current and target statuses.

---

## Line-Item Audit of Mentor Concerns

### Concern 1: Real Data vs. Synthetic Data
- **Concern**: The mentor questioned data realism, sourcing, and whether public AML datasets (e.g. IBM AMLSim, Elliptic, PaySim) should be used or blindly merged.
- **Current Implementation**: Synthetic national-scale dataset with 50,000 complaints, 349,706 transactions, 40,000 accounts, 7,000 ATMs, 50,000 withdrawals, and 11.9M ranking pairs.
- **Gap**: Lack of formal public dataset audit document and explicit dataset provenance registry.
- **Required Change**: Perform a formal audit of public AML/mule datasets. Classify datasets by role (Primary, Auxiliary Training, Graph Benchmark, Validation Reference, Not Suitable). Maintain Indian synthetic benchmark dataset without falsely claiming real bank data.
- **Files Affected**:
  - `docs/public_dataset_audit.md` (NEW)
  - `docs/data_provenance_registry.md` (NEW)
- **Validation Test**: `tests/test_final_dataset_connectivity.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 2: Account / Card / ATM Already Known by Banks
- **Concern**: Banks already know victim accounts, cards, ATM IDs, transaction amounts, and timestamps for isolated transactions. CIRIS must not claim to "discover" an account the bank already knows.
- **Current Implementation**: Focused heavily on predicting the specific ATM cashout location for a given complaint.
- **Gap**: Clear articulation and implementation of CIRIS's unique value proposition: cross-case correlation, multi-hop money flow tracing, unflagged related entity discovery, and next-endpoint prediction.
- **Required Change**: Document existing bank/AML control gaps vs CIRIS capabilities. Implement cross-case linkage and multi-hop network expansion.
- **Files Affected**:
  - `docs/ciris_existing_system_gap.md` (NEW)
  - `docs/ciris_vs_existing_systems.md` (NEW)
  - `src/ml/contracts/case_intelligence.py` (NEW)
- **Validation Test**: `tests/test_case_intelligence_e2e.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 3: Mobile / Device / Card Linkage
- **Concern**: How does the system link entities (Person, Account, Card, UPI, Mobile, Device) when fields are incomplete or varied?
- **Current Implementation**: Simple account-to-account edges and UPI entity lookups in `TemporalGraphEngine`.
- **Gap**: Formal entity-resolution framework with explicit tiering of available, optional authorized, and unavailable fields.
- **Required Change**: Implement `EntityResolutionEngine` handling identity linking across Person ↔ Account ↔ Card ↔ UPI ↔ Mobile ↔ Device with synthetic identifiers.
- **Files Affected**:
  - `src/ml/features/entity_resolution.py` (NEW)
  - `docs/entity_resolution_model.md` (NEW)
- **Validation Test**: `tests/test_entity_resolution.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 4: Account Blocking
- **Concern**: Account blocking/freezing is already handled by core banking/AML systems and cannot be done automatically by third-party systems without authorization.
- **Current Implementation**: Alert status flags `DISPATCH_ALERT` or `MONITOR_HOLD`.
- **Gap**: Formal intervention workflow specifying legal authorization boundaries and recommendation tiers (HOLD REVIEW, MONITOR, INVESTIGATE, ESCALATE).
- **Required Change**: Implement `InterventionRecommendationEngine` that produces actionable advice for human bank/LEA officers without asserting automatic execution.
- **Files Affected**:
  - `src/ml/routing/intervention.py` (NEW)
  - `docs/intervention_workflow.md` (NEW)
- **Validation Test**: `tests/test_intervention.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 5: Money Splitting / Fragmentation
- **Concern**: Fraudsters split high-value fraud funds into multiple small micro-transactions across multiple accounts to evade static thresholds.
- **Current Implementation**: Transaction counts and account velocity in `FeatureBuilder`, but no explicit multi-destination fragmentation detector.
- **Gap**: Lack of dedicated transaction fragmentation engine detecting rapid fund splitting, branching, and micro-flow patterns.
- **Required Change**: Implement `TransactionFragmentationDetector` analyzing time proximity, splitting ratios, velocity surges, and destination fan-out.
- **Files Affected**:
  - `src/ml/features/fragmentation_detector.py` (NEW)
  - `docs/transaction_fragmentation_engine.md` (NEW)
- **Validation Test**: `tests/test_fragmentation.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 6: Money-Flow Graph
- **Concern**: Real fraud money flows across complex multi-hop graphs with branching, convergence, and multiple non-ATM endpoints, not simple 1-hop Account→ATM paths.
- **Current Implementation**: 2-hop graph lookup in `TemporalGraphEngine`.
- **Gap**: Generalized financial graph engine supporting k-hop traversal, time-bounded subgraphs, multi-endpoint paths, and connected component analysis.
- **Required Change**: Implement `MoneyFlowGraphEngine` providing k-hop graph extraction, path discovery, and subgraph metrics.
- **Files Affected**:
  - `src/ml/retrieval/money_flow_graph.py` (NEW)
  - `docs/money_flow_graph_engine.md` (NEW)
- **Validation Test**: `tests/test_money_flow_graph.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 7: Mule / Network Detection
- **Concern**: System must evaluate mule risk objectively without making unsupported claims of "criminal identification".
- **Current Implementation**: Isolation Forest anomaly score and mule degree features.
- **Gap**: Dedicated Mule Risk engine returning continuous risk scores, confidence levels, and explicit evidence rationale tags.
- **Required Change**: Implement `MuleNetworkIntelligenceEngine` producing entity-level risk scoring and evidence rationale tags ("high-risk mule candidate").
- **Files Affected**:
  - `src/ml/models/mule_network.py` (NEW)
  - `docs/mule_network_intelligence.md` (NEW)
- **Validation Test**: `tests/test_mule_network.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 8: Remote / Unusual ATM
- **Concern**: Preserving the strong predictive capability for unusual/remote ATM cashout locations.
- **Current Implementation**: LightGBM LambdaMART ranker with BallTree spatial index, hotspot cache, and candidate retrieval.
- **Gap**: Maintain existing high performance (86% candidate pool recall, 46x lift over baseline) without regression.
- **Required Change**: Preserve ATM ML V4 intact as the primary ATM Endpoint Intelligence Module.
- **Files Affected**:
  - `src/ml/models/ranker.py`
  - `src/ml/retrieval/candidate_retriever.py`
- **Validation Test**: `tests/test_stage_0.py`, `tests/test_stage_2.py`
- **Status**: ✅ GREEN → Preserve

---

### Concern 9: What If There Is No ATM?
- **Concern**: Fraudulent funds do not always end in ATM withdrawals; funds may be spent at merchants/POS or transferred indefinitely.
- **Current Implementation**: System assumed ATM cashout was the primary outcome.
- **Gap**: Endpoint classification layer assessing whether funds are heading to ATM, Merchant/POS, or Onward Transfer.
- **Required Change**: Implement `EndpointTypeClassifier` categorizing endpoint likelihoods and routing to specific intelligence sub-modules.
- **Files Affected**:
  - `src/ml/routing/endpoint_classifier.py` (NEW)
- **Validation Test**: `tests/test_endpoint_classifier.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 10: Real Fraud Lifecycle
- **Concern**: The system must model the complete lifecycle from initial complaint through multi-hop transfers to endpoint intelligence.
- **Current Implementation**: Complaint -> Candidate Retrieval -> ATM Ranking -> Output.
- **Gap**: End-to-end case intelligence object encapsulating disputed amount, money flow, entity resolution, mule risk, amount at risk, endpoint prediction, and intervention recommendation.
- **Required Change**: Update `CIPHERPipeline` to orchestrate the full case lifecycle and output unified `CaseIntelligenceObject`.
- **Files Affected**:
  - `src/ml/pipeline.py`
  - `src/ml/contracts/case_intelligence.py` (NEW)
- **Validation Test**: `tests/test_pipeline_e2e.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 11: ML Reality (No 100% Accuracy Claim)
- **Concern**: Realistic ML models in financial crime cannot achieve 100% accuracy; confidence, calibration, and false positive trade-offs must be explicit.
- **Current Implementation**: Platt scaling calibrator with Brier Score = 0.002039.
- **Gap**: Comprehensive evaluation policy documenting classification metrics (Precision, Recall, PR-AUC, ROC-AUC, FPR, FNR) alongside ranking and continuous time metrics.
- **Required Change**: Document formal `docs/ml_evaluation_policy.md` and enforce transparent metric reporting across all evaluation modes.
- **Files Affected**:
  - `docs/ml_evaluation_policy.md` (NEW)
  - `src/ml/evaluation/evaluator.py`
- **Validation Test**: `tests/test_stage_5.py`
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

### Concern 12: Thinking > ML Architecture
- **Concern**: Domain problem solving and money flow logic must take precedence over blindly stacking ML models.
- **Current Implementation**: Strong 6-stage ML pipeline.
- **Gap**: Documented decision flow proving domain logic precedes model execution.
- **Required Change**: Structure pipeline execution around clear financial crime domain steps: Fraud Pattern → Money Flow → Connected Entities → Unflagged Entities → Next Endpoint → Recommended Action.
- **Files Affected**:
  - `docs/ciris_final_architecture.md` (NEW)
- **Validation Test**: System-wide integration test suite
- **Status**: 🟡 IN_PROGRESS → Target: ✅ GREEN

---

## Audit Summary
- **Total Mentor Concerns**: 12
- **Currently Preserved Core Modules**: 1 (ATM ML V4)
- **New Modules/Docs Introduced**: 15 new documents, 7 new ML engine components
- **Target Overall System Status**: 100% GREEN upon full verification

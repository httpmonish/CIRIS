/**
 * CIRIS API Type Definitions
 * Directly aligned with docs/frontend_api_contract.md and FastAPI endpoint responses.
 */

export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN';

export interface SystemStatus {
  system: string;
  version: string;
  status: string;
  components: {
    api: string;
    database: string;
    ml_models: string;
    case_pipeline: string;
    graph_engine: string;
    spatial_index: string;
  };
  timestamp: string;
}

export interface AmountAtRisk {
  disputed_amount: number;
  observed_moved_amount: number;
  observed_remaining_amount: number;
  unresolved_amount: number;
  hold_review_recommended_amount: number;
}

export interface MoneyFlowPathNode {
  id: string;
  type: 'VICTIM' | 'MULE' | 'ATM' | 'MERCHANT' | 'ACCOUNT';
  label: string;
  risk: number;
  metadata?: Record<string, any>;
}

export interface MoneyFlowPathEdge {
  source: string;
  target: string;
  amount: number;
  timestamp: string;
  transaction_id: string;
  transaction_type: string;
  risk: number;
  case_link?: string;
}

export interface MoneyFlowGraph {
  case_id: string;
  nodes: MoneyFlowPathNode[];
  edges: MoneyFlowPathEdge[];
}

export interface LocationDetails {
  city: string;
  district: string;
  bank_name?: string;
  latitude?: number;
  longitude?: number;
  merchant_category?: string;
}

export interface SHAPFeature {
  feature: string;
  friendly_name: string;
  value: number;
  shap_value: number;
  abs_impact: number;
  direction: 'RISK_INCREASE' | 'RISK_DECREASE';
}

export interface EndpointPrediction {
  endpoint_type: 'ATM' | 'MERCHANT' | 'TRANSFER' | 'UNKNOWN';
  endpoint_id: string;
  endpoint_name: string;
  location_details: LocationDetails;
  probability: number;
  predicted_time_window: string;
  predicted_delay_hours: number;
  fused_risk_score: number;
  evidence_attributions: SHAPFeature[];
}

export interface EvidenceTag {
  feature: string;
  friendly_name: string;
  value: number;
  shap_value: number;
  abs_impact: number;
  direction: string;
}

export interface EvidenceSection {
  fraud_type: string;
  location_details: LocationDetails;
  evidence_attributions: EvidenceTag[];
}

export interface InterventionRecommendation {
  recommended_action: 'HOLD REVIEW' | 'MONITOR' | 'INVESTIGATE' | 'ESCALATE';
  confidence_score: number;
  action_rationale: string;
  potential_hold_amount: number;
  authorization_boundary: string;
  target_accounts_for_review: string[];
  xai_narrative_briefing: string;
}

export interface CaseIntelligence {
  case_id: string;
  victim_id: string;
  complaint_timestamp: string;
  disputed_amount: number;
  fraud_type: string;
  known_suspicious_transactions: any[];
  connected_entities: {
    account_id: string;
    entity_id: string;
    linked_accounts: string[];
    cards: string[];
    upi_ids: string[];
    mobiles: string[];
    devices: string[];
  };
  money_flow_paths: any[];
  mule_candidates: Array<{
    entity_id: string;
    account_id: string;
    mule_risk_score: number;
    confidence: string;
    evidence_tags: string[];
    cluster_size: number;
    degree_centrality: number;
    rapid_in_out_ratio: number;
    is_unflagged_related: boolean;
  }>;
  amount_at_risk: AmountAtRisk;
  potential_endpoints: EndpointPrediction[];
  overall_case_risk: number;
  overall_confidence: number;
  top_evidence: Array<{
    feature: string;
    friendly_name: string;
    value: number;
    shap_value: number;
    abs_impact: number;
    direction: string;
  }>;
  related_cases: string[];
  intervention_recommendation: InterventionRecommendation;
  xai_narrative_briefing: string;
}

export interface CaseItem {
  case_id: string;
  complaint_id: string;
  victim_id: string;
  status: string;
  priority: string;
  overall_case_risk: number;
  disputed_amount: number;
  fraud_type: string;
  primary_mule_account: string;
  predicted_endpoint: string;
  created_at: string;
}

export interface TimelineEvent {
  event_id: string;
  case_id: string;
  event_type: string;
  title: string;
  description: string;
  timestamp: string;
  actor: string;
  metadata: Record<string, any>;
}

export interface AlertItem {
  id: string;
  case_id: string;
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  title: string;
  risk_score: number;
  amount_at_risk: number;
  endpoint_type: string;
  time_window: string;
  status: 'NEW' | 'ACKNOWLEDGED' | 'ASSIGNED' | 'RESOLVED';
  assigned_to: string;
  created_at: string;
}

export interface InterventionReview {
  review_id: string;
  case_id: string;
  reviewer: string;
  decision: 'APPROVE_HOLD_REVIEW' | 'DECLINE' | 'MONITOR';
  notes: string;
  updated_at: string;
}

export interface EntityProfile {
  entity_id: string;
  primary_account: string;
  mule_risk_score: number;
  confidence: string;
  linked_accounts: string[];
  cards: string[];
  upi_ids: string[];
  mobiles: string[];
  devices: string[];
  associated_cases: string[];
  transaction_count: number;
}

export interface TransactionDetail {
  transaction_id: string;
  source_account: string;
  target_account: string;
  amount: number;
  timestamp: string;
  transaction_type: string;
  risk_score: number;
  associated_case: string;
}

export interface NetworkDetail {
  network_id: string;
  case_id: string;
  risk_score: number;
  entity_count: number;
  case_count: number;
  transaction_count: number;
  nodes: MoneyFlowPathNode[];
  edges: MoneyFlowPathEdge[];
  top_entities: string[];
  evidence_summary: string[];
}

export interface ATMDetail {
  atm_id: string;
  bank_name: string;
  city: string;
  district: string;
  state: string;
  latitude: number;
  longitude: number;
  risk_score: number;
  historical_cashouts_24h: number;
  associated_cases: string[];
}

export interface MapFeature {
  type: 'Feature';
  geometry: {
    type: 'Point' | 'Polygon' | 'MultiPolygon';
    coordinates: any;
  };
  properties: {
    id: string;
    title: string;
    type: 'CASE' | 'ATM' | 'NETWORK' | 'RISK_ZONE';
    risk: number;
    district?: string;
    time_window?: string;
    [key: string]: any;
  };
}

export interface MapGeoJSON {
  type: 'FeatureCollection';
  features: MapFeature[];
}

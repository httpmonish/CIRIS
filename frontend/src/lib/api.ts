import {
  SystemStatus,
  CaseItem,
  CaseIntelligence,
  MoneyFlowGraph,
  AmountAtRisk,
  EndpointPrediction,
  EvidenceSection,
  TimelineEvent,
  AlertItem,
  InterventionReview,
  EntityProfile,
  TransactionDetail,
  NetworkDetail,
  ATMDetail,
  MapGeoJSON,
} from '../types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => '');
      throw new Error(`API ${res.status} ${res.statusText}: ${errorText || 'Server Error'}`);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`Fetch error on ${url}:`, err);
    throw err;
  }
}

export const cirisApi = {
  // System & Health
  getHealth: () => fetchJson<{ status: string; timestamp: string }>('/health'),
  getSystemStatus: () => fetchJson<SystemStatus>('/api/v1/system/status'),

  // Cases
  getCases: (params?: { status?: string; priority?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.append('status', params.status);
    if (params?.priority) query.append('priority', params.priority);
    if (params?.limit) query.append('limit', String(params.limit));
    if (params?.offset) query.append('offset', String(params.offset));
    const qs = query.toString() ? `?${query.toString()}` : '';
    return fetchJson<CaseItem[]>(`/api/v1/cases${qs}`);
  },

  getCaseDetail: (caseId: string) => fetchJson<CaseItem>(`/api/v1/cases/${caseId}`),
  getCaseIntelligence: (caseId: string) => fetchJson<CaseIntelligence>(`/api/v1/cases/${caseId}/intelligence`),
  getCaseMoneyFlow: (caseId: string, maxHops = 3) => fetchJson<MoneyFlowGraph>(`/api/v1/cases/${caseId}/money-flow?max_hops=${maxHops}`),
  getCasePredictions: (caseId: string) => fetchJson<EndpointPrediction[]>(`/api/v1/cases/${caseId}/prediction`),
  getCaseAmountAtRisk: (caseId: string) => fetchJson<AmountAtRisk>(`/api/v1/cases/${caseId}/amount-at-risk`),
  getCaseEvidence: (caseId: string) => fetchJson<EvidenceSection>(`/api/v1/cases/${caseId}/evidence`),
  getCaseTimeline: (caseId: string) => fetchJson<TimelineEvent[]>(`/api/v1/cases/${caseId}/timeline`),

  createCase: (payload: {
    complaint_id: string;
    victim_id: string;
    reported_loss_amount: number;
    fraud_type?: string;
  }) =>
    fetchJson<CaseItem>('/api/v1/cases', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Entities
  getEntity: (entityId: string) => fetchJson<EntityProfile>(`/api/v1/entities/${entityId}`),

  // Transactions
  getTransaction: (transactionId: string) => fetchJson<TransactionDetail>(`/api/v1/transactions/${transactionId}`),

  // ATMs
  getATM: (atmId: string) => fetchJson<ATMDetail>(`/api/v1/atms/${atmId}`),

  // Alerts
  getAlerts: () => fetchJson<AlertItem[]>('/api/v1/alerts'),
  acknowledgeAlert: (alertId: string) =>
    fetchJson<{ message: string; alert_id: string }>(`/api/v1/alerts/${alertId}/acknowledge`, { method: 'POST' }),
  assignAlert: (alertId: string, assignedTo: string) =>
    fetchJson<{ message: string; alert_id: string }>(`/api/v1/alerts/${alertId}/assign`, {
      method: 'POST',
      body: JSON.stringify({ assigned_to: assignedTo }),
    }),
  escalateAlert: (alertId: string, reason: string) =>
    fetchJson<{ message: string; alert_id: string }>(`/api/v1/alerts/${alertId}/escalate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  // Interventions
  getCaseIntervention: (caseId: string) => fetchJson<InterventionReview>(`/api/v1/cases/${caseId}/intervention`),
  reviewIntervention: (caseId: string, reviewer: string, decision: string, notes: string) =>
    fetchJson<InterventionReview>(`/api/v1/cases/${caseId}/intervention/review`, {
      method: 'POST',
      body: JSON.stringify({ reviewer, decision, notes }),
    }),
  escalateIntervention: (caseId: string, actor: string, reason: string) =>
    fetchJson<{ status: string; case_id: string; escalated_at: string }>(`/api/v1/cases/${caseId}/intervention/escalate`, {
      method: 'POST',
      body: JSON.stringify({ actor, reason }),
    }),

  // GIS / Map
  getMapRisk: () => fetchJson<MapGeoJSON>('/api/v1/map/risk'),
  getMapPredictedATMs: () => fetchJson<MapGeoJSON>('/api/v1/map/predicted-atms'),
  getMapNetworks: () => fetchJson<MapGeoJSON>('/api/v1/map/networks'),
  getMapCases: () => fetchJson<MapGeoJSON>('/api/v1/map/cases'),

  // Networks
  getNetwork: (networkId: string) => fetchJson<NetworkDetail>(`/api/v1/networks/${networkId}`),
};

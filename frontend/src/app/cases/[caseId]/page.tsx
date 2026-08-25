'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  FolderGit2,
  GitCommit,
  Users,
  Search,
  HelpCircle,
  Clock,
  ShieldCheck,
  Building2,
  ArrowLeft,
  AlertTriangle,
  IndianRupee,
} from 'lucide-react';
import { RiskBadge } from '../../../components/ui/RiskBadge';
import { MetricCard } from '../../../components/ui/MetricCard';
import { MoneyFlowGraph } from '../../../components/graph/MoneyFlowGraph';
import { EvidenceCard } from '../../../components/ui/EvidenceCard';
import { Timeline } from '../../../components/ui/Timeline';
import { InterventionCard } from '../../../components/ui/InterventionCard';
import { cirisApi } from '../../../lib/api';
import {
  CaseIntelligence,
  MoneyFlowGraph as MoneyFlowGraphType,
  TimelineEvent,
  InterventionReview,
  MoneyFlowPathNode,
  MoneyFlowPathEdge,
} from '../../../types/api';

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = (params.caseId as string) || 'CASE-DEMO-001';

  const [intel, setIntel] = useState<CaseIntelligence | null>(null);
  const [moneyFlow, setMoneyFlow] = useState<MoneyFlowGraphType | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [intervention, setIntervention] = useState<InterventionReview | undefined>();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected Node/Edge state for Graph Drawer
  const [selectedNode, setSelectedNode] = useState<MoneyFlowPathNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<MoneyFlowPathEdge | null>(null);

  // Active Sub-Tab
  const [activeTab, setActiveTab] = useState<'graph' | 'prediction' | 'evidence' | 'timeline' | 'intervention'>('graph');

  const loadCaseData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [intelRes, moneyFlowRes, timelineRes, intervRes] = await Promise.allSettled([
        cirisApi.getCaseIntelligence(caseId),
        cirisApi.getCaseMoneyFlow(caseId),
        cirisApi.getCaseTimeline(caseId),
        cirisApi.getCaseIntervention(caseId),
      ]);

      if (intelRes.status === 'fulfilled') {
        setIntel(intelRes.value);
      } else {
        setError(`Failed loading intelligence for case ${caseId}`);
      }

      if (moneyFlowRes.status === 'fulfilled') setMoneyFlow(moneyFlowRes.value);
      if (timelineRes.status === 'fulfilled') setTimeline(timelineRes.value);
      if (intervRes.status === 'fulfilled') setIntervention(intervRes.value);
    } catch (err: any) {
      setError(err.message || 'Error fetching case intelligence');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCaseData();
  }, [caseId]);

  if (isLoading) {
    return (
      <div className="p-12 text-center space-y-4">
        <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <div className="text-xs font-mono text-slate-400">Loading CIRIS Intelligence for {caseId}...</div>
      </div>
    );
  }

  if (error || !intel) {
    return (
      <div className="p-8 text-center space-y-4 max-w-lg mx-auto bg-slate-900 border border-slate-800 rounded-xl mt-12">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
        <h3 className="text-base font-bold text-white">Case Not Found or Error</h3>
        <p className="text-xs text-slate-400">{error || `No intelligence object returned for ${caseId}`}</p>
        <button
          onClick={() => router.push('/cases')}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg"
        >
          Return to Case Registry
        </button>
      </div>
    );
  }

  const primaryEndpoint = intel.potential_endpoints?.[0];
  const amountAtRisk = intel.amount_at_risk;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Navigation & Case Title Bar */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/cases')}
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-extrabold text-white tracking-tight font-mono">{intel.case_id}</h2>
              <RiskBadge score={intel.overall_case_risk} />
            </div>
            <p className="text-xs text-slate-400">
              Complaint ID: <span className="font-mono text-blue-400">{intel.victim_id}</span> | Type:{' '}
              <span className="text-white font-medium">{intel.fraud_type}</span>
            </p>
          </div>
        </div>

        {/* Quick Action Navigation */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveTab('intervention')}
            className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-lg shadow-rose-950 transition-colors"
          >
            <ShieldCheck className="w-4 h-4" /> Take Intervention Action
          </button>
        </div>
      </div>

      {/* Amount-at-Risk Summary Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono uppercase text-slate-400">Disputed Loss</span>
          <div className="text-lg font-bold text-white font-mono">₹{intel.disputed_amount?.toLocaleString()}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono uppercase text-slate-400">Observed Moved</span>
          <div className="text-lg font-bold text-amber-400 font-mono">
            ₹{amountAtRisk?.observed_moved_amount?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono uppercase text-slate-400">Observed Remaining</span>
          <div className="text-lg font-bold text-emerald-400 font-mono">
            ₹{amountAtRisk?.observed_remaining_amount?.toLocaleString() || '0'}
          </div>
        </div>
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] font-mono uppercase text-slate-400">Recommended Hold</span>
          <div className="text-lg font-bold text-rose-400 font-mono">
            ₹{amountAtRisk?.hold_review_recommended_amount?.toLocaleString() || intel.disputed_amount?.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-800 text-xs font-medium space-x-6">
        {[
          { id: 'graph', label: 'Money Flow Graph', icon: GitCommit },
          { id: 'prediction', label: 'ATM / Endpoint Prediction', icon: Building2 },
          { id: 'evidence', label: 'SHAP Evidence (WHY)', icon: HelpCircle },
          { id: 'timeline', label: 'Case Timeline', icon: Clock },
          { id: 'intervention', label: 'Intervention Recommendation', icon: ShieldCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-3 flex items-center gap-2 border-b-2 font-semibold transition-colors ${
                isActive
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Main Tab Content Display */}
      {activeTab === 'graph' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ReactFlow Interactive Graph Canvas (2 Cols) */}
          <div className="lg:col-span-2 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Multi-Hop Transaction Path & Mule Network
            </h3>
            {moneyFlow ? (
              <MoneyFlowGraph
                data={moneyFlow}
                onNodeSelect={(n) => {
                  setSelectedNode(n);
                  setSelectedEdge(null);
                }}
                onEdgeSelect={(e) => {
                  setSelectedEdge(e);
                  setSelectedNode(null);
                }}
              />
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">No money flow graph available.</div>
            )}
          </div>

          {/* Right-Side Detail Panel (Node or Mule Candidate) */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
              Entity & Account Inspection
            </h3>

            {selectedNode ? (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="font-mono text-xs font-bold text-blue-400">{selectedNode.id}</span>
                  <RiskBadge score={selectedNode.risk} />
                </div>
                <div className="text-xs space-y-1 font-mono text-slate-300">
                  <p>Type: <span className="text-white font-bold">{selectedNode.type}</span></p>
                  <p>Label: {selectedNode.label}</p>
                </div>
                <button
                  onClick={() => router.push(`/entities/${selectedNode.id}`)}
                  className="w-full py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-blue-300"
                >
                  View Entity 360 Profile
                </button>
              </div>
            ) : selectedEdge ? (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 font-mono text-xs">
                <div className="font-bold text-white">Transaction Edge Detail</div>
                <p className="text-slate-400">ID: {selectedEdge.transaction_id}</p>
                <p className="text-emerald-400 font-bold">Amount: ₹{selectedEdge.amount.toLocaleString()}</p>
                <p className="text-slate-300">Type: {selectedEdge.transaction_type}</p>
                <button
                  onClick={() => router.push(`/transactions/${selectedEdge.transaction_id}`)}
                  className="w-full py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-blue-300 font-sans"
                >
                  View Transaction Details
                </button>
              </div>
            ) : (
              /* Default Candidate Mules Panel */
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                <div className="text-xs font-semibold text-white">Top Mule Entity Candidates</div>
                {intel.mule_candidates?.length ? (
                  intel.mule_candidates.map((mule, idx) => (
                    <div
                      key={idx}
                      onClick={() => router.push(`/entities/${mule.entity_id}`)}
                      className="p-3 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer space-y-1.5"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-mono text-xs font-bold text-amber-400">{mule.account_id}</span>
                        <RiskBadge score={mule.mule_risk_score} />
                      </div>
                      <div className="text-[10px] text-slate-400 flex justify-between font-mono">
                        <span>Centrality: {mule.degree_centrality}</span>
                        <span>In/Out Ratio: {mule.rapid_in_out_ratio}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic">No mule candidates extracted.</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'prediction' && (
        <div className="space-y-4 max-w-3xl">
          <h3 className="text-sm font-bold text-white">Predicted Cashout Endpoints & ATM Hotspots</h3>
          {primaryEndpoint ? (
            <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                    RANK #1 PREDICTION
                  </span>
                  <h4 className="text-lg font-bold text-white mt-1">{primaryEndpoint.endpoint_name}</h4>
                  <p className="text-xs text-slate-400 font-mono">
                    ID: {primaryEndpoint.endpoint_id} | Bank: {primaryEndpoint.location_details?.bank_name}
                  </p>
                </div>
                <RiskBadge score={primaryEndpoint.fused_risk_score} />
              </div>

              <div className="grid grid-cols-3 gap-3 font-mono text-xs">
                <div className="p-3 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Predicted Time Window</span>
                  <span className="text-amber-300 font-bold">{primaryEndpoint.predicted_time_window}</span>
                </div>
                <div className="p-3 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Endpoint Probability</span>
                  <span className="text-emerald-400 font-bold">
                    {(primaryEndpoint.probability * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="p-3 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Location District</span>
                  <span className="text-white font-bold">{primaryEndpoint.location_details?.district}</span>
                </div>
              </div>

              <button
                onClick={() => router.push(`/atms/${primaryEndpoint.endpoint_id}`)}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold"
              >
                View Full ATM Spatial Profile
              </button>
            </div>
          ) : (
            <p className="text-xs text-slate-500">No endpoint predictions generated.</p>
          )}
        </div>
      )}

      {activeTab === 'evidence' && (
        <div className="space-y-4 max-w-3xl">
          <h3 className="text-sm font-bold text-white">TreeSHAP Explainable Intelligence (WHY HIGH RISK)</h3>
          {intel.top_evidence?.length ? (
            <EvidenceCard features={intel.top_evidence as any} narrative={intel.xai_narrative_briefing} />
          ) : (
            <p className="text-xs text-slate-500">No SHAP attributions generated.</p>
          )}
        </div>
      )}

      {activeTab === 'timeline' && (
        <div className="space-y-4 max-w-3xl">
          <h3 className="text-sm font-bold text-white">Chronological Case Investigation Feed</h3>
          <Timeline events={timeline} />
        </div>
      )}

      {activeTab === 'intervention' && (
        <div className="space-y-4 max-w-3xl">
          <InterventionCard
            caseId={intel.case_id}
            recommendation={intel.intervention_recommendation}
            existingReview={intervention}
            onSuccess={loadCaseData}
          />
        </div>
      )}
    </div>
  );
}

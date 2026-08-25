'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Network, ArrowLeft, GitFork } from 'lucide-react';
import { RiskBadge } from '../../../components/ui/RiskBadge';
import { MoneyFlowGraph } from '../../../components/graph/MoneyFlowGraph';
import { cirisApi } from '../../../lib/api';
import { NetworkDetail } from '../../../types/api';

export default function NetworkDetailPage() {
  const params = useParams();
  const router = useRouter();
  const netId = (params.networkId as string) || 'NET-DEMO-001';

  const [net, setNet] = useState<NetworkDetail | null>(null);
  const [hopDepth, setHopDepth] = useState<number>(2);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    cirisApi
      .getNetwork(netId)
      .then((res) => setNet(res))
      .catch((err) => console.error('Error fetching network:', err))
      .finally(() => setIsLoading(false));
  }, [netId]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading Mule Network Cluster...</div>;
  }

  if (!net) {
    return <div className="p-8 text-center text-xs text-slate-400">Network {netId} not found.</div>;
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-extrabold text-white font-mono">{net.network_id}</h2>
              <RiskBadge score={net.risk_score} />
            </div>
            <p className="text-xs text-slate-400">
              Entities: <span className="font-bold text-white">{net.entity_count}</span> | Case Link:{' '}
              <span className="font-mono text-blue-400">{net.case_id}</span>
            </p>
          </div>
        </div>

        {/* Hop Depth Toggle Buttons */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-lg text-xs font-mono">
          <span className="text-slate-500 px-2">Hop Depth:</span>
          {[1, 2, 3].map((d) => (
            <button
              key={d}
              onClick={() => setHopDepth(d)}
              className={`px-3 py-1 rounded font-bold transition-colors ${
                hopDepth === d ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {d}-Hop
            </button>
          ))}
        </div>
      </div>

      {/* Network Money Flow Graph Canvas */}
      <MoneyFlowGraph
        data={{
          case_id: net.case_id,
          nodes: net.nodes || [],
          edges: net.edges || [],
        }}
      />

      {/* Top Entities & Evidence */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <span className="font-bold text-white uppercase block">High Centrality Mule Entities</span>
          {net.top_entities?.map((eId, i) => (
            <div
              key={i}
              onClick={() => router.push(`/entities/${eId}`)}
              className="p-2 rounded bg-slate-950 border border-slate-800 hover:border-slate-700 cursor-pointer text-amber-300 font-bold flex justify-between"
            >
              <span>{eId}</span>
              <span className="text-slate-400 font-sans font-normal">View 360</span>
            </div>
          ))}
        </div>

        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <span className="font-bold text-white uppercase block">Network Structural Evidence</span>
          {net.evidence_summary?.map((ev, i) => (
            <div key={i} className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-300 font-sans">
              • {ev}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

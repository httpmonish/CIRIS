'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Users, ArrowLeft, CreditCard, Smartphone, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { RiskBadge } from '../../../components/ui/RiskBadge';
import { cirisApi } from '../../../lib/api';
import { EntityProfile } from '../../../types/api';

export default function EntityDetailPage() {
  const params = useParams();
  const router = useRouter();
  const entityId = (params.entityId as string) || 'ENTITY_000001';

  const [entity, setEntity] = useState<EntityProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    cirisApi
      .getEntity(entityId)
      .then((res) => setEntity(res))
      .catch((err) => console.error('Error fetching entity:', err))
      .finally(() => setIsLoading(false));
  }, [entityId]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading Entity 360 Profile...</div>;
  }

  if (!entity) {
    return (
      <div className="p-8 text-center text-xs text-slate-400">
        Entity profile for {entityId} not found in database.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl animate-in fade-in duration-300">
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
              <h2 className="text-xl font-extrabold text-white font-mono">{entity.entity_id}</h2>
              <RiskBadge score={entity.mule_risk_score} />
            </div>
            <p className="text-xs text-slate-400 font-mono">Primary Mule Account: {entity.primary_account}</p>
          </div>
        </div>
      </div>

      {/* Grid of Attributes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Linked Accounts */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <span className="text-xs font-bold text-white uppercase font-mono flex items-center gap-1.5">
            <CreditCard className="w-4 h-4 text-amber-400" /> Linked Bank Accounts
          </span>
          <div className="space-y-1 font-mono text-xs text-slate-300">
            {entity.linked_accounts?.map((acc, i) => (
              <div key={i} className="p-2 rounded bg-slate-950 border border-slate-800 flex justify-between">
                <span>{acc}</span>
                <span className="text-amber-400 font-bold">MULE CANDIDATE</span>
              </div>
            ))}
          </div>
        </div>

        {/* UPI Identifiers */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <span className="text-xs font-bold text-white uppercase font-mono flex items-center gap-1.5">
            <Smartphone className="w-4 h-4 text-blue-400" /> Linked UPI Handles & Cards
          </span>
          <div className="space-y-1 font-mono text-xs text-slate-300">
            {entity.upi_ids?.map((upi, i) => (
              <div key={i} className="p-2 rounded bg-slate-950 border border-slate-800">
                UPI: <span className="text-blue-300">{upi}</span>
              </div>
            ))}
            {entity.cards?.map((card, i) => (
              <div key={i} className="p-2 rounded bg-slate-950 border border-slate-800">
                Card: <span className="text-purple-300">{card}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Associated Cases */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
        <span className="text-xs font-bold text-white uppercase font-mono">Associated Cybercrime Cases</span>
        <div className="flex gap-2">
          {entity.associated_cases?.map((cId) => (
            <button
              key={cId}
              onClick={() => router.push(`/cases/${cId}`)}
              className="px-3 py-1.5 rounded bg-blue-950 border border-blue-800 text-blue-300 text-xs font-mono font-bold hover:bg-blue-900"
            >
              {cId}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

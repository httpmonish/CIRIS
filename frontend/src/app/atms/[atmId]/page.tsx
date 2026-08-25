'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Building2, ArrowLeft, MapPin, Clock } from 'lucide-react';
import { RiskBadge } from '../../../components/ui/RiskBadge';
import { cirisApi } from '../../../lib/api';
import { ATMDetail } from '../../../types/api';

export default function ATMDetailPage() {
  const params = useParams();
  const router = useRouter();
  const atmId = (params.atmId as string) || 'ATM_000349';

  const [atm, setAtm] = useState<ATMDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    cirisApi
      .getATM(atmId)
      .then((res) => setAtm(res))
      .catch((err) => console.error('Error fetching ATM:', err))
      .finally(() => setIsLoading(false));
  }, [atmId]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading ATM Spatial Intelligence...</div>;
  }

  if (!atm) {
    return <div className="p-8 text-center text-xs text-slate-400">ATM {atmId} not found.</div>;
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
              <h2 className="text-xl font-extrabold text-white font-mono">{atm.atm_id}</h2>
              <RiskBadge score={atm.risk_score} />
            </div>
            <p className="text-xs text-slate-400 font-mono">
              Bank: <span className="text-white font-bold">{atm.bank_name}</span> | District:{' '}
              <span className="text-slate-200">{atm.district}, {atm.city}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Spatial Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] text-slate-500 uppercase block">Geo Coordinates</span>
          <span className="text-white font-bold">
            {atm.latitude}, {atm.longitude}
          </span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] text-slate-500 uppercase block">24h Historical Cashouts</span>
          <span className="text-rose-400 font-bold text-base">{atm.historical_cashouts_24h} Events</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
          <span className="text-[10px] text-slate-500 uppercase block">Linked Cyber Cases</span>
          <span className="text-blue-400 font-bold">{atm.associated_cases?.length || 1} Active</span>
        </div>
      </div>

      {/* Associated Cases List */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
        <span className="text-xs font-bold text-white uppercase font-mono">Associated Fraud Complaints</span>
        <div className="flex gap-2">
          {atm.associated_cases?.map((cId) => (
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

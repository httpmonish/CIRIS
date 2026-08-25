'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Activity, Play, Bell, Shield, CheckCircle } from 'lucide-react';
import { cirisApi } from '../../lib/api';

export const Header: React.FC = () => {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [systemStatus, setSystemStatus] = useState<string>('CHECKING...');
  const [isHealthy, setIsHealthy] = useState<boolean>(false);

  useEffect(() => {
    cirisApi
      .getHealth()
      .then((res) => {
        if (res.status === 'OK') {
          setSystemStatus('OPERATIONAL');
          setIsHealthy(true);
        } else {
          setSystemStatus('DEGRADED');
        }
      })
      .catch(() => {
        setSystemStatus('OFFLINE');
        setIsHealthy(false);
      });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const query = searchQuery.trim();
    if (!query) return;

    if (query.toUpperCase().startsWith('CASE') || query.toUpperCase().startsWith('CMP')) {
      router.push(`/cases/${query}`);
    } else if (query.toUpperCase().startsWith('ENTITY')) {
      router.push(`/entities/${query}`);
    } else if (query.toUpperCase().startsWith('TX') || query.toUpperCase().startsWith('EDGE')) {
      router.push(`/transactions/${query}`);
    } else if (query.toUpperCase().startsWith('ATM')) {
      router.push(`/atms/${query}`);
    } else if (query.toUpperCase().startsWith('NET')) {
      router.push(`/networks/${query}`);
    } else {
      router.push(`/cases?search=${encodeURIComponent(query)}`);
    }
  };

  return (
    <header className="h-16 bg-slate-950/90 backdrop-blur border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Global Search Bar */}
      <form onSubmit={handleSearch} className="relative w-96">
        <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Search Case ID, Entity, Transaction, ATM, Network..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </form>

      {/* Header Status & Quick Actions */}
      <div className="flex items-center gap-4">
        {/* System Health Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
            }`}
          />
          <span className="text-slate-400 font-mono text-[11px]">API:</span>
          <span className={`font-bold font-mono text-[11px] ${isHealthy ? 'text-emerald-400' : 'text-rose-400'}`}>
            {systemStatus}
          </span>
        </div>

        {/* Demo Mode Direct Launch */}
        <div className="flex items-center gap-1.5 bg-blue-950/40 border border-blue-800/50 p-1 rounded-lg">
          <button
            onClick={() => router.push('/cases/CASE-DEMO-001')}
            className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            <Play className="w-3 h-3 fill-current" /> Demo 1 (ATM)
          </button>
          <button
            onClick={() => router.push('/cases/CASE-DEMO-002')}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-blue-300 text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            <Play className="w-3 h-3 fill-current" /> Demo 2 (Merchant)
          </button>
        </div>

        {/* User Badge */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
          <div className="w-8 h-8 rounded-full bg-blue-900/60 border border-blue-700/60 flex items-center justify-center text-blue-300 font-bold text-xs">
            IO
          </div>
          <div className="text-left">
            <div className="text-xs font-semibold text-white">Investigating Officer</div>
            <div className="text-[10px] text-slate-500 font-mono">LEA / Bank Ops</div>
          </div>
        </div>
      </div>
    </header>
  );
};

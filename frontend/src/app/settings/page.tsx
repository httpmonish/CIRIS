'use client';

import React, { useState, useEffect } from 'react';
import { Settings, Server, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { cirisApi } from '../../lib/api';
import { SystemStatus } from '../../types/api';

export default function SettingsPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const res = await cirisApi.getSystemStatus();
      setStatus(res);
    } catch (err) {
      console.error('Error fetching system status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <div className="space-y-6 max-w-3xl animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Settings className="w-6 h-6 text-slate-400" /> System Diagnostics & Backend Status
          </h2>
          <p className="text-xs text-slate-400">
            Real-time health audits of CIRIS FastAPI backend, ML models, database, and pipeline components.
          </p>
        </div>
        <button
          onClick={fetchStatus}
          className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Run Diagnostics
        </button>
      </div>

      {/* Backend API Base URL Config Info */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2 font-mono text-xs">
        <div className="text-slate-400">Active API Base URL</div>
        <div className="text-blue-400 font-bold text-sm">
          {process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000'}
        </div>
      </div>

      {/* Components Status Grid */}
      {status ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          {Object.entries(status.components || {}).map(([key, val]) => (
            <div key={key} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-slate-400 uppercase">{key.replace('_', ' ')}</span>
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                  {val}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center text-xs text-slate-500 italic">Checking backend system status...</div>
      )}
    </div>
  );
}

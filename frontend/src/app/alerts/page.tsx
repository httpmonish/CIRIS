'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Bell, ShieldAlert, CheckCircle, UserPlus, ArrowUpRight } from 'lucide-react';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { cirisApi } from '../../lib/api';
import { AlertItem } from '../../types/api';

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [filterPriority, setFilterPriority] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadAlerts = async () => {
    setIsLoading(true);
    try {
      const res = await cirisApi.getAlerts();
      if (Array.isArray(res)) setAlerts(res);
    } catch (err) {
      console.error('Error fetching alerts:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleAcknowledge = async (id: string) => {
    try {
      await cirisApi.acknowledgeAlert(id);
      setActionMsg(`Alert ${id} acknowledged!`);
      loadAlerts();
    } catch (err: any) {
      setActionMsg(`Error acknowledging: ${err.message}`);
    }
  };

  const handleAssign = async (id: string) => {
    const officer = prompt('Enter Officer ID to assign:', 'Officer_Sharma_LEA');
    if (!officer) return;
    try {
      await cirisApi.assignAlert(id, officer);
      setActionMsg(`Alert ${id} assigned to ${officer}!`);
      loadAlerts();
    } catch (err: any) {
      setActionMsg(`Error assigning: ${err.message}`);
    }
  };

  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  const filteredAlerts = safeAlerts.filter((a) => {
    if (filterPriority === 'ALL') return true;
    return a.priority === filterPriority;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <Bell className="w-6 h-6 text-amber-400" /> Priority Cybercrime Alerts Queue
          </h2>
          <p className="text-xs text-slate-400">
            Real-time P1-P4 priority triage queue for high-velocity cashout windows and suspect mule networks.
          </p>
        </div>

        {/* Priority Filter Buttons */}
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 p-1 rounded-lg text-xs font-mono">
          {['ALL', 'P1', 'P2', 'P3', 'P4'].map((p) => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              className={`px-3 py-1 rounded font-bold transition-colors ${
                filterPriority === p ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {actionMsg && <div className="p-3 rounded bg-emerald-950/60 border border-emerald-800 text-xs text-emerald-300 font-mono">{actionMsg}</div>}

      {/* Alerts Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px]">
            <tr>
              <th className="p-3">Priority</th>
              <th className="p-3">Alert Title</th>
              <th className="p-3">Case ID</th>
              <th className="p-3">Amount at Risk</th>
              <th className="p-3">Predicted Endpoint</th>
              <th className="p-3">Time Window</th>
              <th className="p-3">Status</th>
              <th className="p-3">Assigned Officer</th>
              <th className="p-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-300 font-mono">
            {filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-6 text-center text-slate-500 italic">
                  {isLoading ? 'Loading priority alerts...' : 'No alerts found matching priority filter.'}
                </td>
              </tr>
            ) : (
              filteredAlerts.map((alert) => (
                <tr key={alert.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3">
                    <RiskBadge level={alert.priority} score={alert.risk_score} />
                  </td>
                  <td className="p-3 font-sans font-semibold text-white max-w-xs">{alert.title}</td>
                  <td className="p-3 text-blue-400 font-bold">{alert.case_id}</td>
                  <td className="p-3 text-emerald-400 font-bold">₹{alert.amount_at_risk.toLocaleString()}</td>
                  <td className="p-3 text-rose-300">{alert.endpoint_type}</td>
                  <td className="p-3 text-amber-300">{alert.time_window}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-200 border border-slate-700">
                      {alert.status}
                    </span>
                  </td>
                  <td className="p-3 text-slate-400">{alert.assigned_to || 'Unassigned'}</td>
                  <td className="p-3">
                    <div className="flex items-center gap-1.5 font-sans">
                      <button
                        onClick={() => handleAcknowledge(alert.id)}
                        title="Acknowledge Alert"
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px]"
                      >
                        Ack
                      </button>
                      <button
                        onClick={() => handleAssign(alert.id)}
                        title="Assign Officer"
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px]"
                      >
                        Assign
                      </button>
                      <button
                        onClick={() => router.push(`/cases/${alert.case_id}`)}
                        className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-semibold flex items-center gap-1"
                      >
                        Open <ArrowUpRight className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

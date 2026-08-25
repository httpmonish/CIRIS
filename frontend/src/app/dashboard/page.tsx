'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  FolderGit2,
  Bell,
  Users,
  IndianRupee,
  Building2,
  ShieldAlert,
  Play,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { MetricCard } from '../../components/ui/MetricCard';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { GISMap } from '../../components/map/GISMap';
import { cirisApi } from '../../lib/api';
import { CaseItem, AlertItem, MapGeoJSON } from '../../types/api';

export default function DashboardPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [casesGeoJson, setCasesGeoJson] = useState<MapGeoJSON | undefined>();
  const [atmsGeoJson, setAtmsGeoJson] = useState<MapGeoJSON | undefined>();
  const [isLoading, setIsLoading] = useState(true);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [casesRes, alertsRes, casesMapRes, atmsMapRes] = await Promise.allSettled([
        cirisApi.getCases(),
        cirisApi.getAlerts(),
        cirisApi.getMapCases(),
        cirisApi.getMapPredictedATMs(),
      ]);

      if (casesRes.status === 'fulfilled' && Array.isArray(casesRes.value)) setCases(casesRes.value);
      if (alertsRes.status === 'fulfilled' && Array.isArray(alertsRes.value)) setAlerts(alertsRes.value);
      if (casesMapRes.status === 'fulfilled' && casesMapRes.value?.features) setCasesGeoJson(casesMapRes.value);
      if (atmsMapRes.status === 'fulfilled' && atmsMapRes.value?.features) setAtmsGeoJson(atmsMapRes.value);
    } catch (err) {
      console.error('Error loading dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const safeCases = Array.isArray(cases) ? cases : [];
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  const totalCases = safeCases.length;
  const criticalCases = safeCases.filter((c) => c.priority === 'P1' || c.overall_case_risk >= 0.75).length;
  const totalAmountAtRisk = safeCases.reduce((sum, c) => sum + (c.disputed_amount || 0), 0);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Top Banner & Refresh */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight">Cybercrime Intelligence Command Center</h2>
          <p className="text-xs text-slate-400">
            Real-time cyber fraud analytics, predictive ATM cash-out alerts, and intervention workflows.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadDashboardData}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <button
            onClick={() => router.push('/cases/CASE-DEMO-001')}
            className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-lg shadow-blue-950 transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" /> Launch Case Demo 1
          </button>
        </div>
      </div>

      {/* KPI Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Fraud Cases"
          value={totalCases || '2'}
          subtitle="Registered investigations"
          icon={FolderGit2}
          onClick={() => router.push('/cases')}
          color="blue"
        />
        <MetricCard
          title="Critical Risk Alerts"
          value={criticalCases || '1'}
          subtitle="P1 Immediate Cash-out window"
          icon={ShieldAlert}
          onClick={() => router.push('/alerts')}
          color="rose"
        />
        <MetricCard
          title="Total Disputed Amount"
          value={`₹${totalAmountAtRisk ? totalAmountAtRisk.toLocaleString() : '85,000'}`}
          subtitle="Observed remaining across mules"
          icon={IndianRupee}
          color="amber"
        />
        <MetricCard
          title="Predicted Endpoints"
          value="2"
          subtitle="ATM Cashouts & Merchant Outlets"
          icon={Building2}
          onClick={() => router.push('/atms/ATM_000349')}
          color="emerald"
        />
      </div>

      {/* Main Grid: GIS Preview + Priority Alerts Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spatial Map Preview (2 Cols) */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm text-white flex items-center gap-2">
              National Cybercrime Spatial Risk Map
            </h3>
            <Link href="/map" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
              Full Map View <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <GISMap casesGeoJson={casesGeoJson} atmsGeoJson={atmsGeoJson} />
        </div>

        {/* Priority Alerts Sidebar (1 Col) */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm text-white flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" /> Priority Intelligence Alerts
            </h3>
            <Link href="/alerts" className="text-xs text-slate-400 hover:text-slate-200">
              View All
            </Link>
          </div>

          <div className="space-y-3">
            {safeAlerts.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400">
                {isLoading ? 'Loading priority alerts...' : 'No priority alerts available.'}
              </div>
            ) : (
              safeAlerts.slice(0, 4).map((alert) => (
                <div
                  key={alert.id}
                  onClick={() => router.push(`/cases/${alert.case_id}`)}
                  className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <RiskBadge level={alert.priority} score={alert.risk_score} />
                    <span className="text-[10px] font-mono text-slate-400">{alert.time_window}</span>
                  </div>
                  <div className="font-semibold text-xs text-white">{alert.title}</div>
                  <div className="flex justify-between items-center text-[10px] font-mono text-slate-400">
                    <span>Case: {alert.case_id}</span>
                    <span className="text-emerald-400 font-bold">₹{alert.amount_at_risk?.toLocaleString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Case Investigations Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-white">Recent Case Investigations</h3>
          <Link href="/cases" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
            View All Cases <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px]">
              <tr>
                <th className="p-3">Case ID</th>
                <th className="p-3">Risk Score</th>
                <th className="p-3">Priority</th>
                <th className="p-3">Fraud Type</th>
                <th className="p-3">Disputed Amount</th>
                <th className="p-3">Predicted Endpoint</th>
                <th className="p-3">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300 font-mono">
              {safeCases.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-4 text-center text-slate-500 italic">
                    No active case investigations found.
                  </td>
                </tr>
              ) : (
                safeCases.map((c) => (
                  <tr key={c.case_id} className="hover:bg-slate-800/40 font-mono">
                    <td className="p-3 font-bold text-blue-400">{c.case_id}</td>
                    <td className="p-3">
                      <RiskBadge score={c.overall_case_risk} />
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold">{c.priority}</span>
                    </td>
                    <td className="p-3 font-sans text-white">{c.fraud_type}</td>
                    <td className="p-3 text-emerald-400 font-bold">₹{c.disputed_amount?.toLocaleString()}</td>
                    <td className="p-3 text-rose-300">{c.predicted_endpoint}</td>
                    <td className="p-3">
                      <button
                        onClick={() => router.push(`/cases/${c.case_id}`)}
                        className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-sans font-medium"
                      >
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FolderGit2, Search, Plus, Filter, ArrowUpRight } from 'lucide-react';
import { RiskBadge } from '../../components/ui/RiskBadge';
import { cirisApi } from '../../lib/api';
import { CaseItem } from '../../types/api';

export default function CasesPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [priorityFilter, setPriorityFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  // New Case Modal State
  const [showNewModal, setShowNewModal] = useState(false);
  const [complaintId, setComplaintId] = useState(`CMP-MANUAL-${Math.floor(Math.random() * 1000)}`);
  const [victimId, setVictimId] = useState('VICTIM_NEW_001');
  const [lossAmount, setLossAmount] = useState('75000');
  const [fraudType, setFraudType] = useState('Investment Cyber Fraud');

  const loadCases = async () => {
    setIsLoading(true);
    try {
      const res = await cirisApi.getCases();
      if (Array.isArray(res)) setCases(res);
    } catch (err) {
      console.error('Error loading cases:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const newCase = await cirisApi.createCase({
        complaint_id: complaintId,
        victim_id: victimId,
        reported_loss_amount: parseFloat(lossAmount),
        fraud_type: fraudType,
      });
      setShowNewModal(false);
      router.push(`/cases/${newCase.case_id}`);
    } catch (err: any) {
      alert(`Error creating case: ${err.message}`);
    }
  };

  const safeCases = Array.isArray(cases) ? cases : [];

  const filteredCases = safeCases.filter((c) => {
    const matchesSearch =
      c.case_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.complaint_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.fraud_type.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || c.status === statusFilter;
    const matchesPriority = priorityFilter === 'ALL' || c.priority === priorityFilter;
    return matchesSearch && matchesStatus && matchesPriority;
  });

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <FolderGit2 className="w-6 h-6 text-blue-400" /> Active Cybercrime Case Registry
          </h2>
          <p className="text-xs text-slate-400">
            Comprehensive investigation catalog with ML risk scores and predicted endpoints.
          </p>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors"
        >
          <Plus className="w-4 h-4" /> Register New Complaint Case
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-3 rounded-xl">
        <div className="relative w-80">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search Case ID, Complaint ID, Fraud Type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        <div className="flex items-center gap-3 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white"
            >
              <option value="ALL">ALL STATUSES</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="PENDING_REVIEW">PENDING REVIEW</option>
              <option value="RESOLVED">RESOLVED</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded px-2 py-1 text-white"
            >
              <option value="ALL">ALL PRIORITIES</option>
              <option value="P1">P1 (Critical)</option>
              <option value="P2">P2 (High)</option>
              <option value="P3">P3 (Medium)</option>
              <option value="P4">P4 (Low)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Case Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px]">
            <tr>
              <th className="p-3">Case ID</th>
              <th className="p-3">Risk Score</th>
              <th className="p-3">Priority</th>
              <th className="p-3">Victim ID</th>
              <th className="p-3">Fraud Type</th>
              <th className="p-3">Disputed Amount</th>
              <th className="p-3">Predicted Endpoint</th>
              <th className="p-3">Status</th>
              <th className="p-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-slate-300 font-mono">
            {filteredCases.length === 0 ? (
              <tr>
                <td colSpan={9} className="p-6 text-center text-slate-500 italic">
                  {isLoading ? 'Loading cases...' : 'No cases matching search criteria.'}
                </td>
              </tr>
            ) : (
              filteredCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 font-bold text-blue-400">{c.case_id}</td>
                  <td className="p-3">
                    <RiskBadge score={c.overall_case_risk} />
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200 font-bold">{c.priority}</span>
                  </td>
                  <td className="p-3 text-slate-400">{c.victim_id}</td>
                  <td className="p-3 font-sans text-white font-medium">{c.fraud_type}</td>
                  <td className="p-3 text-emerald-400 font-bold">₹{c.disputed_amount.toLocaleString()}</td>
                  <td className="p-3 text-rose-300">{c.predicted_endpoint}</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-[10px] bg-slate-800 border border-slate-700 text-slate-300">
                      {c.status}
                    </span>
                  </td>
                  <td className="p-3">
                    <button
                      onClick={() => router.push(`/cases/${c.case_id}`)}
                      className="px-2.5 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-sans font-semibold flex items-center gap-1"
                    >
                      Investigate <ArrowUpRight className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* New Case Creation Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-base font-bold text-white">Register New Cybercrime Complaint</h3>
            <form onSubmit={handleCreateCase} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">NCRP Complaint ID</label>
                <input
                  type="text"
                  value={complaintId}
                  onChange={(e) => setComplaintId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Victim Entity ID</label>
                <input
                  type="text"
                  value={victimId}
                  onChange={(e) => setVictimId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Reported Loss Amount (₹)</label>
                <input
                  type="number"
                  value={lossAmount}
                  onChange={(e) => setLossAmount(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Fraud Classification Type</label>
                <input
                  type="text"
                  value={fraudType}
                  onChange={(e) => setFraudType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-white"
                  required
                />
              </div>

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="flex-1 bg-slate-800 text-slate-300 py-2 rounded text-xs font-semibold"
                >
                  Cancel
                </button>
                <button type="submit" className="flex-1 bg-blue-600 text-white py-2 rounded text-xs font-semibold">
                  Create Case & Run ML Pipeline
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

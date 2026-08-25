'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { CreditCard, ArrowLeft, ArrowRight } from 'lucide-react';
import { RiskBadge } from '../../../components/ui/RiskBadge';
import { cirisApi } from '../../../lib/api';
import { TransactionDetail } from '../../../types/api';

export default function TransactionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const txId = (params.transactionId as string) || 'TX_DEMO_001';

  const [tx, setTx] = useState<TransactionDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    cirisApi
      .getTransaction(txId)
      .then((res) => setTx(res))
      .catch((err) => console.error('Error fetching transaction:', err))
      .finally(() => setIsLoading(false));
  }, [txId]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400 font-mono">Loading Transaction Details...</div>;
  }

  if (!tx) {
    return <div className="p-8 text-center text-xs text-slate-400">Transaction {txId} not found.</div>;
  }

  return (
    <div className="space-y-6 max-w-3xl animate-in fade-in duration-300">
      <div className="flex items-center gap-3 border-b border-slate-800 pb-4">
        <button
          onClick={() => router.back()}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-extrabold text-white font-mono">{tx.transaction_id}</h2>
            <RiskBadge score={tx.risk_score} />
          </div>
          <p className="text-xs text-slate-400 font-mono">Case Link: {tx.associated_case}</p>
        </div>
      </div>

      {/* Transaction Flow Diagram */}
      <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between font-mono">
        <div className="text-center">
          <span className="text-[10px] text-slate-500 uppercase block">Source Account</span>
          <span className="text-sm font-bold text-emerald-400">{tx.source_account}</span>
        </div>
        <div className="text-center px-4">
          <span className="text-xs text-amber-400 font-bold block mb-1">
            ₹{tx.amount.toLocaleString()} ({tx.transaction_type})
          </span>
          <ArrowRight className="w-6 h-6 text-blue-400 mx-auto" />
        </div>
        <div className="text-center">
          <span className="text-[10px] text-slate-500 uppercase block">Destination Account</span>
          <span className="text-sm font-bold text-amber-400">{tx.target_account}</span>
        </div>
      </div>
    </div>
  );
}

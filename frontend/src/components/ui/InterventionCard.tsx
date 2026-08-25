import React, { useState } from 'react';
import { InterventionRecommendation, InterventionReview } from '../../types/api';
import { ShieldAlert, CheckCircle2, AlertOctagon, Send } from 'lucide-react';
import { cirisApi } from '../../lib/api';

interface InterventionCardProps {
  caseId: string;
  recommendation?: InterventionRecommendation;
  existingReview?: InterventionReview;
  onSuccess?: () => void;
}

export const InterventionCard: React.FC<InterventionCardProps> = ({
  caseId,
  recommendation,
  existingReview,
  onSuccess,
}) => {
  const [reviewer, setReviewer] = useState('Officer_Kulkarni_SBI');
  const [decision, setDecision] = useState<'APPROVE_HOLD_REVIEW' | 'DECLINE' | 'MONITOR'>('APPROVE_HOLD_REVIEW');
  const [notes, setNotes] = useState('Hold review passed to bank compliance workflow for lien placement.');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submittedReview, setSubmittedReview] = useState<InterventionReview | null>(existingReview || null);
  const [message, setMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);
    try {
      const res = await cirisApi.reviewIntervention(caseId, reviewer, decision, notes);
      setSubmittedReview(res);
      setMessage('Decision recorded cleanly in operational audit trail!');
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setMessage(`Error submitting review: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEscalate = async () => {
    setIsSubmitting(true);
    setMessage(null);
    try {
      await cirisApi.escalateIntervention(caseId, reviewer, 'High risk active cashout window detected');
      setMessage('Case escalated to LEA / NCRP priority queue!');
      if (onSuccess) onSuccess();
    } catch (err: any) {
      setMessage(`Error escalating: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const recAction = recommendation?.recommended_action || 'HOLD REVIEW';

  return (
    <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <h3 className="font-semibold text-white">Predictive Intervention Recommendation</h3>
        </div>
        <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800">
          {recAction}
        </span>
      </div>

      {recommendation && (
        <div className="space-y-2 text-xs text-slate-300">
          <p className="leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
            {recommendation.action_rationale}
          </p>
          <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Target Accounts: </span>
              <span className="text-amber-300">{recommendation.target_accounts_for_review.join(', ') || 'N/A'}</span>
            </div>
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-slate-400">Hold Amount: </span>
              <span className="text-emerald-400">₹{recommendation.potential_hold_amount.toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Safety Notice */}
      <div className="p-2.5 rounded bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
        <AlertOctagon className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <span>
          <strong>Authorization Boundary:</strong> CIRIS provides predictive decision-support intelligence. Actual account lien/hold operations are executed by authorized bank compliance and LEA officers.
        </span>
      </div>

      {/* Existing Review Status */}
      {submittedReview ? (
        <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-xs space-y-1">
          <div className="flex items-center gap-2 font-semibold text-emerald-300">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Decision Recorded: {submittedReview.decision}
          </div>
          <p className="text-emerald-200/80">Reviewer: {submittedReview.reviewer}</p>
          <p className="text-slate-300 font-mono text-[11px]">Notes: {submittedReview.notes}</p>
        </div>
      ) : (
        /* Form for Investigator Review */
        <form onSubmit={handleSubmit} className="space-y-3 pt-2 border-t border-slate-800">
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="block text-slate-400 mb-1 font-medium">Reviewer Official</label>
              <input
                type="text"
                value={reviewer}
                onChange={(e) => setReviewer(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1 font-medium">Action Decision</label>
              <select
                value={decision}
                onChange={(e: any) => setDecision(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white focus:outline-none focus:border-blue-500"
              >
                <option value="APPROVE_HOLD_REVIEW">APPROVE HOLD REVIEW</option>
                <option value="MONITOR">MONITOR ONLY</option>
                <option value="DECLINE">DECLINE ACTION</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 text-xs font-medium">Compliance Notes / Directive</label>
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-white text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-3 rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              Submit Official Review
            </button>
            <button
              type="button"
              onClick={handleEscalate}
              disabled={isSubmitting}
              className="bg-rose-900/60 hover:bg-rose-800/80 text-rose-200 border border-rose-700/60 font-medium py-2 px-3 rounded-lg text-xs transition-colors disabled:opacity-50"
            >
              Escalate to LEA
            </button>
          </div>
        </form>
      )}

      {message && <p className="text-xs text-emerald-400 font-mono text-center">{message}</p>}
    </div>
  );
};

import React from 'react';
import { SHAPFeature } from '../../types/api';
import { AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface EvidenceCardProps {
  features: SHAPFeature[];
  narrative?: string;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ features, narrative }) => {
  return (
    <div className="space-y-4">
      {narrative && (
        <div className="p-3.5 rounded-lg bg-blue-950/40 border border-blue-800/40 text-xs text-blue-200 leading-relaxed flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold text-blue-300 mb-1">CIRIS XAI Intelligence Briefing</div>
            {narrative}
          </div>
        </div>
      )}

      <div className="space-y-2.5">
        {features.map((item, idx) => {
          const isRiskIncrease = item.direction === 'RISK_INCREASE' || item.shap_value > 0;
          const impactPercent = Math.min(100, Math.round(item.abs_impact * 100));

          return (
            <div key={idx} className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200">{item.friendly_name || item.feature}</span>
                <span className={`flex items-center gap-1 font-mono font-medium ${isRiskIncrease ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {isRiskIncrease ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  SHAP: {item.shap_value >= 0 ? `+${item.shap_value.toFixed(4)}` : item.shap_value.toFixed(4)}
                </span>
              </div>
              
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${isRiskIncrease ? 'bg-rose-500' : 'bg-emerald-500'}`}
                  style={{ width: `${impactPercent}%` }}
                />
              </div>

              <div className="flex justify-between items-center text-[10px] text-slate-400 font-mono">
                <span>Value: {item.value}</span>
                <span>Impact Weight: {(item.abs_impact * 100).toFixed(1)}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

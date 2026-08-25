import React from 'react';

interface RiskBadgeProps {
  score?: number;
  level?: string;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ score, level, className = '' }) => {
  let displayLevel = level ? level.toUpperCase() : 'UNKNOWN';
  let badgeColor = 'bg-slate-800 text-slate-300 border-slate-700';

  if (score !== undefined) {
    if (score >= 0.8) displayLevel = 'CRITICAL';
    else if (score >= 0.5) displayLevel = 'HIGH';
    else if (score >= 0.25) displayLevel = 'MEDIUM';
    else displayLevel = 'LOW';
  }

  switch (displayLevel) {
    case 'CRITICAL':
    case 'P1':
      badgeColor = 'bg-rose-950/80 text-rose-300 border-rose-800/60 animate-pulse';
      break;
    case 'HIGH':
    case 'P2':
      badgeColor = 'bg-amber-950/80 text-amber-300 border-amber-800/60';
      break;
    case 'MEDIUM':
    case 'P3':
      badgeColor = 'bg-blue-950/80 text-blue-300 border-blue-800/60';
      break;
    case 'LOW':
    case 'P4':
      badgeColor = 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badgeColor} ${className}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {displayLevel} {score !== undefined && `(${score.toFixed(2)})`}
    </span>
  );
};

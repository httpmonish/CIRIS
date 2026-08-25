import React from 'react';
import { LucideIcon } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: string;
  onClick?: () => void;
  color?: 'blue' | 'rose' | 'amber' | 'emerald' | 'slate';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  onClick,
  color = 'blue',
}) => {
  const colorStyles = {
    blue: 'border-blue-900/40 hover:border-blue-700/60 bg-gradient-to-br from-slate-900 to-blue-950/20 text-blue-400',
    rose: 'border-rose-900/40 hover:border-rose-700/60 bg-gradient-to-br from-slate-900 to-rose-950/20 text-rose-400',
    amber: 'border-amber-900/40 hover:border-amber-700/60 bg-gradient-to-br from-slate-900 to-amber-950/20 text-amber-400',
    emerald: 'border-emerald-900/40 hover:border-emerald-700/60 bg-gradient-to-br from-slate-900 to-emerald-950/20 text-emerald-400',
    slate: 'border-slate-800 hover:border-slate-700 bg-slate-900/80 text-slate-400',
  };

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-xl border transition-all duration-200 ${colorStyles[color]} ${
        onClick ? 'cursor-pointer hover:scale-[1.01] shadow-lg' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && <Icon className="w-5 h-5 opacity-80" />}
      </div>
      <div className="mt-2 text-2xl font-bold tracking-tight text-white">{value}</div>
      {(subtitle || trend) && (
        <div className="mt-1 flex items-center justify-between text-xs text-slate-400">
          {subtitle && <span>{subtitle}</span>}
          {trend && <span className="font-mono font-medium text-emerald-400">{trend}</span>}
        </div>
      )}
    </div>
  );
};

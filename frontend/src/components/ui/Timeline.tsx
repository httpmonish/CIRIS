import React from 'react';
import { TimelineEvent } from '../../types/api';
import { Clock, ShieldAlert, GitCommit, Search, AlertTriangle, ArrowRight } from 'lucide-react';

interface TimelineProps {
  events: TimelineEvent[];
}

export const Timeline: React.FC<TimelineProps> = ({ events }) => {
  if (!events || events.length === 0) {
    return <div className="text-xs text-slate-500 italic p-4 text-center">No timeline events recorded.</div>;
  }

  const getEventIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'COMPLAINT_FILED':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'RISK_SCORE_COMPUTED':
        return <ShieldAlert className="w-4 h-4 text-rose-400" />;
      case 'MONEY_FLOW_DISCOVERED':
        return <GitCommit className="w-4 h-4 text-blue-400" />;
      case 'PREDICTION_GENERATED':
        return <Search className="w-4 h-4 text-purple-400" />;
      default:
        return <Clock className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
      {events.map((evt, idx) => (
        <div key={idx} className="relative group">
          <div className="absolute -left-[23px] top-1 p-1 rounded-full bg-slate-950 border border-slate-800 group-hover:border-blue-500 transition-colors">
            {getEventIcon(evt.event_type)}
          </div>
          
          <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1 hover:border-slate-700 transition-colors">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-xs text-white">{evt.title}</span>
              <span className="font-mono text-[10px] text-slate-500">
                {new Date(evt.timestamp).toLocaleString()}
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">{evt.description}</p>
            <div className="flex justify-between items-center text-[10px] text-slate-500 pt-1 font-mono">
              <span>Actor: {evt.actor}</span>
              <span className="text-slate-400 font-semibold">{evt.event_type}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

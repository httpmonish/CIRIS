'use client';

import React, { useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { MoneyFlowGraph as MoneyFlowGraphType, MoneyFlowPathNode, MoneyFlowPathEdge } from '../../types/api';

interface MoneyFlowGraphProps {
  data: MoneyFlowGraphType;
  onNodeSelect?: (node: MoneyFlowPathNode) => void;
  onEdgeSelect?: (edge: MoneyFlowPathEdge) => void;
}

export const MoneyFlowGraph: React.FC<MoneyFlowGraphProps> = ({ data, onNodeSelect, onEdgeSelect }) => {
  // Convert API nodes to ReactFlow nodes
  const initialNodes = useMemo(() => {
    if (!data || !data.nodes) return [];

    return data.nodes.map((node, index) => {
      let bg = 'bg-slate-900 border-slate-700 text-slate-200';
      if (node.type === 'VICTIM') {
        bg = 'bg-emerald-950/90 border-emerald-500/80 text-emerald-200 shadow-emerald-950';
      } else if (node.type === 'MULE' || node.type === 'ACCOUNT') {
        bg = 'bg-amber-950/90 border-amber-500/80 text-amber-200 shadow-amber-950';
      } else if (node.type === 'ATM') {
        bg = 'bg-rose-950/90 border-rose-500/80 text-rose-200 shadow-rose-950';
      } else if (node.type === 'MERCHANT') {
        bg = 'bg-blue-950/90 border-blue-500/80 text-blue-200 shadow-blue-950';
      }

      // Automatic layout positioning horizontally across hops
      const xPos = index * 260 + 50;
      const yPos = (index % 2 === 0 ? 80 : 180);

      return {
        id: node.id,
        position: { x: xPos, y: yPos },
        data: {
          label: (
            <div className="p-3 rounded-lg border text-left shadow-lg cursor-pointer transition-all hover:scale-105 min-w-[160px]">
              <div className="flex items-center justify-between text-[10px] font-mono font-bold uppercase mb-1 tracking-wider opacity-80">
                <span>{node.type}</span>
                {node.risk !== undefined && (
                  <span className={node.risk > 0.5 ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                    {(node.risk * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              <div className="font-mono text-xs font-extrabold truncate">{node.id}</div>
              <div className="text-[10px] text-slate-400 truncate">{node.label}</div>
            </div>
          ),
          rawNode: node,
        },
        className: bg,
      };
    });
  }, [data]);

  // Convert API edges to ReactFlow edges
  const initialEdges = useMemo(() => {
    if (!data || !data.edges) return [];

    return data.edges.map((edge, index) => ({
      id: `e-${index}-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      label: `₹${edge.amount.toLocaleString()} (${edge.transaction_type})`,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
      labelStyle: { fill: '#94a3b8', fontSize: 10, fontWeight: 600, fontFamily: 'monospace' },
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9, rx: 4 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#3b82f6',
      },
      data: { rawEdge: edge },
    }));
  }, [data]);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = (_: any, node: any) => {
    if (onNodeSelect && node.data?.rawNode) {
      onNodeSelect(node.data.rawNode);
    }
  };

  const handleEdgeClick = (_: any, edge: any) => {
    if (onEdgeSelect && edge.data?.rawEdge) {
      onEdgeSelect(edge.data.rawEdge);
    }
  };

  return (
    <div className="w-full h-[420px] rounded-xl bg-slate-950 border border-slate-800 overflow-hidden relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        fitView
        attributionPosition="bottom-right"
      >
        <Background color="#1e293b" gap={16} />
        <Controls className="bg-slate-900 border-slate-800 text-slate-300 fill-slate-300" />
      </ReactFlow>

      {/* Graph Legend */}
      <div className="absolute top-3 right-3 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-lg p-2 flex items-center gap-3 text-[10px] font-mono">
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-500" /> Victim</div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500" /> Mule Account</div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-rose-500" /> ATM Cashout</div>
        <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-blue-500" /> Merchant</div>
      </div>
    </div>
  );
};

'use client';

import React, { useState } from 'react';
import { MapGeoJSON, MapFeature } from '../../types/api';
import { MapPin, Layers, Filter, Compass } from 'lucide-react';
import { RiskBadge } from '../ui/RiskBadge';

interface GISMapProps {
  casesGeoJson?: MapGeoJSON;
  atmsGeoJson?: MapGeoJSON;
  riskGeoJson?: MapGeoJSON;
  networksGeoJson?: MapGeoJSON;
  onFeatureSelect?: (feature: MapFeature) => void;
}

export const GISMap: React.FC<GISMapProps> = ({
  casesGeoJson,
  atmsGeoJson,
  riskGeoJson,
  networksGeoJson,
  onFeatureSelect,
}) => {
  const [showCases, setShowCases] = useState(true);
  const [showATMs, setShowATMs] = useState(true);
  const [showRisk, setShowRisk] = useState(true);
  const [showNetworks, setShowNetworks] = useState(true);
  const [selectedFeature, setSelectedFeature] = useState<MapFeature | null>(null);

  // Combine features from enabled layers
  const activeFeatures: MapFeature[] = [
    ...(showCases && casesGeoJson?.features ? casesGeoJson.features : []),
    ...(showATMs && atmsGeoJson?.features ? atmsGeoJson.features : []),
    ...(showRisk && riskGeoJson?.features ? riskGeoJson.features : []),
    ...(showNetworks && networksGeoJson?.features ? networksGeoJson.features : []),
  ];

  const handleMarkerClick = (feat: MapFeature) => {
    setSelectedFeature(feat);
    if (onFeatureSelect) onFeatureSelect(feat);
  };

  return (
    <div className="w-full h-[550px] rounded-xl bg-slate-950 border border-slate-800 overflow-hidden relative flex">
      {/* Map Control Sidebar Overlay */}
      <div className="absolute top-4 left-4 z-20 bg-slate-900/90 backdrop-blur border border-slate-800 rounded-xl p-3.5 space-y-3 w-56">
        <div className="flex items-center gap-2 font-semibold text-xs text-white border-b border-slate-800 pb-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <span>GIS Spatial Layers</span>
        </div>

        <div className="space-y-2 text-xs">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showCases}
              onChange={(e) => setShowCases(e.target.checked)}
              className="rounded accent-emerald-500"
            />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Active Cyber Cases
          </label>
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showATMs}
              onChange={(e) => setShowATMs(e.target.checked)}
              className="rounded accent-rose-500"
            />
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" /> Predicted ATMs
          </label>
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showRisk}
              onChange={(e) => setShowRisk(e.target.checked)}
              className="rounded accent-amber-500"
            />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> Regional Risk Zones
          </label>
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={showNetworks}
              onChange={(e) => setShowNetworks(e.target.checked)}
              className="rounded accent-purple-500"
            />
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> Mule Networks
          </label>
        </div>
      </div>

      {/* Main Map Viewport simulation canvas with interactive spatial grid */}
      <div className="flex-1 bg-slate-950 relative overflow-hidden flex items-center justify-center">
        {/* Grid Background */}
        <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px] opacity-60" />

        {/* Compass Overlay */}
        <div className="absolute top-4 right-4 z-10 text-slate-600 flex items-center gap-1 font-mono text-[10px]">
          <Compass className="w-5 h-5 text-slate-500 animate-spin-slow" /> GIS Spatial Radar (India Hotspots)
        </div>

        {/* Interactive Feature Markers mapped across viewport */}
        <div className="relative w-[90%] h-[80%] border border-slate-800/40 rounded-2xl bg-slate-900/30 p-6 flex flex-wrap gap-8 items-center justify-around">
          {activeFeatures.length === 0 ? (
            <div className="text-xs text-slate-500 font-mono">No layers toggled on.</div>
          ) : (
            activeFeatures.map((feat, idx) => {
              const isATM = feat.properties.type === 'ATM';
              const isCase = feat.properties.type === 'CASE';
              const isRiskZone = feat.properties.type === 'RISK_ZONE';

              let markerBg = 'bg-blue-600 border-blue-400 text-white';
              if (isATM) markerBg = 'bg-rose-600 border-rose-400 text-white animate-bounce';
              if (isCase) markerBg = 'bg-emerald-600 border-emerald-400 text-white';
              if (isRiskZone) markerBg = 'bg-amber-600 border-amber-400 text-white';

              return (
                <div
                  key={idx}
                  onClick={() => handleMarkerClick(feat)}
                  className={`p-3 rounded-xl border cursor-pointer transition-all duration-300 hover:scale-110 shadow-2xl flex items-center gap-2.5 ${markerBg}`}
                >
                  <MapPin className="w-4 h-4 shrink-0" />
                  <div className="text-left font-mono">
                    <div className="text-xs font-bold leading-tight">{feat.properties.title}</div>
                    <div className="text-[10px] opacity-80">{feat.properties.district || 'Spatial Coordinates'}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Feature Detail Drawer Overlay */}
        {selectedFeature && (
          <div className="absolute bottom-4 right-4 left-64 z-30 bg-slate-900/95 backdrop-blur border border-slate-800 rounded-xl p-4 flex items-center justify-between text-xs animate-in slide-in-from-bottom duration-200">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">{selectedFeature.properties.title}</span>
                <RiskBadge score={selectedFeature.properties.risk} />
              </div>
              <p className="text-slate-400 font-mono text-[11px]">
                District: {selectedFeature.properties.district || 'National Central'} | Type: {selectedFeature.properties.type}
              </p>
            </div>
            <button
              onClick={() => setSelectedFeature(null)}
              className="px-3 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 font-mono text-[11px]"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

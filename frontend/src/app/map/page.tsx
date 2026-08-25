'use client';

import React, { useState, useEffect } from 'react';
import { GISMap } from '../../components/map/GISMap';
import { cirisApi } from '../../lib/api';
import { MapGeoJSON } from '../../types/api';
import { MapPin, RefreshCw } from 'lucide-react';

export default function MapPage() {
  const [casesGeoJson, setCasesGeoJson] = useState<MapGeoJSON | undefined>();
  const [atmsGeoJson, setAtmsGeoJson] = useState<MapGeoJSON | undefined>();
  const [riskGeoJson, setRiskGeoJson] = useState<MapGeoJSON | undefined>();
  const [networksGeoJson, setNetworksGeoJson] = useState<MapGeoJSON | undefined>();
  const [isLoading, setIsLoading] = useState(true);

  const loadMapData = async () => {
    setIsLoading(true);
    try {
      const [cRes, aRes, rRes, nRes] = await Promise.allSettled([
        cirisApi.getMapCases(),
        cirisApi.getMapPredictedATMs(),
        cirisApi.getMapRisk(),
        cirisApi.getMapNetworks(),
      ]);

      if (cRes.status === 'fulfilled') setCasesGeoJson(cRes.value);
      if (aRes.status === 'fulfilled') setAtmsGeoJson(aRes.value);
      if (rRes.status === 'fulfilled') setRiskGeoJson(rRes.value);
      if (nRes.status === 'fulfilled') setNetworksGeoJson(nRes.value);
    } catch (err) {
      console.error('Error fetching GIS layers:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMapData();
  }, []);

  return (
    <div className="space-y-4 animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
            <MapPin className="w-6 h-6 text-rose-400" /> Fullscreen Cybercrime GIS Spatial Workspace
          </h2>
          <p className="text-xs text-slate-400">
            Multi-layer spatial analytics across active cases, predicted ATM cash-out endpoints, and regional risk zones.
          </p>
        </div>
        <button
          onClick={loadMapData}
          className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-300 flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} /> Refresh GIS Layers
        </button>
      </div>

      <GISMap
        casesGeoJson={casesGeoJson}
        atmsGeoJson={atmsGeoJson}
        riskGeoJson={riskGeoJson}
        networksGeoJson={networksGeoJson}
      />
    </div>
  );
}

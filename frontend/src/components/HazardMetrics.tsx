import React, { useMemo } from 'react';
import { ShieldAlert, Car, Siren, Droplets, AlertOctagon } from 'lucide-react';

interface HazardMetricsProps {
  depthFrame: number[][] | null;
  cellAreaM2?: number; // 40m * 40m = 1600 m2
}

export const HazardMetrics: React.FC<HazardMetricsProps> = ({
  depthFrame,
  cellAreaM2 = 1600,
}) => {
  if (!depthFrame) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col gap-3 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 w-48 bg-slate-800 rounded" />
          <div className="h-4 w-24 bg-slate-800 rounded" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-slate-800/40 border border-slate-800 rounded-xl p-2.5 h-16 flex flex-col justify-between">
              <div className="h-2.5 w-20 bg-slate-800 rounded" />
              <div className="h-4 w-16 bg-slate-700/80 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const stats = useMemo(() => {
    let wet = 0;
    let impassable = 0;
    let emergency = 0;
    let severe = 0;
    let volume = 0;
    let maxD = 0;

    for (let r = 0; r < depthFrame.length; r++) {
      for (let c = 0; c < depthFrame[r].length; c++) {
        const d = depthFrame[r][c];
        if (d > maxD) maxD = d;
        if (d >= 0.05) wet++;
        if (d >= 0.15) impassable++;
        if (d >= 0.30) emergency++;
        if (d >= 0.60) severe++;
        volume += d * cellAreaM2;
      }
    }

    return {
      totalCells: depthFrame.length * depthFrame[0].length,
      wetCells: wet,
      impassableCells: impassable,
      emergencyCutoffCells: emergency,
      severeCells: severe,
      totalVolumeM3: volume,
      maxDepth: maxD,
    };
  }, [depthFrame, cellAreaM2]);

  const floodedPercent = ((stats.wetCells / stats.totalCells) * 100).toFixed(1);
  const impassablePercent = ((stats.impassableCells / stats.totalCells) * 100).toFixed(1);

  // Determine overall urban alert level
  let alertBadge = {
    label: 'SAFE / NORMAL',
    color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  };
  if (stats.severeCells > 50 || stats.emergencyCutoffCells > 150) {
    alertBadge = {
      label: 'CRITICAL / FLOOD EMERGENCY',
      color: 'text-rose-400 bg-rose-500/10 border-rose-500/20 animate-pulse',
    };
  } else if (stats.impassableCells > 100) {
    alertBadge = {
      label: 'WARNING / STREETS IMPASSABLE',
      color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    };
  } else if (stats.wetCells > 50) {
    alertBadge = {
      label: 'ADVISORY / URBAN RUNOFF',
      color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    };
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-bold text-white uppercase tracking-wider">
            Urban Street Hazard Assessment
          </h3>
        </div>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${alertBadge.color}`}>
          {alertBadge.label}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {/* Total Inundation Area */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Droplets className="w-3 h-3 text-cyan-400" /> Catchment Flood
          </div>
          <div className="text-base font-bold text-white font-mono mt-0.5">
            {floodedPercent}%
          </div>
          <div className="text-[9px] text-slate-500">
            {((stats.wetCells * cellAreaM2) / 10000).toFixed(1)} ha submerged
          </div>
        </div>

        {/* Impassable Roads */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Car className="w-3 h-3 text-amber-400" /> Car Stall Risk (&ge;15cm)
          </div>
          <div className="text-base font-bold text-amber-300 font-mono mt-0.5">
            {impassablePercent}%
          </div>
          <div className="text-[9px] text-slate-500">
            {stats.impassableCells} road segments
          </div>
        </div>

        {/* Emergency Vehicle Cutoff */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <Siren className="w-3 h-3 text-rose-400" /> Emergency Cutoff (&ge;30cm)
          </div>
          <div className="text-base font-bold text-rose-300 font-mono mt-0.5">
            {stats.emergencyCutoffCells}
          </div>
          <div className="text-[9px] text-slate-500">
            {((stats.emergencyCutoffCells * cellAreaM2) / 10000).toFixed(1)} ha blocked
          </div>
        </div>

        {/* Total Retention Volume */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-400 flex items-center gap-1">
            <AlertOctagon className="w-3 h-3 text-indigo-400" /> Retention Volume
          </div>
          <div className="text-base font-bold text-indigo-300 font-mono mt-0.5">
            {(stats.totalVolumeM3 / 1000).toFixed(0)} <span className="text-xs font-normal">m³</span>
          </div>
          <div className="text-[9px] text-slate-500">
            {(stats.totalVolumeM3 / 1000000).toFixed(2)} megaliters (ML)
          </div>
        </div>
      </div>
    </div>
  );
};


import React, { useMemo } from 'react';
import { Droplets, Info, Layers, Waves, AlertCircle } from 'lucide-react';

export interface HazardThresholdsConfig {
  source: string;
  wet_m: number;
  impassable_m: number;
  critical_m: number;
}

interface HazardMetricsProps {
  depthFrame: number[][] | null;
  cellAreaM2?: number; // 40m * 40m = 1600 m2
  thresholds?: HazardThresholdsConfig;
}

export const HazardMetrics: React.FC<HazardMetricsProps> = ({
  depthFrame,
  cellAreaM2 = 1600,
  thresholds = {
    source: 'ILLUSTRATIVE, not an official standard',
    wet_m: 0.05,
    impassable_m: 0.15,
    critical_m: 0.30,
  },
}) => {
  if (!depthFrame) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3 animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 w-48 bg-slate-200 rounded" />
          <div className="h-4 w-24 bg-slate-200 rounded" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-slate-50 border border-slate-200 rounded-xl p-2.5 h-16 flex flex-col justify-between">
              <div className="h-2.5 w-20 bg-slate-200 rounded" />
              <div className="h-4 w-16 bg-slate-300 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const impassableThreshold = thresholds?.impassable_m ?? 0.15;
  const criticalThreshold = thresholds?.critical_m ?? 0.30;
  const wetThreshold = thresholds?.wet_m ?? 0.05;

  const stats = useMemo(() => {
    let wet = 0;
    let impassable = 0;
    let critical = 0;
    let severe = 0;
    let volume = 0;
    let maxD = 0;

    for (let r = 0; r < depthFrame.length; r++) {
      for (let c = 0; c < depthFrame[r].length; c++) {
        const d = depthFrame[r][c];
        if (d > maxD) maxD = d;
        if (d >= wetThreshold) wet++;
        if (d >= impassableThreshold) impassable++;
        if (d >= criticalThreshold) critical++;
        if (d >= 0.60) severe++;
        volume += d * cellAreaM2;
      }
    }

    return {
      totalCells: depthFrame.length * depthFrame[0].length,
      wetCells: wet,
      impassableCells: impassable,
      criticalCells: critical,
      severeCells: severe,
      totalVolumeM3: volume,
      maxDepth: maxD,
    };
  }, [depthFrame, cellAreaM2, wetThreshold, impassableThreshold, criticalThreshold]);

  const floodedPercent = ((stats.wetCells / stats.totalCells) * 100).toFixed(1);
  const impassablePercent = ((stats.impassableCells / stats.totalCells) * 100).toFixed(1);

  // Determine illustrative depth severity indicator (no official municipal terminology)
  let severityBadge = {
    label: 'Minimal surface water (< 0.05 m)',
    color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  };
  if (stats.criticalCells > 150 || stats.severeCells > 50) {
    severityBadge = {
      label: `Substantial depth (> ${(criticalThreshold * 100).toFixed(0)} cm)`,
      color: 'text-rose-700 bg-rose-50 border-rose-200',
    };
  } else if (stats.impassableCells > 100) {
    severityBadge = {
      label: `Moderate depth (> ${(impassableThreshold * 100).toFixed(0)} cm)`,
      color: 'text-amber-800 bg-amber-50 border-amber-200',
    };
  } else if (stats.wetCells > 50) {
    severityBadge = {
      label: 'Minor runoff (> 0.05 m)',
      color: 'text-cyan-700 bg-cyan-50 border-cyan-200',
    };
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3 text-slate-900">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-600" />
          <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
            Illustrative hazard levels
            <div className="relative group cursor-help inline-flex items-center">
              <Info className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600 transition" />
              <div className="absolute left-0 bottom-full mb-2 w-72 p-2.5 bg-white border border-slate-200 rounded-xl shadow-xl text-[10px] leading-relaxed text-slate-700 hidden group-hover:block z-50 pointer-events-none normal-case font-normal">
                <span className="font-bold text-amber-700 block mb-0.5">
                  {thresholds.source}
                </span>
                Depth thresholds ({Math.round(impassableThreshold * 100)} cm and {Math.round(criticalThreshold * 100)} cm) are illustrative markers for simulated demonstration and do not constitute an official municipal emergency hazard classification.
              </div>
            </div>
          </h3>
        </div>
        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${severityBadge.color}`}>
          {severityBadge.label}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {/* Surface Inundation Extent */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <Droplets className="w-3 h-3 text-cyan-600" /> Wetted Area (&ge; 5 cm)
          </div>
          <div className="text-base font-bold text-slate-900 font-mono mt-0.5">
            {floodedPercent}%
          </div>
          <div className="text-[9px] text-slate-400">
            {((stats.wetCells * cellAreaM2) / 10000).toFixed(1)} ha inundated
          </div>
        </div>

        {/* 15 cm Illustrative Threshold */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <Waves className="w-3 h-3 text-amber-600" /> Depth &ge; {Math.round(impassableThreshold * 100)} cm
          </div>
          <div className="text-base font-bold text-amber-700 font-mono mt-0.5">
            {impassablePercent}%
          </div>
          <div className="text-[9px] text-slate-400">
            {stats.impassableCells} cells (&ge; {Math.round(impassableThreshold * 100)} cm)
          </div>
        </div>

        {/* 30 cm Illustrative Threshold */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-rose-600" /> Depth &ge; {Math.round(criticalThreshold * 100)} cm
          </div>
          <div className="text-base font-bold text-rose-700 font-mono mt-0.5">
            {stats.criticalCells}
          </div>
          <div className="text-[9px] text-slate-400">
            {((stats.criticalCells * cellAreaM2) / 10000).toFixed(1)} ha (&ge; {Math.round(criticalThreshold * 100)} cm)
          </div>
        </div>

        {/* Peak Water Depth */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <Waves className="w-3 h-3 text-indigo-600" /> Peak Frame Depth
          </div>
          <div className="text-base font-bold text-indigo-700 font-mono mt-0.5">
            {stats.maxDepth.toFixed(3)} m
          </div>
          <div className="text-[9px] text-slate-400">
            Vol: {Math.round(stats.totalVolumeM3).toLocaleString()} m³
          </div>
        </div>
      </div>
    </div>
  );
};

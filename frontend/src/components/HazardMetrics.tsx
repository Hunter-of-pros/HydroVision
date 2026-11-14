import React, { useMemo } from 'react';
import { Info } from 'lucide-react';

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
  const wetHa = ((stats.wetCells * cellAreaM2) / 10000).toFixed(1);
  const criticalHa = ((stats.criticalCells * cellAreaM2) / 10000).toFixed(1);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-4 text-slate-900">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-slate-800">
          Illustrative hazard levels
        </h3>
        <div className="relative group cursor-help inline-flex items-center">
          <Info className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600 transition" />
          <div className="absolute right-0 top-full mt-1.5 w-64 p-2.5 bg-white border border-slate-200 rounded-xl shadow-xl text-[10px] leading-relaxed text-slate-700 hidden group-hover:block z-50 pointer-events-none normal-case font-normal">
            <span className="font-bold text-amber-700 block mb-0.5">
              {thresholds.source}
            </span>
            Depth thresholds ({Math.round(impassableThreshold * 100)} cm and {Math.round(criticalThreshold * 100)} cm) are illustrative markers for simulated demonstration and do not constitute an official municipal emergency hazard classification.
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3.5">
        {/* Row 1: Wetted Area */}
        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-slate-500 font-medium">
            Wetted Area (&ge; 5 cm) &middot; {wetHa} ha inundated
          </div>
          <div className="text-3xl font-extrabold text-slate-800 font-mono tracking-tight">
            {floodedPercent}%
          </div>
          <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-sky-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, Number(floodedPercent)))}%` }}
            />
          </div>
        </div>

        {/* Row 2: Depth >= 15 cm */}
        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-slate-500 font-medium">
            Depth &ge; {Math.round(impassableThreshold * 100)} cm &middot; {stats.impassableCells} cells
          </div>
          <div className="text-3xl font-extrabold text-[#b45309] font-mono tracking-tight">
            {impassablePercent}%
          </div>
          <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-400 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, Math.max(0, Number(impassablePercent)))}%` }}
            />
          </div>
        </div>

        {/* Row 3: Depth >= 30 cm */}
        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-slate-500 font-medium">
            Depth &ge; {Math.round(criticalThreshold * 100)} cm &middot; impassable threshold
          </div>
          <div className="text-3xl font-extrabold text-[#dc2626] font-mono tracking-tight">
            {criticalHa} ha
          </div>
          <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-rose-500 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  Math.max(0, (stats.criticalCells / stats.totalCells) * 100 * 3)
                )}%`,
              }}
            />
          </div>
        </div>

        {/* Row 4: Peak Frame Depth */}
        <div className="flex flex-col gap-1">
          <div className="text-[11px] text-slate-500 font-medium">
            Peak Frame Depth &middot; Vol {Math.round(stats.totalVolumeM3).toLocaleString()} m³
          </div>
          <div className="text-3xl font-extrabold text-[#1e1b4b] font-mono tracking-tight">
            {stats.maxDepth.toFixed(2)} m
          </div>
        </div>
      </div>
    </div>
  );
};

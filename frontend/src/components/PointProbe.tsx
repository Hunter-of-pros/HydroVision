import React from 'react';
import { MapPin, X, TrendingUp, AlertTriangle } from 'lucide-react';

interface PointProbeProps {
  selectedCell: { row: number; col: number; elevation: number } | null;
  depthTimeseries: number[]; // Water depth at this cell over all 121 frames
  currentFrame: number;
  totalFrames: number;
  onClear: () => void;
}

export const PointProbe: React.FC<PointProbeProps> = ({
  selectedCell,
  depthTimeseries,
  currentFrame,
  totalFrames,
  onClear,
}) => {
  if (!selectedCell || !depthTimeseries || depthTimeseries.length === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex items-center justify-between text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-cyan-600" />
          <span>Click anywhere on the map to drop a probe pin and inspect localized flood hydrograph.</span>
        </div>
      </div>
    );
  }

  const currentDepth = depthTimeseries[currentFrame] || 0;
  const peakDepth = Math.max(0.01, ...depthTimeseries);
  const peakFrame = depthTimeseries.indexOf(peakDepth);

  // Find arrival time (first frame with depth >= 0.05m)
  const arrivalFrame = depthTimeseries.findIndex((d) => d >= 0.05);

  return (
    <div className="bg-white border border-cyan-300 rounded-2xl p-4 shadow-sm flex flex-col gap-3 relative text-slate-900">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-50 text-cyan-700 border border-cyan-200">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
              Probe Location: Cell [{selectedCell.row}, {selectedCell.col}]
              <span className="text-[10px] text-slate-500 font-mono font-normal">
                (Elev: {selectedCell.elevation.toFixed(1)}m)
              </span>
            </div>
            <div className="text-[10px] text-slate-500">
              Live hydrograph curve: Inundation evolution over the 2-hour storm
            </div>
          </div>
        </div>

        <button
          onClick={onClear}
          className="p-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition"
          title="Clear probe pin"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Hydrograph Stats Badges */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500">Current Depth</div>
          <div className={`text-base font-bold font-mono ${currentDepth >= 0.05 ? 'text-cyan-700' : 'text-slate-700'}`}>
            {currentDepth.toFixed(3)} m
          </div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <TrendingUp className="w-3 h-3 text-brand-600" /> Peak Depth
          </div>
          <div className="text-base font-bold font-mono text-slate-900">
            {peakDepth.toFixed(3)} m
          </div>
          <div className="text-[9px] text-slate-400 font-mono">at +{peakFrame}m</div>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-2.5">
          <div className="text-[10px] text-slate-500 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> Inundation Arrival
          </div>
          <div className="text-base font-bold font-mono text-amber-700">
            {arrivalFrame >= 0 ? `+${arrivalFrame} min` : 'None (Dry)'}
          </div>
          <div className="text-[9px] text-slate-400 font-mono">threshold 5cm</div>
        </div>
      </div>

      {/* SVG Hydrograph Curve */}
      <div className="relative h-20 w-full bg-slate-50 rounded-xl p-2 border border-slate-200 overflow-hidden">
        <svg
          viewBox={`0 0 ${depthTimeseries.length} 100`}
          preserveAspectRatio="none"
          className="w-full h-full"
        >
          <defs>
            <linearGradient id="hydrographGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0891b2" stopOpacity="0.7" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.1" />
            </linearGradient>
          </defs>

          {/* Area fill */}
          <polygon
            points={`0,100 ${depthTimeseries
              .map((d, i) => `${i},${100 - (d / peakDepth) * 85}`)
              .join(' ')} ${depthTimeseries.length - 1},100`}
            fill="url(#hydrographGradient)"
          />

          {/* Line stroke */}
          <polyline
            points={depthTimeseries.map((d, i) => `${i},${100 - (d / peakDepth) * 85}`).join(' ')}
            fill="none"
            stroke="#0891b2"
            strokeWidth={1.8}
            strokeLinecap="round"
          />

          {/* 5cm flood threshold horizontal guideline */}
          {peakDepth >= 0.05 && (
            <line
              x1={0}
              y1={100 - (0.05 / peakDepth) * 85}
              x2={depthTimeseries.length}
              y2={100 - (0.05 / peakDepth) * 85}
              stroke="#eab308"
              strokeWidth={0.8}
              strokeDasharray="2 1"
            />
          )}

          {/* Current Frame Vertical Cursor */}
          <line
            x1={(currentFrame / totalFrames) * depthTimeseries.length}
            y1={0}
            x2={(currentFrame / totalFrames) * depthTimeseries.length}
            y2={100}
            stroke="#f59e0b"
            strokeWidth={1.5}
            strokeDasharray="2 1"
          />
        </svg>
      </div>

      <div className="flex justify-between text-[10px] text-slate-400 font-mono">
        <span>0 min</span>
        <span>Water Depth Hydrograph h(t)</span>
        <span>120 min</span>
      </div>
    </div>
  );
};


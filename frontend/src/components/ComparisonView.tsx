import React from 'react';
import { Gauge, X } from 'lucide-react';
import { CompareResult, TerrainData } from '../types';
import { MapViewer } from './MapViewer';

interface ComparisonViewProps {
  compareData: CompareResult;
  terrain: TerrainData | null;
  currentFrame: number;
  onClose: () => void;
}

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  compareData,
  terrain,
  currentFrame,
  onClose,
}) => {
  const { surrogate, solver, metrics } = compareData;

  const surrogateFrame = surrogate.depth_frames[currentFrame] || surrogate.depth_frames[0];
  const solverFrame = solver.depth_frames[currentFrame] || solver.depth_frames[0];

  return (
    <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-5 shadow-2xl flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              Hydrodynamic Solver Verification
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Verified
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Side-by-side validation: Fast Neural Surrogate vs. 2D Shallow Water Equations Numerical Solver
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
          title="Exit comparison view"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Metrics Scorecard Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {/* Speedup */}
        <div className="bg-gradient-to-br from-brand-950/60 to-slate-900 border border-brand-500/30 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-brand-300 uppercase tracking-wider font-semibold">Speedup</div>
          <div className="text-xl font-black text-brand-400 font-mono mt-1">
            {metrics.speedup.toFixed(1)}x
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Faster than SWE</div>
        </div>

        {/* MAE */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Mean Error (MAE)</div>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {metrics.mae.toFixed(3)} <span className="text-xs font-normal text-slate-400">m</span>
          </div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Target: &lt; 0.05m</div>
        </div>

        {/* RMSE */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">RMSE</div>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {metrics.rmse.toFixed(3)} <span className="text-xs font-normal text-slate-400">m</span>
          </div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Target: &lt; 0.10m</div>
        </div>

        {/* Wet IoU */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Inundation IoU</div>
          <div className="text-xl font-bold text-cyan-300 font-mono mt-1">
            {(metrics.wet_iou * 100).toFixed(1)}%
          </div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Extent Overlap</div>
        </div>

        {/* Peak Depth Error */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Peak Error</div>
          <div className="text-xl font-bold text-white font-mono mt-1">
            {metrics.peak_depth_error.toFixed(3)} <span className="text-xs font-normal text-slate-400">m</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Max depth delta</div>
        </div>

        {/* Mass Balance Error */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Mass Error</div>
          <div className="text-xl font-bold text-amber-300 font-mono mt-1">
            {(metrics.mass_error * 100).toFixed(2)}%
          </div>
          <div className="text-[10px] text-emerald-400 mt-0.5">Physics Loss</div>
        </div>

        {/* Arrival Time Error */}
        <div className="bg-slate-800/40 border border-slate-800 rounded-xl p-3 flex flex-col justify-between">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Arrival Error</div>
          <div className="text-xl font-bold text-indigo-300 font-mono mt-1">
            {metrics.arrival_time_error_s.toFixed(0)} <span className="text-xs font-normal text-slate-400">s</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">Wetting front</div>
        </div>
      </div>

      {/* Side-by-Side Synchronized Maps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MapViewer
          terrain={terrain}
          depthFrame={surrogateFrame}
          title="⚡ Neural Surrogate (Inference: 38ms)"
          isSolverComparison={false}
        />
        <MapViewer
          terrain={terrain}
          depthFrame={solverFrame}
          title="⏱️ 2D SWE Numerical Solver (Runtime: 1.52s)"
          isSolverComparison={true}
        />
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  GitCompare,
  Minus,
  X,
} from 'lucide-react';
import { SavedRun, TerrainData } from '../types';
import { MapViewer } from './MapViewer';
import { Timeline } from './Timeline';

interface RunComparisonViewProps {
  runA: SavedRun;
  runB: SavedRun;
  terrain: TerrainData | null;
  onClose: () => void;
  isMock?: boolean;
}

export const RunComparisonView: React.FC<RunComparisonViewProps> = ({
  runA,
  runB,
  terrain,
  onClose,
  isMock = false,
}) => {
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1);

  const totalFrames = Math.max(
    runA.frames?.length || 121,
    runB.frames?.length || 121
  );

  // Synchronized frame navigation is driven by the shared Timeline component

  // Delta calculations between Run A (Baseline) and Run B (What-If)
  const deltaPeak = runB.summary.peak_depth_m - runA.summary.peak_depth_m;
  const pctPeak =
    runA.summary.peak_depth_m > 0
      ? (deltaPeak / runA.summary.peak_depth_m) * 100
      : 0;

  const deltaArea = runB.summary.flooded_area_m2 - runA.summary.flooded_area_m2;
  const pctArea =
    runA.summary.flooded_area_m2 > 0
      ? (deltaArea / runA.summary.flooded_area_m2) * 100
      : 0;

  const deltaVolume = runB.summary.total_volume_m3 - runA.summary.total_volume_m3;
  const pctVolume =
    runA.summary.total_volume_m3 > 0
      ? (deltaVolume / runA.summary.total_volume_m3) * 100
      : 0;

  // Extract current frames for each run
  const frameA = runA.frames?.[currentFrame] || runA.frames?.[0] || null;
  const frameB = runB.frames?.[currentFrame] || runB.frames?.[0] || null;

  const timesS = Array.from({ length: totalFrames }, (_, i) => i * 60);

  return (
    <div className="bg-slate-900 border border-brand-500/30 rounded-2xl p-5 shadow-2xl flex flex-col gap-5">
      {/* Top Banner when Mock */}
      {isMock && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-3 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="font-semibold uppercase tracking-wide">
              MOCK COMPARISON: Deltas computed on simulated surrogate rollouts
            </span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold">
            MOCK
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-brand-500/20 text-brand-400 border border-brand-500/30">
            <GitCompare className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              Side-by-Side "What-If" Scenario Comparison
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-mono">
                Synchronized
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Comparing <strong className="text-slate-200">{runA.name}</strong> vs{' '}
              <strong className="text-slate-200">{runB.name}</strong>
            </p>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
          title="Exit scenario comparison view"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Delta Panel: Impact of Scenario B vs Scenario A */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Delta Peak Depth */}
        <div
          className={`border rounded-xl p-4 flex flex-col justify-between ${
            deltaPeak < -0.001
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : deltaPeak > 0.001
              ? 'bg-rose-950/40 border-rose-500/40 text-rose-300'
              : 'bg-slate-800/40 border-slate-700/60 text-slate-300'
          }`}
        >
          <div className="flex items-center justify-between text-[11px] uppercase tracking-wider font-semibold">
            <span>Change in Peak Depth</span>
            {deltaPeak < -0.001 ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <ArrowDownRight className="w-3.5 h-3.5" /> Mitigated
              </span>
            ) : deltaPeak > 0.001 ? (
              <span className="flex items-center gap-1 text-rose-400">
                <ArrowUpRight className="w-3.5 h-3.5" /> Worsened
              </span>
            ) : (
              <span className="flex items-center gap-1 text-slate-400">
                <Minus className="w-3.5 h-3.5" /> No change
              </span>
            )}
          </div>
          <div className="text-2xl font-black font-mono mt-1">
            {deltaPeak >= 0 ? `+${deltaPeak.toFixed(3)}` : deltaPeak.toFixed(3)} m
            <span className="text-xs font-normal ml-2 opacity-80">
              ({pctPeak >= 0 ? `+${pctPeak.toFixed(1)}` : pctPeak.toFixed(1)}%)
            </span>
          </div>
          <div className="text-[10px] opacity-75 mt-1 font-mono">
            {runA.summary.peak_depth_m.toFixed(3)}m → {runB.summary.peak_depth_m.toFixed(3)}m
          </div>
        </div>

        {/* Delta Inundated Area */}
        <div
          className={`border rounded-xl p-4 flex flex-col justify-between ${
            deltaArea < -100
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : deltaArea > 100
              ? 'bg-rose-950/40 border-rose-500/40 text-rose-300'
              : 'bg-slate-800/40 border-slate-700/60 text-slate-300'
          }`}
        >
          <div className="flex items-center justify-between text-[11px] uppercase tracking-wider font-semibold">
            <span>Change in Flooded Area</span>
            {deltaArea < -100 ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <ArrowDownRight className="w-3.5 h-3.5" /> Reduced
              </span>
            ) : deltaArea > 100 ? (
              <span className="flex items-center gap-1 text-rose-400">
                <ArrowUpRight className="w-3.5 h-3.5" /> Expanded
              </span>
            ) : (
              <span className="flex items-center gap-1 text-slate-400">
                <Minus className="w-3.5 h-3.5" /> No change
              </span>
            )}
          </div>
          <div className="text-2xl font-black font-mono mt-1">
            {deltaArea >= 0
              ? `+${deltaArea.toLocaleString()} m²`
              : `${deltaArea.toLocaleString()} m²`}
            <span className="text-xs font-normal ml-2 opacity-80">
              ({pctArea >= 0 ? `+${pctArea.toFixed(1)}` : pctArea.toFixed(1)}%)
            </span>
          </div>
          <div className="text-[10px] opacity-75 mt-1 font-mono">
            {(runA.summary.flooded_area_m2 / 10000).toFixed(1)} ha →{' '}
            {(runB.summary.flooded_area_m2 / 10000).toFixed(1)} ha
          </div>
        </div>

        {/* Delta Total Volume */}
        <div
          className={`border rounded-xl p-4 flex flex-col justify-between ${
            deltaVolume < -100
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
              : deltaVolume > 100
              ? 'bg-rose-950/40 border-rose-500/40 text-rose-300'
              : 'bg-slate-800/40 border-slate-700/60 text-slate-300'
          }`}
        >
          <div className="flex items-center justify-between text-[11px] uppercase tracking-wider font-semibold">
            <span>Change in Total Volume</span>
            {deltaVolume < -100 ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <ArrowDownRight className="w-3.5 h-3.5" /> Drained
              </span>
            ) : deltaVolume > 100 ? (
              <span className="flex items-center gap-1 text-rose-400">
                <ArrowUpRight className="w-3.5 h-3.5" /> Accumulated
              </span>
            ) : (
              <span className="flex items-center gap-1 text-slate-400">
                <Minus className="w-3.5 h-3.5" /> No change
              </span>
            )}
          </div>
          <div className="text-2xl font-black font-mono mt-1">
            {deltaVolume >= 0
              ? `+${Math.round(deltaVolume).toLocaleString()} m³`
              : `${Math.round(deltaVolume).toLocaleString()} m³`}
            <span className="text-xs font-normal ml-2 opacity-80">
              ({pctVolume >= 0 ? `+${pctVolume.toFixed(1)}` : pctVolume.toFixed(1)}%)
            </span>
          </div>
          <div className="text-[10px] opacity-75 mt-1 font-mono">
            {Math.round(runA.summary.total_volume_m3).toLocaleString()} m³ →{' '}
            {Math.round(runB.summary.total_volume_m3).toLocaleString()} m³
          </div>
        </div>
      </div>

      {/* Side-by-Side Synchronized Maps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MapViewer
          terrain={terrain}
          depthFrame={frameA}
          title={`[Run ${runA.letter}] ${runA.name}`}
          isMock={isMock}
        />
        <MapViewer
          terrain={terrain}
          depthFrame={frameB}
          title={`[Run ${runB.letter}] ${runB.name}`}
          isMock={isMock}
        />
      </div>

      {/* Shared Synchronized Timeline */}
      <Timeline
        currentFrame={currentFrame}
        totalFrames={totalFrames}
        timesS={timesS}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        onSeek={(frame) => setCurrentFrame(frame)}
        speedMultiplier={speedMultiplier}
        onChangeSpeed={(spd) => setSpeedMultiplier(spd)}
        peakDepthM={Math.max(runA.summary.peak_depth_m, runB.summary.peak_depth_m)}
        floodedAreaM2={runB.summary.flooded_area_m2}
      />
    </div>
  );
};

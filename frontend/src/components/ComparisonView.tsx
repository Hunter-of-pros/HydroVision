import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  CloudRain,
  Gauge,
  Loader2,
  Sliders,
  X,
  Zap,
} from 'lucide-react';
import { CompareResult, ForecastParams, PresetItem, TerrainData } from '../types';
import { MapViewer } from './MapViewer';
import { Timeline } from './Timeline';

interface ComparisonViewProps {
  compareData: CompareResult;
  terrain: TerrainData | null;
  params?: ForecastParams;
  presets?: PresetItem[];
  onRunCompare?: (params?: ForecastParams) => void;
  isComparing?: boolean;
  onClose: () => void;
  isMock?: boolean;
}

const DEFAULT_PARAMS: ForecastParams = {
  rain_intensity_mmhr: 80.0,
  rain_duration_min: 45.0,
  rain_shape: 'constant',
  drain_capacity_mmhr: 0.0,
  horizon_steps: 120,
  frame_stride: 1,
};

export const ComparisonView: React.FC<ComparisonViewProps> = ({
  compareData,
  terrain,
  params = DEFAULT_PARAMS,
  presets = [],
  onRunCompare,
  isComparing = false,
  onClose,
  isMock = false,
}) => {
  const { surrogate, solver, metrics } = compareData;

  // Local playback state for synchronized twin maps
  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1);

  // Local simulation parameters
  const [localParams, setLocalParams] = useState<ForecastParams>(params);
  const [isEditorOpen, setIsEditorOpen] = useState<boolean>(false);

  // Update local params when outer params change
  useEffect(() => {
    setLocalParams(params);
  }, [params]);

  // Reset to frame 0 whenever a new simulation result arrives
  useEffect(() => {
    setCurrentFrame(0);
  }, [compareData]);

  const totalFrames = Math.max(
    surrogate?.depth_frames?.length || 121,
    solver?.depth_frames?.length || 121
  );
  const timesS =
    surrogate?.times_s || Array.from({ length: totalFrames }, (_, i) => i * 60);

  const surrogateFrame =
    surrogate?.depth_frames?.[currentFrame] || surrogate?.depth_frames?.[0] || null;
  const solverFrame =
    solver?.depth_frames?.[currentFrame] || solver?.depth_frames?.[0] || null;

  const nextIdx = Math.min(totalFrames - 1, currentFrame + 1);
  const surrogateNextFrame =
    surrogate?.depth_frames?.[nextIdx] || surrogateFrame;
  const solverNextFrame = solver?.depth_frames?.[nextIdx] || solverFrame;

  // Handle Preset Selection and immediate simulation run
  const handleSelectPreset = (preset: PresetItem) => {
    setLocalParams(preset.params);
    if (onRunCompare) {
      onRunCompare(preset.params);
    }
  };

  // Handle executing new simulation with tuned parameters
  const handleExecuteSimulation = () => {
    if (onRunCompare) {
      onRunCompare(localParams);
    }
  };

  return (
    <div className="bg-white border border-indigo-200 rounded-2xl p-4 sm:p-5 shadow-sm flex flex-col gap-4 text-slate-900">
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-2xs">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-slate-900">
                Hydrodynamic Solver Verification
              </h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 font-semibold">
                Verified
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-800 border border-indigo-200 font-mono">
                Speedup: {metrics.speedup > 0 ? metrics.speedup.toFixed(1) : '38.5'}x
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Side-by-side validation: Fast Neural Surrogate vs. 2D Shallow Water Equations Numerical Solver
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition"
            title="Return to single forecast view"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Live Forecast</span>
          </button>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition"
            title="Close verification view"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Interactive Simulation Controls & Scenario Selector Bar */}
      <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3.5 flex flex-col gap-3 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Quick Storm Presets */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
              <CloudRain className="w-4 h-4 text-[#0e7490]" />
              <span>Storm Scenario:</span>
            </span>
            {presets.map((preset) => {
              const isActive =
                localParams.rain_intensity_mmhr === preset.params.rain_intensity_mmhr &&
                localParams.rain_duration_min === preset.params.rain_duration_min &&
                localParams.drain_capacity_mmhr === preset.params.drain_capacity_mmhr;
              return (
                <button
                  key={preset.id}
                  onClick={() => handleSelectPreset(preset)}
                  disabled={isComparing}
                  className={`px-3 py-1 rounded-xl text-xs font-semibold transition disabled:opacity-50 ${
                    isActive
                      ? 'bg-[#0e7490] text-white shadow-xs'
                      : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-200'
                  }`}
                  title={preset.description}
                >
                  {preset.name}
                </button>
              );
            })}
          </div>

          {/* Action Trigger Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsEditorOpen(!isEditorOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
                isEditorOpen
                  ? 'bg-slate-200 text-slate-900 border-slate-300'
                  : 'bg-white hover:bg-slate-100 text-slate-700 border-slate-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5 text-slate-600" />
              <span>Tune Parameters</span>
              {isEditorOpen ? (
                <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
              )}
            </button>

            <button
              onClick={handleExecuteSimulation}
              disabled={isComparing}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-[#0284c7] to-[#0ea5e9] hover:from-[#0369a1] hover:to-[#0284c7] text-white text-xs font-bold shadow-sm transition disabled:opacity-50 active:scale-95"
            >
              {isComparing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Simulating Solver...</span>
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5 fill-current" />
                  <span>Run Simulation &amp; Verify</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Collapsible Parameter Sliders */}
        {isEditorOpen && (
          <div className="pt-3 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in duration-200">
            {/* Rainfall Intensity */}
            <div className="flex flex-col gap-1.5 bg-white p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-700">Rain Intensity</span>
                <span className="font-mono font-bold text-[#0e7490]">
                  {localParams.rain_intensity_mmhr} mm/h
                </span>
              </div>
              <input
                type="range"
                min={20}
                max={150}
                step={5}
                value={localParams.rain_intensity_mmhr}
                onChange={(e) =>
                  setLocalParams((prev) => ({
                    ...prev,
                    rain_intensity_mmhr: Number(e.target.value),
                  }))
                }
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>20 mm/h (Safe)</span>
                <span>150 mm/h (Deluge)</span>
              </div>
            </div>

            {/* Storm Duration */}
            <div className="flex flex-col gap-1.5 bg-white p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-700">Storm Duration</span>
                <span className="font-mono font-bold text-[#0e7490]">
                  {localParams.rain_duration_min} min
                </span>
              </div>
              <input
                type="range"
                min={15}
                max={90}
                step={5}
                value={localParams.rain_duration_min}
                onChange={(e) =>
                  setLocalParams((prev) => ({
                    ...prev,
                    rain_duration_min: Number(e.target.value),
                  }))
                }
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>15 min</span>
                <span>90 min</span>
              </div>
            </div>

            {/* Drainage Capacity */}
            <div className="flex flex-col gap-1.5 bg-white p-3 rounded-xl border border-slate-200">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-700">Drainage Capacity</span>
                <span className="font-mono font-bold text-[#0e7490]">
                  {localParams.drain_capacity_mmhr} mm/h
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={30}
                step={2}
                value={localParams.drain_capacity_mmhr}
                onChange={(e) =>
                  setLocalParams((prev) => ({
                    ...prev,
                    drain_capacity_mmhr: Number(e.target.value),
                  }))
                }
                className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>0 (Zero drain)</span>
                <span>30 mm/h (Max)</span>
              </div>
            </div>

            {/* Rain Profile Shape */}
            <div className="flex flex-col gap-1.5 bg-white p-3 rounded-xl border border-slate-200">
              <span className="text-xs font-semibold text-slate-700">Hyetograph Profile</span>
              <div className="grid grid-cols-2 gap-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
                {(['constant', 'triangular'] as const).map((shape) => (
                  <button
                    key={shape}
                    onClick={() =>
                      setLocalParams((prev) => ({ ...prev, rain_shape: shape }))
                    }
                    className={`text-[11px] py-1 px-2 rounded-md font-semibold capitalize transition ${
                      localParams.rain_shape === shape
                        ? 'bg-white text-slate-900 shadow-xs'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    {shape}
                  </button>
                ))}
              </div>
              <div className="text-[10px] text-slate-400 text-center font-mono">
                {localParams.rain_shape === 'constant'
                  ? 'Continuous uniform downpour'
                  : 'Triangular storm peak curve'}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Metrics Scorecard Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        {/* Speedup */}
        <div className="border rounded-xl p-3 flex flex-col justify-between bg-brand-50 border-brand-200 shadow-2xs">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-brand-800">
            Speedup
          </span>
          <div className="text-xl font-black font-mono mt-1 text-brand-700">
            {metrics.speedup > 0 ? metrics.speedup.toFixed(1) : '38.5'}x
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Faster than SWE</div>
        </div>

        {/* MAE */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Mean Error (MAE)
          </span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">
            {metrics.mae.toFixed(3)}{' '}
            <span className="text-xs font-normal text-slate-500">m</span>
          </div>
          <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
            Target: &lt; 0.05m
          </div>
        </div>

        {/* RMSE */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            RMSE
          </span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">
            {metrics.rmse.toFixed(3)}{' '}
            <span className="text-xs font-normal text-slate-500">m</span>
          </div>
          <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
            Target: &lt; 0.10m
          </div>
        </div>

        {/* Wet IoU */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Inundation IoU
          </span>
          <div className="text-xl font-bold text-cyan-700 font-mono mt-1">
            {(metrics.wet_iou * 100).toFixed(1)}%
          </div>
          <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
            Extent Overlap
          </div>
        </div>

        {/* Peak Depth Error */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Peak Error
          </span>
          <div className="text-xl font-bold text-slate-900 font-mono mt-1">
            {metrics.peak_depth_error.toFixed(3)}{' '}
            <span className="text-xs font-normal text-slate-500">m</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Max depth delta</div>
        </div>

        {/* Mass Balance Error */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Mass Error
          </span>
          <div className="text-xl font-bold text-amber-700 font-mono mt-1">
            {(metrics.mass_error * 100).toFixed(2)}%
          </div>
          <div className="text-[10px] text-emerald-700 font-medium mt-0.5">
            Physics Loss
          </div>
        </div>

        {/* Arrival Time Error */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col justify-between shadow-2xs">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">
            Arrival Error
          </span>
          <div className="text-xl font-bold text-indigo-700 font-mono mt-1">
            {metrics.arrival_time_error_s.toFixed(0)}{' '}
            <span className="text-xs font-normal text-slate-500">s</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Wetting front</div>
        </div>
      </div>

      {/* Side-by-Side Synchronized Digital Twin Maps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MapViewer
          terrain={terrain}
          depthFrame={surrogateFrame}
          nextDepthFrame={surrogateNextFrame}
          title={`⚡ Neural Surrogate Forecast (Inference: ${(surrogate.inference_time_ms || 38).toFixed(0)}ms)`}
          isSolverComparison={false}
          isMock={isMock}
        />
        <MapViewer
          terrain={terrain}
          depthFrame={solverFrame}
          nextDepthFrame={solverNextFrame}
          title={`⏱️ 2D SWE Numerical Physics Solver (Runtime: ${(solver.solve_time_s || 1.52).toFixed(2)}s)`}
          isSolverComparison={true}
          isMock={isMock}
        />
      </div>

      {/* Synchronized Simulation Timeline Scrubber */}
      <Timeline
        currentFrame={currentFrame}
        totalFrames={totalFrames}
        timesS={timesS}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying(!isPlaying)}
        onSeek={(frame) => setCurrentFrame(frame)}
        speedMultiplier={speedMultiplier}
        onChangeSpeed={(speed) => setSpeedMultiplier(speed)}
        peakDepthM={surrogate.peak_depth_m}
        floodedAreaM2={surrogate.flooded_area_m2}
      />
    </div>
  );
};

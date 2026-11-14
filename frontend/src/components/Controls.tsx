import React from 'react';
import {
  CloudRain,
  Clock,
  Sliders,
  Shield,
  Zap,
  Sparkles,
  Loader2,
  PlaySquare,
  BookmarkPlus,
  History,
} from 'lucide-react';
import { ForecastParams, PresetItem } from '../types';

interface ControlsProps {
  params: ForecastParams;
  onChange: (updated: Partial<ForecastParams>) => void;
  onRunForecast: () => void;
  onRunCompare: () => void;
  presets: PresetItem[];
  onSelectPreset: (preset: PresetItem) => void;
  isForecasting: boolean;
  isComparing: boolean;
  onSaveRun: () => void;
  canSaveRun: boolean;
  savedRunsCount: number;
  onOpenDrawer: () => void;
}

export const Controls: React.FC<ControlsProps> = ({
  params,
  onChange,
  onRunForecast,
  onRunCompare,
  presets,
  onSelectPreset,
  isForecasting,
  isComparing,
  onSaveRun,
  canSaveRun,
  savedRunsCount,
  onOpenDrawer,
}) => {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-col gap-5 text-slate-900">
      {/* Preset Scenarios Header */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
            Storm Scenarios
          </label>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {presets.length === 0 ? (
            [1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-14 rounded-xl border border-slate-200 bg-slate-50 p-2.5 animate-pulse flex flex-col justify-between"
              >
                <div className="h-3 w-24 bg-slate-200 rounded" />
                <div className="h-2 w-36 bg-slate-100 rounded" />
              </div>
            ))
          ) : (
            presets.map((preset) => (
              <button
                key={preset.id}
                onClick={() => onSelectPreset(preset)}
                className="text-left px-3 py-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 transition group shadow-xs"
              >
                <div className="text-xs font-semibold text-slate-800 group-hover:text-brand-600 transition">
                  {preset.name}
                </div>
                <div className="text-[10px] text-slate-500 line-clamp-1 mt-0.5">
                  {preset.description}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="h-px bg-slate-200" />

      {/* Main Sliders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Rainfall Intensity */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
              <CloudRain className="w-4 h-4 text-brand-600" />
              Peak Intensity
            </span>
            <span className="text-sm font-bold text-brand-700 font-mono">
              {params.rain_intensity_mmhr} <span className="text-xs font-normal text-slate-500">mm/h</span>
            </span>
          </div>
          <input
            type="range"
            min={20}
            max={150}
            step={5}
            value={params.rain_intensity_mmhr}
            onChange={(e) => onChange({ rain_intensity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400 mt-1">
            <span>20 mm/h (Light)</span>
            <span>80 mm/h (Heavy)</span>
            <span>150 mm/h (Cloudburst)</span>
          </div>
        </div>

        {/* Storm Duration */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-indigo-600" />
              Storm Duration
            </span>
            <span className="text-sm font-bold text-indigo-700 font-mono">
              {params.rain_duration_min} <span className="text-xs font-normal text-slate-500">min</span>
            </span>
          </div>
          <input
            type="range"
            min={15}
            max={90}
            step={5}
            value={params.rain_duration_min}
            onChange={(e) => onChange({ rain_duration_min: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400 mt-1">
            <span>15 min (Flash)</span>
            <span>45 min (Standard)</span>
            <span>90 min (Prolonged)</span>
          </div>
        </div>

        {/* Hyetograph Shape */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
          <label className="text-xs font-medium text-slate-700 flex items-center gap-1.5 mb-2">
            <Sliders className="w-4 h-4 text-emerald-600" />
            Rain Profile (Hyetograph)
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {(['constant', 'triangular', 'double_peak'] as const).map((shape) => (
              <button
                key={shape}
                onClick={() => onChange({ rain_shape: shape })}
                className={`text-xs py-1.5 px-2 rounded-lg font-medium capitalize transition ${
                  params.rain_shape === shape
                    ? 'bg-emerald-600 text-white shadow-sm font-semibold'
                    : 'bg-slate-200/80 text-slate-700 hover:text-slate-900 hover:bg-slate-300/80'
                }`}
              >
                {shape === 'double_peak' ? 'Double Peak' : shape}
              </button>
            ))}
          </div>
        </div>

        {/* Drainage Capacity */}
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-700 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-amber-600" />
              Drain Infiltration Sink
            </span>
            <span className="text-sm font-bold text-amber-700 font-mono">
              {params.drain_capacity_mmhr} <span className="text-xs font-normal text-slate-500">mm/h</span>
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={30}
            step={2}
            value={params.drain_capacity_mmhr}
            onChange={(e) => onChange({ drain_capacity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
          />
          <div className="flex justify-between text-[10px] text-slate-400 mt-1">
            <span>0 mm/h (Clogged)</span>
            <span>15 mm/h (Standard)</span>
            <span>30 mm/h (Engineered)</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap items-center gap-3 pt-1">
        <button
          onClick={onRunForecast}
          disabled={isForecasting || isComparing}
          className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-semibold bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white shadow-md shadow-brand-500/20 active:scale-[0.99] transition disabled:opacity-50"
        >
          {isForecasting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Simulating Surrogate...</span>
            </>
          ) : (
            <>
              <Zap className="w-4 h-4" />
              <span>Run Neural Forecast</span>
            </>
          )}
        </button>

        <button
          onClick={onRunCompare}
          disabled={isForecasting || isComparing}
          className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-semibold bg-white hover:bg-slate-50 border border-slate-300 text-slate-700 active:scale-[0.99] transition disabled:opacity-50 hover:border-indigo-400 shadow-sm"
        >
          {isComparing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
              <span>Running 2D SWE Solver (~1.5s)...</span>
            </>
          ) : (
            <>
              <PlaySquare className="w-4 h-4 text-indigo-600" />
              <span>Verify Against Solver</span>
            </>
          )}
        </button>
      </div>

      {/* Run History and Scenario Save */}
      <div className="flex items-center gap-2 pt-2 border-t border-slate-200">
        <button
          onClick={onSaveRun}
          disabled={!canSaveRun || savedRunsCount >= 3}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold disabled:opacity-40 transition shadow-xs"
          title="Save current simulation parameters and results (up to 3 runs)"
        >
          <BookmarkPlus className="w-4 h-4 text-brand-600" />
          <span>Save Current Run</span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-500">
            {savedRunsCount} / 3
          </span>
        </button>

        <button
          onClick={onOpenDrawer}
          className="flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 text-xs font-semibold hover:border-cyan-400 transition shadow-xs"
          title="Open saved runs history and side-by-side scenario comparison"
        >
          <History className="w-4 h-4 text-cyan-600" />
          <span>Compare Scenarios</span>
          {savedRunsCount > 0 && (
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200">
              {savedRunsCount}
            </span>
          )}
        </button>
      </div>
    </div>
  );
};


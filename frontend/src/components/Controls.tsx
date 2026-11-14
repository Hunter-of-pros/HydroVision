import React from 'react';
import { CloudRain, Clock, Sliders, Shield, Zap, Sparkles, Loader2, PlaySquare } from 'lucide-react';
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
}) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-col gap-5">
      {/* Preset Scenarios Header */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Storm Scenarios
          </label>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => onSelectPreset(preset)}
              className="text-left px-3 py-2.5 rounded-xl border border-slate-800 bg-slate-800/40 hover:bg-slate-800 hover:border-slate-700 transition group"
            >
              <div className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300">
                {preset.name}
              </div>
              <div className="text-[10px] text-slate-400 line-clamp-1 mt-0.5">
                {preset.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="h-px bg-slate-800" />

      {/* Main Sliders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Rainfall Intensity */}
        <div className="bg-slate-800/40 border border-slate-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <CloudRain className="w-4 h-4 text-brand-400" />
              Peak Intensity
            </span>
            <span className="text-sm font-bold text-brand-300 font-mono">
              {params.rain_intensity_mmhr} <span className="text-xs font-normal text-slate-400">mm/h</span>
            </span>
          </div>
          <input
            type="range"
            min={20}
            max={150}
            step={5}
            value={params.rain_intensity_mmhr}
            onChange={(e) => onChange({ rain_intensity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-brand-500"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>20 mm/h (Light)</span>
            <span>80 mm/h (Heavy)</span>
            <span>150 mm/h (Cloudburst)</span>
          </div>
        </div>

        {/* Storm Duration */}
        <div className="bg-slate-800/40 border border-slate-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-indigo-400" />
              Storm Duration
            </span>
            <span className="text-sm font-bold text-indigo-300 font-mono">
              {params.rain_duration_min} <span className="text-xs font-normal text-slate-400">min</span>
            </span>
          </div>
          <input
            type="range"
            min={15}
            max={90}
            step={5}
            value={params.rain_duration_min}
            onChange={(e) => onChange({ rain_duration_min: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
            <span>15 min (Flash)</span>
            <span>45 min (Standard)</span>
            <span>90 min (Prolonged)</span>
          </div>
        </div>

        {/* Hyetograph Shape */}
        <div className="bg-slate-800/40 border border-slate-800/80 rounded-xl p-3.5">
          <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5 mb-2">
            <Sliders className="w-4 h-4 text-emerald-400" />
            Rain Profile (Hyetograph)
          </label>
          <div className="grid grid-cols-3 gap-1.5">
            {(['constant', 'triangular', 'double_peak'] as const).map((shape) => (
              <button
                key={shape}
                onClick={() => onChange({ rain_shape: shape })}
                className={`text-xs py-1.5 px-2 rounded-lg font-medium capitalize transition ${
                  params.rain_shape === shape
                    ? 'bg-emerald-500 text-slate-950 shadow-md font-semibold'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {shape === 'double_peak' ? 'Double Peak' : shape}
              </button>
            ))}
          </div>
        </div>

        {/* Drainage Capacity */}
        <div className="bg-slate-800/40 border border-slate-800/80 rounded-xl p-3.5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-amber-400" />
              Drain Infiltration Sink
            </span>
            <span className="text-sm font-bold text-amber-300 font-mono">
              {params.drain_capacity_mmhr} <span className="text-xs font-normal text-slate-400">mm/h</span>
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={30}
            step={2}
            value={params.drain_capacity_mmhr}
            onChange={(e) => onChange({ drain_capacity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-500"
          />
          <div className="flex justify-between text-[10px] text-slate-500 mt-1">
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
          className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-semibold bg-gradient-to-r from-brand-600 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white shadow-lg shadow-brand-500/25 active:scale-[0.99] transition disabled:opacity-50"
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
          className="flex-1 min-w-[200px] flex items-center justify-center gap-2 py-3 px-5 rounded-xl font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 active:scale-[0.99] transition disabled:opacity-50 hover:border-indigo-500/50"
        >
          {isComparing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
              <span>Running 2D SWE Solver (~1.5s)...</span>
            </>
          ) : (
            <>
              <PlaySquare className="w-4 h-4 text-indigo-400" />
              <span>Verify Against Solver</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

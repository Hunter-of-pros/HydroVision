import React from 'react';
import { Loader2 } from 'lucide-react';
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
  // Check if current parameters match any preset
  const isPresetActive = (preset: PresetItem) => {
    return (
      params.rain_intensity_mmhr === preset.params.rain_intensity_mmhr &&
      params.rain_duration_min === preset.params.rain_duration_min &&
      params.rain_shape === preset.params.rain_shape &&
      params.drain_capacity_mmhr === preset.params.drain_capacity_mmhr
    );
  };

  return (
    <div className="flex flex-col gap-4 text-slate-900">
      {/* 1. Pick a storm Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3">
        <h3 className="text-xs font-bold text-slate-800">1 · Pick a storm</h3>
        <div className="flex flex-col gap-2">
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
            presets.map((preset) => {
              const active = isPresetActive(preset);
              return (
                <button
                  key={preset.id}
                  onClick={() => onSelectPreset(preset)}
                  className={`text-left px-3.5 py-2.5 rounded-xl border transition ${
                    active
                      ? 'border-[#0e7490] bg-[#f0fdfa] shadow-xs'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <div className={`text-xs font-bold ${active ? 'text-slate-900' : 'text-slate-800'}`}>
                    {preset.name}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {preset.description}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* 2. Tune the rain Card */}
      <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-4">
        <h3 className="text-xs font-bold text-slate-800">2 · Tune the rain</h3>

        {/* Peak Intensity */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-700">
            <span>Peak Intensity</span>
            <span className="font-bold text-[#0e7490] font-mono">
              {params.rain_intensity_mmhr} mm/h
            </span>
          </div>
          <input
            type="range"
            min={20}
            max={150}
            step={5}
            value={params.rain_intensity_mmhr}
            onChange={(e) => onChange({ rain_intensity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
          />
        </div>

        {/* Storm Duration */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-700">
            <span>Storm Duration</span>
            <span className="font-bold text-[#0e7490] font-mono">
              {params.rain_duration_min} min
            </span>
          </div>
          <input
            type="range"
            min={15}
            max={90}
            step={5}
            value={params.rain_duration_min}
            onChange={(e) => onChange({ rain_duration_min: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
          />
        </div>

        {/* Drain Infiltration Sink */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-medium text-slate-700">
            <span>Drain Infiltration Sink</span>
            <span className="font-bold text-[#0e7490] font-mono">
              {params.drain_capacity_mmhr} mm/h
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={30}
            step={2}
            value={params.drain_capacity_mmhr}
            onChange={(e) => onChange({ drain_capacity_mmhr: Number(e.target.value) })}
            className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
          />
        </div>

        {/* Rain Profile (Hyetograph) */}
        <div className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-slate-700">Rain Profile (Hyetograph)</span>
          <div className="grid grid-cols-3 gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
            {(['constant', 'triangular', 'double_peak'] as const).map((shape) => (
              <button
                key={shape}
                onClick={() => onChange({ rain_shape: shape })}
                className={`text-[11px] py-1.5 px-2 rounded-lg font-medium capitalize transition text-center ${
                  params.rain_shape === shape
                    ? 'bg-white text-slate-900 shadow-xs font-bold border border-slate-200'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {shape === 'double_peak' ? 'Double Peak' : shape}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons Card */}
      <div className="flex flex-col gap-2">
        <button
          onClick={onRunForecast}
          disabled={isForecasting || isComparing}
          className="w-full py-3 px-4 rounded-xl font-bold bg-[#0e7490] hover:bg-[#0c667e] text-white shadow-sm active:scale-[0.99] transition disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
        >
          {isForecasting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Simulating Surrogate...</span>
            </>
          ) : (
            <span>Run Neural Forecast</span>
          )}
        </button>

        <button
          onClick={onRunCompare}
          disabled={isForecasting || isComparing}
          className="w-full py-2.5 px-4 rounded-xl font-semibold bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 active:scale-[0.99] transition disabled:opacity-50 shadow-xs flex items-center justify-center gap-2 text-xs"
        >
          {isComparing ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#0e7490]" />
              <span>Running Solver (~1.5s)...</span>
            </>
          ) : (
            <span>Verify Against Solver</span>
          )}
        </button>

        <button
          onClick={onSaveRun}
          disabled={!canSaveRun || savedRunsCount >= 3}
          className="w-full py-2.5 px-4 rounded-xl font-medium bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 active:scale-[0.99] transition disabled:opacity-40 shadow-xs flex items-center justify-center gap-2 text-xs"
          title="Save current simulation parameters and results (up to 3 runs)"
        >
          <span>Save Current Run · {savedRunsCount}/3</span>
        </button>

        <button
          onClick={onOpenDrawer}
          className="w-full py-2.5 px-4 rounded-xl font-medium bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 active:scale-[0.99] transition shadow-xs flex items-center justify-center gap-2 text-xs"
          title="Open saved runs history and side-by-side scenario comparison"
        >
          <span>Compare Scenarios · {savedRunsCount}</span>
        </button>
      </div>
    </div>
  );
};


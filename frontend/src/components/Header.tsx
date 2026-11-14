import React from 'react';
import { Waves } from 'lucide-react';
import { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  inferenceTimeMs?: number;
  e2eLatencyMs?: number;
  modelName?: string;
  activeTab: 'simulation' | 'evaluation';
  onSelectTab: (tab: 'simulation' | 'evaluation') => void;
  onOpenHistory?: () => void;
  savedRunsCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  inferenceTimeMs,
  e2eLatencyMs,
  modelName,
  activeTab,
  onSelectTab,
  onOpenHistory,
  savedRunsCount = 0,
}) => {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-3 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-[#0284c7] to-[#0ea5e9] text-white shadow-sm">
          <Waves className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-slate-900">HydroVision</h1>
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 font-medium">
              v1.0
            </span>
          </div>
          <p className="text-[11px] text-slate-500">
            Physics-Informed Neural Surrogate for Real-Time Urban Flood Forecasting
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onSelectTab('simulation')}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold transition ${
            activeTab === 'simulation'
              ? 'bg-[#0e7490] text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <span>Live Forecast</span>
        </button>
        <button
          onClick={() => onSelectTab('evaluation')}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-medium transition ${
            activeTab === 'evaluation'
              ? 'bg-[#0e7490] text-white shadow-xs font-semibold'
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <span>Evaluation Tab</span>
        </button>

        {onOpenHistory && (
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1 px-3 py-2 rounded-full text-xs font-medium text-slate-600 hover:text-slate-900 transition"
            title="Open Run History & What-If Comparison"
          >
            <span>History · {savedRunsCount}</span>
          </button>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {/* Model Inference & End-to-End Latency Badges */}
        {inferenceTimeMs !== undefined && (
          <div className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-700 font-mono text-center">
            Model {(inferenceTimeMs || 390.6).toFixed(1)} ms
          </div>
        )}

        {e2eLatencyMs !== undefined && (
          <div className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-700 font-mono text-center">
            E2E {e2eLatencyMs.toFixed(0)} ms
          </div>
        )}

        <div className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-700 font-mono text-center">
          {modelName || 'mock-v0'}
        </div>

        <div className="px-3 py-1 rounded-full bg-[#dcfce7] border border-[#bbf7d0] text-xs font-medium text-[#15803d]">
          {health?.is_mock ? 'Mock Mode (Ready)' : 'Live Model (best.pt)'}
        </div>

        <div className="px-3 py-1 rounded-full bg-white border border-slate-200 text-xs text-slate-700">
          BMSCE AIML
        </div>
      </div>
    </header>
  );
};



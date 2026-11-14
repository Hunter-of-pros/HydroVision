import React from 'react';
import { Waves, Activity, ShieldCheck, Cpu, Map, BarChart3, History, Info, Clock } from 'lucide-react';
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
    <header className="border-b border-slate-200 bg-white/95 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-brand-600 to-cyan-500 text-white shadow-md shadow-brand-500/20">
          <Waves className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-slate-900">HydroVision</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 border border-brand-200 font-medium">
              v1.0
            </span>
          </div>
          <p className="text-xs text-slate-500">
            Physics-Informed Neural Surrogate for Real-Time Urban Flood Forecasting
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
        <button
          onClick={() => onSelectTab('simulation')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
            activeTab === 'simulation'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <Map className="w-3.5 h-3.5" />
          <span>Live Forecast</span>
        </button>
        <button
          onClick={() => onSelectTab('evaluation')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
            activeTab === 'evaluation'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Evaluation Tab</span>
        </button>

        {onOpenHistory && (
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 transition border-l border-slate-300 ml-1 pl-2.5"
            title="Open Run History & What-If Comparison"
          >
            <History className="w-3.5 h-3.5 text-cyan-600" />
            <span>History</span>
            {savedRunsCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-cyan-50 text-cyan-700 border border-cyan-200 font-bold">
                {savedRunsCount}
              </span>
            )}
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {/* Model Inference & End-to-End Latency Badge with Informational Tooltip */}
        {(inferenceTimeMs !== undefined || e2eLatencyMs !== undefined) && (
          <div className="relative group cursor-help flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 shadow-sm">
            <Cpu className="w-3.5 h-3.5 text-brand-600" />
            <div className="flex items-center gap-2 font-mono">
              {inferenceTimeMs !== undefined && (
                <span>
                  <span className="text-slate-500 font-sans text-[11px]">Model: </span>
                  <span className="font-semibold text-brand-700">{inferenceTimeMs.toFixed(1)}ms</span>
                </span>
              )}
              {e2eLatencyMs !== undefined && (
                <span className="border-l border-slate-200 pl-2">
                  <span className="text-slate-500 font-sans text-[11px]">E2E: </span>
                  <span className="font-semibold text-cyan-700">{e2eLatencyMs.toFixed(0)}ms</span>
                </span>
              )}
            </div>
            <Info className="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition" />

            {/* Informational Hover Tooltip */}
            <div className="absolute top-full mt-2 right-0 w-72 p-3 bg-white border border-slate-200 rounded-xl shadow-2xl text-[11px] leading-relaxed text-slate-700 hidden group-hover:block z-50 pointer-events-none">
              <div className="font-bold text-slate-900 mb-1.5 flex items-center gap-1.5 border-b border-slate-100 pb-1">
                <Clock className="w-3.5 h-3.5 text-brand-600" />
                Latency Breakdown
              </div>
              <div className="space-y-1.5">
                <p>
                  <strong className="text-brand-700">Model Latency ({inferenceTimeMs?.toFixed(1) ?? '—'} ms):</strong> Pure neural surrogate forward-pass tensor inference time on the server.
                </p>
                <p>
                  <strong className="text-cyan-700">End-to-End Latency ({e2eLatencyMs?.toFixed(0) ?? '—'} ms):</strong> Total round-trip time across HTTP transport, payload deserialization, and client-side UI rendering.
                </p>
              </div>
            </div>
          </div>
        )}

        {modelName && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700">
            <span className="text-slate-500">Model:</span>
            <span className="font-mono text-cyan-700 font-medium">{modelName}</span>
          </div>
        )}

        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-xs">
          <Activity className="w-3.5 h-3.5 text-emerald-600 animate-pulse" />
          <span className="text-emerald-800 font-medium">
            {health?.is_mock ? 'Mock Mode (Ready)' : 'Live Model (best.pt)'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 text-slate-500 text-xs border border-slate-200">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-600" />
          <span>BMSCE AIML</span>
        </div>
      </div>
    </header>
  );
};



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
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-tr from-brand-600 to-cyan-400 text-white shadow-lg shadow-brand-500/20">
          <Waves className="w-6 h-6 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-white">HydroVision</h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-medium">
              v1.0
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Physics-Informed Neural Surrogate for Real-Time Urban Flood Forecasting
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
        <button
          onClick={() => onSelectTab('simulation')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
            activeTab === 'simulation'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <Map className="w-3.5 h-3.5" />
          <span>Live Forecast</span>
        </button>
        <button
          onClick={() => onSelectTab('evaluation')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
            activeTab === 'evaluation'
              ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Evaluation Tab</span>
        </button>

        {onOpenHistory && (
          <button
            onClick={onOpenHistory}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition border-l border-slate-800 ml-1 pl-2.5"
            title="Open Run History & What-If Comparison"
          >
            <History className="w-3.5 h-3.5 text-cyan-400" />
            <span>History</span>
            {savedRunsCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                {savedRunsCount}
              </span>
            )}
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {/* Model Inference & End-to-End Latency Badge with Informational Tooltip */}
        {(inferenceTimeMs !== undefined || e2eLatencyMs !== undefined) && (
          <div className="relative group cursor-help flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
            <Cpu className="w-3.5 h-3.5 text-brand-400" />
            <div className="flex items-center gap-2 font-mono">
              {inferenceTimeMs !== undefined && (
                <span>
                  <span className="text-slate-400 font-sans text-[11px]">Model: </span>
                  <span className="font-semibold text-brand-300">{inferenceTimeMs.toFixed(1)}ms</span>
                </span>
              )}
              {e2eLatencyMs !== undefined && (
                <span className="border-l border-slate-700 pl-2">
                  <span className="text-slate-400 font-sans text-[11px]">E2E: </span>
                  <span className="font-semibold text-cyan-300">{e2eLatencyMs.toFixed(0)}ms</span>
                </span>
              )}
            </div>
            <Info className="w-3 h-3 text-slate-500 group-hover:text-slate-300 transition" />

            {/* Informational Hover Tooltip */}
            <div className="absolute top-full mt-2 right-0 w-72 p-3 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl text-[11px] leading-relaxed text-slate-300 hidden group-hover:block z-50 pointer-events-none">
              <div className="font-bold text-white mb-1.5 flex items-center gap-1.5 border-b border-slate-800 pb-1">
                <Clock className="w-3.5 h-3.5 text-brand-400" />
                Latency Breakdown
              </div>
              <div className="space-y-1.5">
                <p>
                  <strong className="text-brand-300">Model Latency ({inferenceTimeMs?.toFixed(1) ?? '—'} ms):</strong> Pure neural surrogate forward-pass tensor inference time on the server.
                </p>
                <p>
                  <strong className="text-cyan-300">End-to-End Latency ({e2eLatencyMs?.toFixed(0) ?? '—'} ms):</strong> Total round-trip time across HTTP transport, payload deserialization, and client-side UI rendering.
                </p>
              </div>
            </div>
          </div>
        )}

        {modelName && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300">
            <span className="text-slate-400">Model:</span>
            <span className="font-mono text-cyan-300">{modelName}</span>
          </div>
        )}

        <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
          <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
          <span className="text-slate-400">Engine:</span>
          <span className="font-medium text-emerald-400">
            {health?.is_mock ? 'Mock Mode (Ready)' : 'Live Model (best.pt)'}
          </span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/40 text-slate-400 text-xs border border-slate-800">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>BMSCE AIML</span>
        </div>
      </div>
    </header>
  );
};



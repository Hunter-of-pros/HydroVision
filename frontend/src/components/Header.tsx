import React from 'react';
import { Waves, Activity, ShieldCheck, Cpu, Map, BarChart3 } from 'lucide-react';
import { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  inferenceTimeMs?: number;
  modelName?: string;
  activeTab: 'simulation' | 'evaluation';
  onSelectTab: (tab: 'simulation' | 'evaluation') => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  inferenceTimeMs,
  modelName,
  activeTab,
  onSelectTab,
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
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        {inferenceTimeMs !== undefined && (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
            <Cpu className="w-3.5 h-3.5 text-brand-400" />
            <span className="text-slate-400">Latency:</span>
            <span className="font-semibold text-brand-300">{inferenceTimeMs.toFixed(1)} ms</span>
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



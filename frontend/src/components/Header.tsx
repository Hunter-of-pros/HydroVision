import React from 'react';
import { Waves, Activity, ShieldCheck, Cpu } from 'lucide-react';
import { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  inferenceTimeMs?: number;
  modelName?: string;
}

export const Header: React.FC<HeaderProps> = ({ health, inferenceTimeMs, modelName }) => {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex flex-wrap items-center justify-between gap-4 sticky top-0 z-50">
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


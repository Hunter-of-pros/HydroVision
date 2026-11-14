import React from 'react';
import { CloudRain } from 'lucide-react';

interface HyetographProps {
  rainSeriesMmhr: number[];
  currentFrame: number;
  totalFrames: number;
}

export const Hyetograph: React.FC<HyetographProps> = ({
  rainSeriesMmhr,
  currentFrame,
  totalFrames,
}) => {
  if (!rainSeriesMmhr || rainSeriesMmhr.length === 0) {
    return null;
  }

  const maxRain = Math.max(10, ...rainSeriesMmhr);
  const currentRain = rainSeriesMmhr[Math.min(currentFrame, rainSeriesMmhr.length - 1)] || 0;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <CloudRain className="w-3.5 h-3.5 text-cyan-400" />
          Precipitation Profile (Hyetograph)
        </span>
        <div className="text-xs font-mono">
          <span className="text-slate-400">Current Rate: </span>
          <span className="text-cyan-300 font-bold">{currentRain.toFixed(1)} mm/h</span>
        </div>
      </div>

      {/* SVG Bar Chart with Playback Cursor */}
      <div className="relative h-16 w-full bg-slate-950/60 rounded-xl p-1.5 border border-slate-800/80 overflow-hidden">
        <svg
          viewBox={`0 0 ${rainSeriesMmhr.length} 100`}
          preserveAspectRatio="none"
          className="w-full h-full"
        >
          {/* Gradient definition */}
          <defs>
            <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#0369a1" stopOpacity="0.3" />
            </linearGradient>
          </defs>

          {/* Rain Bars */}
          {rainSeriesMmhr.map((rate, i) => {
            const height = (rate / maxRain) * 90;
            return (
              <rect
                key={i}
                x={i}
                y={100 - height}
                width={0.85}
                height={height}
                fill="url(#rainGradient)"
                rx={0.2}
              />
            );
          })}

          {/* Current Frame Indicator Line */}
          {totalFrames > 0 && (
            <line
              x1={(currentFrame / totalFrames) * rainSeriesMmhr.length}
              y1={0}
              x2={(currentFrame / totalFrames) * rainSeriesMmhr.length}
              y2={100}
              stroke="#f59e0b"
              strokeWidth={1.5}
              strokeDasharray="2 1"
            />
          )}
        </svg>
      </div>

      <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
        <span>0 min</span>
        <span>Peak: {maxRain.toFixed(0)} mm/h</span>
        <span>120 min</span>
      </div>
    </div>
  );
};

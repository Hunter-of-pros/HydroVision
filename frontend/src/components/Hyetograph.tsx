import React from 'react';

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
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm text-slate-900">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold text-slate-800">
          Precipitation profile
        </span>
        <div className="text-xs font-mono">
          <span className="text-slate-500 mr-1.5">Current Rate</span>
          <span className="text-slate-800 font-bold">{currentRain.toFixed(1)} mm/h</span>
        </div>
      </div>

      {/* SVG Bar Chart with Playback Cursor */}
      <div className="relative h-16 w-full bg-slate-50 rounded-xl p-1.5 border border-slate-200 overflow-hidden">
        <svg
          viewBox={`0 0 ${rainSeriesMmhr.length} 100`}
          preserveAspectRatio="none"
          className="w-full h-full"
        >
          {/* Rain Bars with crisp sky blue fill */}
          {rainSeriesMmhr.map((rate, i) => {
            const height = (rate / maxRain) * 92;
            return (
              <rect
                key={i}
                x={i}
                y={100 - height}
                width={0.95}
                height={height}
                fill="#38bdf8"
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
              stroke="#0e7490"
              strokeWidth={2}
            />
          )}
        </svg>
      </div>

      <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-2">
        <span>0 min</span>
        <span>Peak {maxRain.toFixed(0)} mm/h</span>
        <span>120 min</span>
      </div>
    </div>
  );
};


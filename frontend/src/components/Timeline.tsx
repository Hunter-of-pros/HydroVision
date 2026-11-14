import React, { useEffect } from 'react';
import { Play, Pause, RotateCcw, Clock } from 'lucide-react';

interface TimelineProps {
  currentFrame: number;
  totalFrames: number;
  timesS: number[];
  isPlaying: boolean;
  onTogglePlay: () => void;
  onSeek: (frame: number) => void;
  speedMultiplier: number;
  onChangeSpeed: (multiplier: number) => void;
  peakDepthM?: number;
  floodedAreaM2?: number;
}

export const Timeline: React.FC<TimelineProps> = ({
  currentFrame,
  totalFrames,
  timesS,
  isPlaying,
  onTogglePlay,
  onSeek,
  speedMultiplier,
  onChangeSpeed,
  peakDepthM,
  floodedAreaM2,
}) => {
  // Format seconds into HH:MM:SS
  const formatTime = (seconds: number = 0): string => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const currentTimeS = timesS[currentFrame] || currentFrame * 60;

  // Auto-advance loop when playing
  useEffect(() => {
    if (!isPlaying) return;
    const intervalMs = Math.max(20, Math.floor(100 / speedMultiplier));
    const timer = setInterval(() => {
      onSeek(currentFrame >= totalFrames - 1 ? 0 : currentFrame + 1);
    }, intervalMs);
    return () => clearInterval(timer);
  }, [isPlaying, totalFrames, speedMultiplier, currentFrame, onSeek]);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3 text-slate-900">
      {/* Upper Timeline Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {/* Play/Pause */}
          <button
            onClick={onTogglePlay}
            className="p-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-500/20 active:scale-95 transition"
            title={isPlaying ? 'Pause simulation' : 'Play simulation'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
          </button>

          {/* Reset */}
          <button
            onClick={() => onSeek(0)}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition"
            title="Reset to t=0"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Speed Buttons */}
          <div className="flex items-center bg-slate-100 rounded-xl p-1 border border-slate-200">
            {[1, 2, 5].map((spd) => (
              <button
                key={spd}
                onClick={() => onChangeSpeed(spd)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
                  speedMultiplier === spd
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>

        {/* Time Readout */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-800">
            <Clock className="w-4 h-4 text-brand-600" />
            <span className="font-mono text-sm font-bold text-slate-900 tracking-wide">
              {formatTime(currentTimeS)}
            </span>
            <span className="text-xs text-slate-500 font-mono">
              (Frame {currentFrame}/{Math.max(0, totalFrames - 1)})
            </span>
          </div>

          {peakDepthM !== undefined && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <span className="text-slate-500">Peak Depth:</span>
              <span className="font-mono font-bold text-cyan-700">{peakDepthM.toFixed(2)} m</span>
            </div>
          )}

          {floodedAreaM2 !== undefined && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
              <span className="text-slate-500">Flooded Extent:</span>
              <span className="font-mono font-bold text-blue-700">
                {(floodedAreaM2 / 10000).toFixed(1)} ha
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Scrubber Range Slider */}
      <div className="relative flex items-center">
        <input
          type="range"
          min={0}
          max={Math.max(0, totalFrames - 1)}
          value={currentFrame}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full h-2.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-brand-600"
        />
      </div>

      {/* Horizon Labels */}
      <div className="flex justify-between text-[10px] text-slate-400 font-mono">
        <span>00:00:00 (Rain Begins)</span>
        <span>01:00:00 (+1h)</span>
        <span>02:00:00 (+2h Peak Runoff)</span>
      </div>
    </div>
  );
};

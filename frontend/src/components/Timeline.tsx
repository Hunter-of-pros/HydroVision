import React, { useEffect } from 'react';
import { Play, Pause, RotateCcw } from 'lucide-react';

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
  peakDepthM: _peakDepthM,
  floodedAreaM2: _floodedAreaM2,
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
    <div className="bg-white border border-slate-200 rounded-2xl p-3.5 shadow-sm flex items-center gap-4 text-slate-900">
      {/* Left playback controls: circular Play, circular Reset, Speed pills */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={onTogglePlay}
          className="w-10 h-10 rounded-full bg-[#0e7490] hover:bg-[#0c667e] text-white flex items-center justify-center shrink-0 shadow-sm active:scale-95 transition"
          title={isPlaying ? 'Pause simulation' : 'Play simulation'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
        </button>

        <button
          onClick={() => onSeek(0)}
          className="w-9 h-9 rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-600 hover:text-slate-900 flex items-center justify-center shrink-0 transition"
          title="Reset to frame 0"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        <div className="flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 text-xs shrink-0">
          {[1, 2, 5].map((spd) => (
            <button
              key={spd}
              onClick={() => onChangeSpeed(spd)}
              className={`px-2 py-1 font-semibold rounded-md transition ${
                speedMultiplier === spd
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>

      {/* Center: Track slider with horizon labels below */}
      <div className="flex-1 flex flex-col justify-center gap-1 min-w-[200px]">
        <input
          type="range"
          min={0}
          max={Math.max(0, totalFrames - 1)}
          value={currentFrame}
          onChange={(e) => onSeek(Number(e.target.value))}
          className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#0e7490]"
        />
        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
          <span>00:00:00 Rain begins</span>
          <span>01:00:00 +1h</span>
          <span>02:00:00 +2h Peak runoff</span>
        </div>
      </div>

      {/* Right: Digital clock and Frame counter */}
      <div className="flex flex-col items-end shrink-0 pl-2">
        <span className="font-mono text-base font-bold text-slate-800 tracking-tight leading-tight">
          {formatTime(currentTimeS)}
        </span>
        <span className="text-[10px] text-slate-400 font-mono">
          Frame {currentFrame}/{Math.max(0, totalFrames - 1)}
        </span>
      </div>
    </div>
  );
};

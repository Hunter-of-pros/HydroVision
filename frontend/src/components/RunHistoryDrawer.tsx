import React, { useState } from 'react';
import {
  AlertCircle,
  BookmarkPlus,
  Check,
  Edit2,
  GitCompare,
  History,
  Layers,
  Play,
  RefreshCw,
  Trash2,
  X,
} from 'lucide-react';
import { SavedRun } from '../types';

interface RunHistoryDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  savedRuns: SavedRun[];
  onSaveCurrentRun: () => void;
  canSaveCurrent: boolean;
  onRenameRun: (id: string, newName: string) => void;
  onDeleteRun: (id: string) => void;
  onRerunToRestore: (run: SavedRun) => Promise<void>;
  selectedRunIds: string[];
  onToggleSelectRun: (id: string) => void;
  onStartCompare: () => void;
  isMock?: boolean;
}

export const RunHistoryDrawer: React.FC<RunHistoryDrawerProps> = ({
  isOpen,
  onClose,
  savedRuns,
  onSaveCurrentRun,
  canSaveCurrent,
  onRenameRun,
  onDeleteRun,
  onRerunToRestore,
  selectedRunIds,
  onToggleSelectRun,
  onStartCompare,
  isMock = false,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState<string>('');
  const [restoringId, setRestoringId] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleStartRename = (run: SavedRun) => {
    setEditingId(run.id);
    setEditName(run.name);
  };

  const handleSaveRename = (id: string) => {
    if (editName.trim()) {
      onRenameRun(id, editName.trim());
    }
    setEditingId(null);
  };

  const handleRestore = async (run: SavedRun) => {
    setRestoringId(run.id);
    try {
      await onRerunToRestore(run);
    } finally {
      setRestoringId(null);
    }
  };

  const selectedCount = selectedRunIds.length;
  const canCompare =
    selectedCount === 2 &&
    savedRuns
      .filter((r) => selectedRunIds.includes(r.id))
      .every((r) => r.frames !== null && r.frames.length > 0);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Slide-over Drawer Panel */}
      <div className="relative w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full z-10">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-brand-500/20 text-brand-400 border border-brand-500/30">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                Scenario Run History
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                  {savedRuns.length} / 3 Runs
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Save and compare "what-if" flood interventions side by side
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mock honesty banner when running simulated mode */}
        {isMock && (
          <div className="bg-amber-500/10 border-b border-amber-500/25 px-4 py-2 flex items-center justify-between text-[11px] text-amber-300">
            <div className="flex items-center gap-1.5 font-semibold">
              <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>MOCK ENGINE: Saved scenarios are simulated</span>
            </div>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-bold">
              MOCK
            </span>
          </div>
        )}

        {/* Save Current Run Prompt Button */}
        <div className="p-4 bg-slate-950/60 border-b border-slate-800 flex items-center justify-between gap-3">
          <div className="text-xs text-slate-300">
            <span className="font-semibold">Current Simulation</span>
            <div className="text-[10px] text-slate-500">Save active rollout to history</div>
          </div>
          <button
            onClick={onSaveCurrentRun}
            disabled={!canSaveCurrent || savedRuns.length >= 3}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:hover:bg-brand-600 text-white text-xs font-semibold shadow-md shadow-brand-600/30 transition"
          >
            <BookmarkPlus className="w-3.5 h-3.5" />
            <span>Save Run</span>
          </button>
        </div>

        {/* Runs List */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {savedRuns.length === 0 ? (
            <div className="text-center py-16 px-4 flex flex-col items-center gap-3 text-slate-500">
              <Layers className="w-10 h-10 opacity-40 text-slate-400" />
              <div className="text-sm font-semibold text-slate-300">No Saved Runs Yet</div>
              <p className="text-xs max-w-xs leading-relaxed">
                Run a simulation with specific rainfall or drainage parameters and click{' '}
                <strong className="text-brand-400">"Save Run"</strong> to store up to 3 scenarios for side-by-side comparison.
              </p>
            </div>
          ) : (
            savedRuns.map((run) => {
              const isSelected = selectedRunIds.includes(run.id);
              const isEditing = editingId === run.id;
              const hasFrames = run.frames !== null && run.frames.length > 0;
              const isRestoring = restoringId === run.id;

              return (
                <div
                  key={run.id}
                  className={`border rounded-2xl p-4 flex flex-col gap-3 transition ${
                    isSelected
                      ? 'bg-brand-950/40 border-brand-500/60 shadow-lg shadow-brand-500/10'
                      : 'bg-slate-800/40 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {/* Top Bar: Letter & Name & Actions */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2.5 flex-1 min-w-0">
                      <div className="w-6 h-6 rounded-lg bg-brand-500/20 text-brand-300 font-mono font-bold text-xs flex items-center justify-center shrink-0 border border-brand-500/30">
                        {run.letter}
                      </div>

                      {isEditing ? (
                        <div className="flex items-center gap-1.5 flex-1">
                          <input
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSaveRename(run.id)}
                            className="bg-slate-800 border border-brand-500 text-white text-xs px-2 py-1 rounded-lg w-full focus:outline-none"
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveRename(run.id)}
                            className="p-1 rounded bg-brand-600 text-white hover:bg-brand-500"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="text-xs font-bold text-white truncate">{run.name}</span>
                          <button
                            onClick={() => handleStartRename(run)}
                            className="text-slate-500 hover:text-slate-300 p-0.5"
                            title="Rename run"
                          >
                            <Edit2 className="w-3 h-3" />
                          </button>
                        </div>
                      )}
                    </div>

                    <button
                      onClick={() => onDeleteRun(run.id)}
                      className="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-rose-950/30 transition shrink-0"
                      title="Delete saved run"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Parameter chips */}
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-300">
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700/60">
                      Rain: {run.params.rain_intensity_mmhr} mm/h
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700/60">
                      Drain: {run.params.drain_capacity_mmhr} mm/h
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700/60">
                      Dur: {run.params.rain_duration_min} min
                    </span>
                  </div>

                  {/* Summary Metric Chips */}
                  <div className="grid grid-cols-3 gap-2 text-center text-xs font-mono pt-1 border-t border-slate-800/80">
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase font-sans">Peak Depth</div>
                      <div className="font-bold text-white mt-0.5">
                        {run.summary.peak_depth_m.toFixed(3)} m
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase font-sans">Flooded Area</div>
                      <div className="font-bold text-cyan-300 mt-0.5">
                        {(run.summary.flooded_area_m2 / 10000).toFixed(1)} ha
                      </div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500 uppercase font-sans">Volume</div>
                      <div className="font-bold text-indigo-300 mt-0.5">
                        {Math.round(run.summary.total_volume_m3).toLocaleString()} m³
                      </div>
                    </div>
                  </div>

                  {/* Missing Memory Frames Alert & Re-run Trigger */}
                  {!hasFrames && (
                    <div className="bg-amber-950/40 border border-amber-500/30 rounded-xl p-2.5 flex items-center justify-between gap-2 text-[11px] text-amber-300">
                      <div className="flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span>Frames cleared on reload</span>
                      </div>
                      <button
                        onClick={() => handleRestore(run)}
                        disabled={isRestoring}
                        className="flex items-center gap-1 px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 rounded-lg font-semibold transition"
                      >
                        {isRestoring ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          <Play className="w-3 h-3" />
                        )}
                        <span>Re-run to restore</span>
                      </button>
                    </div>
                  )}

                  {/* Selection Toggle Button */}
                  <button
                    onClick={() => onToggleSelectRun(run.id)}
                    className={`w-full py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition ${
                      isSelected
                        ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60'
                    }`}
                  >
                    {isSelected ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Selected for Comparison</span>
                      </>
                    ) : (
                      <span>Select for Comparison</span>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Drawer Footer: Compare Action */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex flex-col gap-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Comparison Selection:</span>
            <span className="font-mono font-bold text-white">{selectedCount} / 2 Selected</span>
          </div>

          <button
            onClick={onStartCompare}
            disabled={!canCompare}
            className="w-full py-3 px-4 rounded-xl font-bold bg-gradient-to-r from-brand-600 to-cyan-500 hover:from-brand-500 hover:to-cyan-400 text-white shadow-lg shadow-brand-500/25 active:scale-[0.99] transition disabled:opacity-40 disabled:hover:from-brand-600 disabled:hover:to-cyan-500 flex items-center justify-center gap-2 text-xs"
          >
            <GitCompare className="w-4 h-4" />
            <span>
              {selectedCount < 2
                ? `Select ${2 - selectedCount} more run${selectedCount === 1 ? '' : 's'} to compare`
                : canCompare
                ? 'Compare 2 Runs Side-by-Side'
                : 'Re-run selected runs to restore frames'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { Controls } from './components/Controls';
import { Timeline } from './components/Timeline';
import { Hyetograph } from './components/Hyetograph';
import { MapViewer } from './components/MapViewer';
import { ComparisonView } from './components/ComparisonView';
import { RunComparisonView } from './components/RunComparisonView';
import { RunHistoryDrawer } from './components/RunHistoryDrawer';
import { PointProbe } from './components/PointProbe';
import { HazardMetrics } from './components/HazardMetrics';
import { EvaluationTab } from './components/EvaluationTab';
import {
  fetchHealth,
  fetchTerrain,
  fetchPresets,
  runForecast,
  runCompare,
} from './api';
import {
  CompareResult,
  ForecastParams,
  ForecastResult,
  HealthStatus,
  PresetItem,
  SavedRun,
  TerrainData,
} from './types';
import { AlertTriangle, RefreshCw } from 'lucide-react';

const DEFAULT_PARAMS: ForecastParams = {
  rain_intensity_mmhr: 80.0,
  rain_duration_min: 45.0,
  rain_shape: 'constant',
  drain_capacity_mmhr: 0.0,
  horizon_steps: 120,
  frame_stride: 1,
};

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isMock, setIsMock] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'simulation' | 'evaluation'>('simulation');
  const [terrain, setTerrain] = useState<TerrainData | null>(null);
  const [presets, setPresets] = useState<PresetItem[]>([]);

  const [params, setParams] = useState<ForecastParams>(DEFAULT_PARAMS);
  const [forecastResult, setForecastResult] = useState<ForecastResult | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResult | null>(null);
  const [selectedProbeCell, setSelectedProbeCell] = useState<{
    row: number;
    col: number;
    elevation: number;
  } | null>(null);

  const [currentFrame, setCurrentFrame] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speedMultiplier, setSpeedMultiplier] = useState<number>(1);

  const [isForecasting, setIsForecasting] = useState<boolean>(false);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Scenario Run History state (stored in memory + lightweight localStorage)
  const [savedRuns, setSavedRuns] = useState<SavedRun[]>(() => {
    try {
      const stored = localStorage.getItem('hydrovision_saved_runs');
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          return parsed.map((item: any) => ({
            ...item,
            frames: null, // Frames not kept in localStorage to stay within browser quota
          }));
        }
      }
    } catch (e) {
      console.warn('Failed to parse saved runs from localStorage:', e);
    }
    return [];
  });

  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [activeRunComparison, setActiveRunComparison] = useState<{
    runA: SavedRun;
    runB: SavedRun;
  } | null>(null);

  // Sync lightweight metadata to localStorage whenever saved runs change
  useEffect(() => {
    try {
      const serialized = savedRuns.map(
        ({ id, name, letter, timestamp, params, summary }) => ({
          id,
          name,
          letter,
          timestamp,
          params,
          summary,
        })
      );
      localStorage.setItem('hydrovision_saved_runs', JSON.stringify(serialized));
    } catch (e) {
      console.warn('Failed to save runs to localStorage:', e);
    }
  }, [savedRuns]);

  // Initialize application and load static metadata
  useEffect(() => {
    const initialize = async () => {
      try {
        setErrorMessage(null);
        const [h, t, p] = await Promise.all([
          fetchHealth(),
          fetchTerrain(),
          fetchPresets(),
        ]);
        setHealth(h);
        setIsMock(Boolean(h?.is_mock));
        setTerrain(t);
        setPresets(p);

        // Run initial default forecast so map is populated immediately
        const initialForecast = await runForecast(DEFAULT_PARAMS);
        setForecastResult(initialForecast);

        // If a restored run matches default params, populate its frames
        setSavedRuns((prev) =>
          prev.map((run) => {
            if (
              !run.frames &&
              JSON.stringify(run.params) === JSON.stringify(DEFAULT_PARAMS)
            ) {
              return { ...run, frames: initialForecast.depth_frames };
            }
            return run;
          })
        );
      } catch (err: any) {
        console.error('Initialization error:', err);
        setErrorMessage(err.message || 'Failed to connect to HydroVision backend server.');
      }
    };

    initialize();
  }, []);

  // Poll /health every 30 seconds to track engine status
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const h = await fetchHealth();
        setHealth(h);
        setIsMock(Boolean(h?.is_mock));
      } catch (err) {
        console.warn('Failed to poll /health endpoint:', err);
      }
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // Execute neural surrogate forecast
  const handleRunForecast = useCallback(async () => {
    setIsForecasting(true);
    setErrorMessage(null);
    try {
      const res = await runForecast(params);
      setForecastResult(res);
      setCompareResult(null); // Exit comparison view if active
      setCurrentFrame(0);
    } catch (err: any) {
      console.error('Forecast error:', err);
      setErrorMessage(err.message || 'Forecast simulation failed.');
    } finally {
      setIsForecasting(false);
    }
  }, [params]);

  // Execute solver verification
  const handleRunCompare = useCallback(async () => {
    setIsComparing(true);
    setErrorMessage(null);
    try {
      const res = await runCompare(params);
      setCompareResult(res);
      setForecastResult(res.surrogate);
      setCurrentFrame(0);
    } catch (err: any) {
      console.error('Comparison error:', err);
      setErrorMessage(err.message || 'Comparison verification failed.');
    } finally {
      setIsComparing(false);
    }
  }, [params]);

  // Handle parameter changes
  const handleParamsChange = (updated: Partial<ForecastParams>) => {
    setParams((prev) => ({ ...prev, ...updated }));
  };

  // Select a predefined storm preset
  const handleSelectPreset = (preset: PresetItem) => {
    setParams({ ...preset.params });
  };

  // Save current forecast run (keep up to 3 runs in memory)
  const handleSaveCurrentRun = useCallback(() => {
    if (!forecastResult || !forecastResult.depth_frames || savedRuns.length >= 3) {
      return;
    }

    const usedLetters = new Set(savedRuns.map((r) => r.letter));
    const letter = ['A', 'B', 'C'].find((l) => !usedLetters.has(l)) || 'A';

    const totalVolume = forecastResult.volume_m3_series?.length
      ? forecastResult.volume_m3_series[forecastResult.volume_m3_series.length - 1]
      : forecastResult.depth_frames[forecastResult.depth_frames.length - 1].reduce(
          (acc, row) => acc + row.reduce((rAcc, cell) => rAcc + cell, 0),
          0
        ) * 1600.0;

    const autoName = `Run ${letter}: ${params.rain_intensity_mmhr} mm/h, drain ${params.drain_capacity_mmhr}`;

    const newRun: SavedRun = {
      id: `run_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      name: autoName,
      letter,
      timestamp: Date.now(),
      params: { ...params },
      summary: {
        peak_depth_m: forecastResult.peak_depth_m,
        flooded_area_m2: forecastResult.flooded_area_m2,
        total_volume_m3: totalVolume,
      },
      frames: forecastResult.depth_frames,
    };

    setSavedRuns((prev) => [...prev, newRun]);
    setIsDrawerOpen(true);
  }, [forecastResult, params, savedRuns]);

  // Rename a saved run
  const handleRenameRun = useCallback((id: string, newName: string) => {
    setSavedRuns((prev) =>
      prev.map((r) => (r.id === id ? { ...r, name: newName } : r))
    );
    setActiveRunComparison((prev) => {
      if (!prev) return null;
      return {
        runA: prev.runA.id === id ? { ...prev.runA, name: newName } : prev.runA,
        runB: prev.runB.id === id ? { ...prev.runB, name: newName } : prev.runB,
      };
    });
  }, []);

  // Delete a saved run
  const handleDeleteRun = useCallback((id: string) => {
    setSavedRuns((prev) => prev.filter((r) => r.id !== id));
    setSelectedRunIds((prev) => prev.filter((runId) => runId !== id));
    setActiveRunComparison((prev) => {
      if (prev && (prev.runA.id === id || prev.runB.id === id)) {
        return null;
      }
      return prev;
    });
  }, []);

  // Re-run simulation to restore frames in memory
  const handleRerunToRestore = useCallback(async (run: SavedRun) => {
    try {
      const res = await runForecast(run.params);
      setSavedRuns((prev) =>
        prev.map((r) => (r.id === run.id ? { ...r, frames: res.depth_frames } : r))
      );
      setActiveRunComparison((prev) => {
        if (!prev) return null;
        let nextA = prev.runA;
        let nextB = prev.runB;
        if (nextA.id === run.id) nextA = { ...nextA, frames: res.depth_frames };
        if (nextB.id === run.id) nextB = { ...nextB, frames: res.depth_frames };
        return { runA: nextA, runB: nextB };
      });
    } catch (err: any) {
      console.error('Failed to rerun simulation for run:', err);
      setErrorMessage(`Failed to rerun scenario ${run.name}: ${err.message || 'Network error'}`);
    }
  }, []);

  // Toggle selection for comparison (max 2 selected)
  const handleToggleSelectRun = useCallback((id: string) => {
    setSelectedRunIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 2) {
        return [prev[1], id];
      }
      return [...prev, id];
    });
  }, []);

  // Launch side-by-side run comparison
  const handleStartCompare = useCallback(() => {
    if (selectedRunIds.length !== 2) return;
    const runA = savedRuns.find((r) => r.id === selectedRunIds[0]);
    const runB = savedRuns.find((r) => r.id === selectedRunIds[1]);
    if (runA && runB && runA.frames && runB.frames) {
      setActiveRunComparison({ runA, runB });
      setIsDrawerOpen(false);
      setCompareResult(null);
    }
  }, [selectedRunIds, savedRuns]);

  const totalFrames = forecastResult?.depth_frames.length || 121;
  const activeDepthFrame =
    forecastResult?.depth_frames[currentFrame] ||
    forecastResult?.depth_frames[0] ||
    null;

  const depthTimeseries = useMemo(() => {
    if (!selectedProbeCell || !forecastResult?.depth_frames) return [];
    return forecastResult.depth_frames.map(
      (frame) => frame[selectedProbeCell.row]?.[selectedProbeCell.col] ?? 0
    );
  }, [selectedProbeCell, forecastResult]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col font-sans">
      {/* Persistent Amber Mock-Mode Banner */}
      {isMock && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 text-amber-300 px-4 py-2 text-xs font-semibold flex items-center justify-center gap-2 tracking-wide uppercase shadow-sm">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>MOCK ENGINE: simulated data, not real model results</span>
        </div>
      )}

      <Header
        health={health}
        inferenceTimeMs={forecastResult?.inference_time_ms}
        modelName={forecastResult?.model_name}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenHistory={() => setIsDrawerOpen(true)}
        savedRunsCount={savedRuns.length}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-6">
        {/* Error Notification Banner */}
        {errorMessage && (
          <div className="bg-rose-950/80 border border-rose-500/40 rounded-xl p-4 flex items-center justify-between gap-3 text-rose-200 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => handleRunForecast()}
              className="flex items-center gap-1 font-semibold px-2.5 py-1 bg-rose-800/40 hover:bg-rose-800/80 rounded-lg transition"
            >
              <RefreshCw className="w-3 h-3" /> Retry
            </button>
          </div>
        )}

        {activeTab === 'evaluation' ? (
          <EvaluationTab presets={presets} isGlobalMock={isMock} />
        ) : (
          <>
            {/* Hazard Risk Summary Bar */}
            <HazardMetrics depthFrame={activeDepthFrame} />

            {/* Scenario Comparison View, Solver Verification View, or Main Simulation View */}
            {activeRunComparison ? (
              <RunComparisonView
                runA={activeRunComparison.runA}
                runB={activeRunComparison.runB}
                terrain={terrain}
                onClose={() => setActiveRunComparison(null)}
                isMock={isMock}
              />
            ) : compareResult ? (
              <ComparisonView
                compareData={compareResult}
                terrain={terrain}
                currentFrame={currentFrame}
                onClose={() => setCompareResult(null)}
                isMock={isMock}
              />
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left Column: Map Viewer & Probe */}
                <div className="lg:col-span-7 flex flex-col gap-4">
                  <MapViewer
                    terrain={terrain}
                    depthFrame={activeDepthFrame}
                    title="⚡ Live Neural Surrogate Forecast Overlay"
                    selectedProbeCell={selectedProbeCell}
                    onSelectProbeCell={setSelectedProbeCell}
                    isMock={isMock}
                  />

                  <PointProbe
                    selectedCell={selectedProbeCell}
                    depthTimeseries={depthTimeseries}
                    currentFrame={currentFrame}
                    totalFrames={totalFrames}
                    onClear={() => setSelectedProbeCell(null)}
                  />
                </div>

                {/* Right Column: Controls & Hyetograph */}
                <div className="lg:col-span-5 flex flex-col gap-4">
                  <Controls
                    params={params}
                    onChange={handleParamsChange}
                    onRunForecast={handleRunForecast}
                    onRunCompare={handleRunCompare}
                    presets={presets}
                    onSelectPreset={handleSelectPreset}
                    isForecasting={isForecasting}
                    isComparing={isComparing}
                    onSaveRun={handleSaveCurrentRun}
                    canSaveRun={Boolean(forecastResult && forecastResult.depth_frames?.length > 0)}
                    savedRunsCount={savedRuns.length}
                    onOpenDrawer={() => setIsDrawerOpen(true)}
                  />

                  <Hyetograph
                    rainSeriesMmhr={forecastResult?.rain_series_mmhr || []}
                    currentFrame={currentFrame}
                    totalFrames={totalFrames}
                  />
                </div>
              </div>
            )}

            {/* Global Timeline Scrubber (only shown in single-run mode) */}
            {!activeRunComparison && (
              <Timeline
                currentFrame={currentFrame}
                totalFrames={totalFrames}
                timesS={forecastResult?.times_s || []}
                isPlaying={isPlaying}
                onTogglePlay={() => setIsPlaying(!isPlaying)}
                onSeek={(frame) => setCurrentFrame(frame)}
                speedMultiplier={speedMultiplier}
                onChangeSpeed={(spd) => setSpeedMultiplier(spd)}
                peakDepthM={forecastResult?.peak_depth_m}
                floodedAreaM2={forecastResult?.flooded_area_m2}
              />
            )}
          </>
        )}
      </main>

      {/* Scenario Run History Drawer */}
      <RunHistoryDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        savedRuns={savedRuns}
        onSaveCurrentRun={handleSaveCurrentRun}
        canSaveCurrent={Boolean(forecastResult && forecastResult.depth_frames?.length > 0)}
        onRenameRun={handleRenameRun}
        onDeleteRun={handleDeleteRun}
        onRerunToRestore={handleRerunToRestore}
        selectedRunIds={selectedRunIds}
        onToggleSelectRun={handleToggleSelectRun}
        onStartCompare={handleStartCompare}
        isMock={isMock}
      />

      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-6 text-center text-xs text-slate-500">
        HydroVision — Problem Statement PS 1.2 • Gradient Club, Dept. of AIML, BMS College of Engineering
      </footer>
    </div>
  );
};

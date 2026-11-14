import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Header } from './components/Header';
import { Controls } from './components/Controls';
import { Timeline } from './components/Timeline';
import { Hyetograph } from './components/Hyetograph';
import { MapViewer } from './components/MapViewer';
import { ComparisonView } from './components/ComparisonView';
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

            {/* Comparison View or Main Map View */}
            {compareResult ? (
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
                  />

                  <Hyetograph
                    rainSeriesMmhr={forecastResult?.rain_series_mmhr || []}
                    currentFrame={currentFrame}
                    totalFrames={totalFrames}
                  />
                </div>
              </div>
            )}

            {/* Global Timeline Scrubber */}
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
          </>
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-6 text-center text-xs text-slate-500">
        HydroVision — Problem Statement PS 1.2 • Gradient Club, Dept. of AIML, BMS College of Engineering
      </footer>
    </div>
  );
};

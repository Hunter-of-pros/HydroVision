import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import { TerrainData } from '../types';

interface MapViewerProps {
  terrain: TerrainData | null;
  depthFrame: number[][] | null; // 64x64 depth in meters
  nextDepthFrame?: number[][] | null;
  frameProgress?: number;
  title?: string;
  isSolverComparison?: boolean;
  selectedProbeCell?: { row: number; col: number } | null;
  onSelectProbeCell?: (cell: { row: number; col: number; elevation: number } | null) => void;
  isMock?: boolean;
  isLoading?: boolean;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  terrain,
  depthFrame,
  nextDepthFrame,
  frameProgress = 0,
  title = 'Urban Flood Inundation Map',
  isSolverComparison: _isSolverComparison = false,
  selectedProbeCell,
  onSelectProbeCell,
  isMock = false,
  isLoading = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const cachedHillshadeRef = useRef<HTMLCanvasElement | null>(null);
  const [hoverCell, setHoverCell] = useState<{
    row: number;
    col: number;
    elevation: number;
    depth: number;
  } | null>(null);

  const [showGrid, setShowGrid] = useState<boolean>(false);
  const [showFlowVectors, setShowFlowVectors] = useState<boolean>(true);
  const [animTick, setAnimTick] = useState<number>(0);
  const [basemapMode, setBasemapMode] = useState<'streets' | 'satellite'>('streets');
  const [imagesLoaded, setImagesLoaded] = useState<boolean>(false);

  const streetsImgRef = useRef<HTMLImageElement | null>(null);
  const satImgRef = useRef<HTMLImageElement | null>(null);

  const rows = terrain?.shape[0] || 64;
  const cols = terrain?.shape[1] || 64;

  // Real geographic bounds for Marathahalli-Bellandur corridor
  const minLat = terrain?.bounds?.[0] ?? 12.923194;
  const minLon = terrain?.bounds?.[1] ?? 77.676250;
  const maxLat = terrain?.bounds?.[2] ?? 12.958750;
  const maxLon = terrain?.bounds?.[3] ?? 77.711806;

  // Preload basemap images on mount
  useEffect(() => {
    let loadedCount = 0;
    const checkLoaded = () => {
      loadedCount++;
      if (loadedCount >= 2) {
        setImagesLoaded(true);
      }
    };

    const streets = new Image();
    streets.src = '/basemap_streets.png';
    streets.onload = () => {
      streetsImgRef.current = streets;
      checkLoaded();
    };
    streets.onerror = () => checkLoaded();

    const sat = new Image();
    sat.src = '/basemap_satellite.png';
    sat.onload = () => {
      satImgRef.current = sat;
      checkLoaded();
    };
    sat.onerror = () => checkLoaded();
  }, []);

  // Precompute min/max terrain elevation
  const { minElev, maxElev } = useMemo(() => {
    if (!terrain) return { minElev: 863.98, maxElev: 901.81 };
    return {
      minElev: terrain.min_elevation,
      maxElev: terrain.max_elevation,
    };
  }, [terrain]);

  // Compute terrain hillshade once when terrain loads for crisp relief under water
  useEffect(() => {
    if (!terrain) return;
    const tRows = terrain.shape[0];
    const tCols = terrain.shape[1];
    const hsCanvas = document.createElement('canvas');
    hsCanvas.width = tCols;
    hsCanvas.height = tRows;
    const hsCtx = hsCanvas.getContext('2d');
    if (!hsCtx) return;

    const imgData = hsCtx.createImageData(tCols, tRows);
    const elev = terrain.elevation;
    const dx = terrain.dx_m || 60.9;
    // NW illumination (315 deg azimuth, 45 deg altitude)
    const sunAz = (315 * Math.PI) / 180;
    const sunAlt = (45 * Math.PI) / 180;

    for (let r = 0; r < tRows; r++) {
      for (let c = 0; c < tCols; c++) {
        const cLeft = Math.max(0, c - 1);
        const cRight = Math.min(tCols - 1, c + 1);
        const rUp = Math.max(0, r - 1);
        const rDown = Math.min(tRows - 1, r + 1);

        const dzdx = (elev[r][cRight] - elev[r][cLeft]) / ((cRight - cLeft) * dx);
        const dzdy = (elev[rDown][c] - elev[rUp][c]) / ((rDown - rUp) * dx);

        const slope = Math.atan(Math.sqrt(dzdx * dzdx + dzdy * dzdy));
        let aspect = Math.atan2(dzdy, -dzdx);
        if (aspect < 0) aspect += 2 * Math.PI;

        const hillshade = Math.max(
          0,
          Math.sin(sunAlt) * Math.cos(slope) +
            Math.cos(sunAlt) * Math.sin(slope) * Math.cos(sunAz - aspect)
        );

        const val = Math.floor(hillshade * 255);
        const idx = (r * tCols + c) * 4;
        imgData.data[idx] = val;
        imgData.data[idx + 1] = val;
        imgData.data[idx + 2] = val;
        imgData.data[idx + 3] = 255;
      }
    }

    hsCtx.putImageData(imgData, 0, 0);
    cachedHillshadeRef.current = hsCanvas;
  }, [terrain]);

  // Subtle continuous water flow ripple animation
  useEffect(() => {
    let animId: number;
    const loop = () => {
      setAnimTick((t) => (t + 1) % 360);
      animId = requestAnimationFrame(loop);
    };
    animId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Frame Interpolation for sub-second smooth fluid rendering
  const activeDepth = useMemo(() => {
    if (!depthFrame) return null;
    if (!nextDepthFrame || frameProgress <= 0.01) return depthFrame;
    const p = Math.max(0, Math.min(1, frameProgress));
    const blended: number[][] = [];
    for (let r = 0; r < rows; r++) {
      const row: number[] = [];
      for (let c = 0; c < cols; c++) {
        const d0 = depthFrame[r]?.[c] ?? 0;
        const d1 = nextDepthFrame[r]?.[c] ?? d0;
        row.push((1 - p) * d0 + p * d1);
      }
      blended.push(row);
    }
    return blended;
  }, [depthFrame, nextDepthFrame, frameProgress, rows, cols]);

  // Render high-fidelity water and map onto canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !terrain) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const cellW = width / cols;
    const cellH = height / rows;

    ctx.clearRect(0, 0, width, height);

    // 1. Draw Selected Basemap Layer
    if (basemapMode === 'streets' && streetsImgRef.current) {
      ctx.drawImage(streetsImgRef.current, 0, 0, width, height);
      // Subtle contrast overlay to enhance street readability
      ctx.fillStyle = 'rgba(15, 23, 42, 0.08)';
      ctx.fillRect(0, 0, width, height);
    } else if (basemapMode === 'satellite' && satImgRef.current) {
      ctx.drawImage(satImgRef.current, 0, 0, width, height);
      ctx.fillStyle = 'rgba(15, 23, 42, 0.12)';
      ctx.fillRect(0, 0, width, height);
    } else {
      // Clean modern light base with subtle terrain gradient
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const elev = terrain.elevation[r]?.[c] ?? 880;
          const normElev = Math.max(0, Math.min(1, (elev - minElev) / Math.max(1, maxElev - minElev)));
          const red = Math.floor(240 - normElev * 20);
          const green = Math.floor(244 - normElev * 15);
          const blue = Math.floor(248 - normElev * 10);
          ctx.fillStyle = `rgb(${red}, ${green}, ${blue})`;
          ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
        }
      }
    }

    // Composite hillshade relief under water so terrain topography reads clearly
    if (cachedHillshadeRef.current) {
      ctx.save();
      ctx.globalAlpha = 0.22;
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(cachedHillshadeRef.current, 0, 0, width, height);
      ctx.restore();
    }

    // 2. High-Fidelity Fluid Water Surface
    if (activeDepth) {
      ctx.save();
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const d = activeDepth[r]?.[c] ?? 0;
          if (d < 0.01) continue; // Pavement is dry below 1cm

          const x = c * cellW;
          const y = r * cellH;

          // Non-linear depth mapping
          const normD = Math.min(1, Math.sqrt(d / 1.5));
          const ripple = Math.sin((r * 4 + c * 3 + animTick * 0.08) % (Math.PI * 2)) * 0.03;
          const alpha = Math.min(0.92, Math.max(0.42, 0.45 + normD * 0.45 + ripple));

          // Physical depth color ramp:
          // < 0.05m: thin sheet flow (sky-blue)
          // 0.05m - 0.30m: street runoff (cyan/blue)
          // 0.30m - 0.70m: impassable road (deep blue)
          // > 0.70m: deep inundation (midnight indigo)
          let rVal: number, gVal: number, bVal: number;
          if (d < 0.05) {
            const t = d / 0.05;
            rVal = Math.floor(56 + t * (6 - 56));
            gVal = Math.floor(189 + t * (182 - 189));
            bVal = Math.floor(248 + t * (212 - 248));
          } else if (d < 0.3) {
            const t = (d - 0.05) / 0.25;
            rVal = Math.floor(6 + t * (2 - 6));
            gVal = Math.floor(182 + t * (132 - 182));
            bVal = Math.floor(212 + t * (199 - 212));
          } else if (d < 0.7) {
            const t = (d - 0.3) / 0.4;
            rVal = Math.floor(2 + t * (30 - 2));
            gVal = Math.floor(132 + t * (64 - 132));
            bVal = Math.floor(199 + t * (175 - 199));
          } else {
            const t = Math.min(1, (d - 0.7) / 1.0);
            rVal = Math.floor(30 + t * (15 - 30));
            gVal = Math.floor(64 + t * (23 - 64));
            bVal = Math.floor(175 + t * (42 - 175));
          }

          ctx.fillStyle = `rgba(${rVal}, ${gVal}, ${bVal}, ${alpha})`;
          ctx.fillRect(x, y, cellW + 0.5, cellH + 0.5);

          // Specular water sheen along surface borders
          if (d >= 0.15 && (r + c) % 3 === 0) {
            ctx.fillStyle = `rgba(255, 255, 255, ${Math.max(0, 0.18 + ripple)})`;
            ctx.fillRect(x + cellW * 0.2, y + cellH * 0.15, cellW * 0.6, cellH * 0.25);
          }
        }
      }
      ctx.restore();
    }

    // Subtle 64x64 grid lines
    if (showGrid) {
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
      ctx.lineWidth = 0.5;
      for (let r = 0; r <= rows; r += 4) {
        ctx.beginPath();
        ctx.moveTo(0, r * cellH);
        ctx.lineTo(width, r * cellH);
        ctx.stroke();
      }
      for (let c = 0; c <= cols; c += 4) {
        ctx.beginPath();
        ctx.moveTo(c * cellW, 0);
        ctx.lineTo(c * cellW, height);
        ctx.stroke();
      }
    }

    // Indicative Flow Vectors
    if (showFlowVectors && terrain) {
      ctx.save();
      const elev = terrain.elevation;
      const step = 4;
      ctx.fillStyle = 'rgba(2, 132, 199, 0.85)';
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.lineWidth = 1;

      for (let r = 2; r < rows; r += step) {
        for (let c = 2; c < cols; c += step) {
          const depth = activeDepth?.[r]?.[c] ?? 0;
          if (depth < 0.03) continue;

          const rUp = Math.max(0, r - 1);
          const rDown = Math.min(rows - 1, r + 1);
          const cLeft = Math.max(0, c - 1);
          const cRight = Math.min(cols - 1, c + 1);

          const dzdx = (elev[r][cRight] - elev[r][cLeft]) / 2;
          const dzdy = (elev[rDown][c] - elev[rUp][c]) / 2;

          let vx = -dzdx;
          let vy = -dzdy;
          const mag = Math.hypot(vx, vy);

          if (mag > 0.05) {
            vx /= mag;
            vy /= mag;
            const cx = (c + 0.5) * cellW;
            const cy = (r + 0.5) * cellH;
            const arrowLen = Math.min(cellW * 1.6, 10 + depth * 5);

            ctx.beginPath();
            ctx.moveTo(cx, cy);
            ctx.lineTo(cx + vx * arrowLen, cy + vy * arrowLen);
            ctx.stroke();

            const angle = Math.atan2(vy, vx);
            const headLen = 3.5;
            ctx.beginPath();
            ctx.moveTo(cx + vx * arrowLen, cy + vy * arrowLen);
            ctx.lineTo(
              cx + vx * arrowLen - headLen * Math.cos(angle - Math.PI / 6),
              cy + vy * arrowLen - headLen * Math.sin(angle - Math.PI / 6)
            );
            ctx.lineTo(
              cx + vx * arrowLen - headLen * Math.cos(angle + Math.PI / 6),
              cy + vy * arrowLen - headLen * Math.sin(angle + Math.PI / 6)
            );
            ctx.closePath();
            ctx.fill();
          }
        }
      }
      ctx.restore();
    }

    // Active Probe Pin Marker (red circle with white center)
    const probeCell = selectedProbeCell || { row: 38, col: 26 };
    const pinX = (probeCell.col + 0.5) * cellW;
    const pinY = (probeCell.row + 0.5) * cellH;

    ctx.save();
    // Soft outer ring / shadow
    ctx.beginPath();
    ctx.arc(pinX, pinY, 9, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = 'rgba(239, 68, 68, 0.4)';
    ctx.shadowBlur = 8;
    ctx.fill();

    // Red outer stroke ring
    ctx.beginPath();
    ctx.arc(pinX, pinY, 7, 0, 2 * Math.PI);
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 3.5;
    ctx.stroke();

    // Center white dot
    ctx.beginPath();
    ctx.arc(pinX, pinY, 2.5, 0, 2 * Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    ctx.restore();
  }, [
    terrain,
    depthFrame,
    activeDepth,
    rows,
    cols,
    minElev,
    maxElev,
    showGrid,
    showFlowVectors,
    animTick,
    basemapMode,
    imagesLoaded,
    selectedProbeCell,
  ]);

  // Cell Coordinates Calculation
  const getCellLatLon = (r: number, c: number) => {
    const lat = maxLat - ((r + 0.5) / rows) * (maxLat - minLat);
    const lon = minLon + ((c + 0.5) / cols) * (maxLon - minLon);
    return { lat, lon };
  };

  // Handle mouse move to extract cell diagnostics
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !terrain) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const col = Math.floor((x / rect.width) * cols);
    const row = Math.floor((y / rect.height) * rows);

    if (row >= 0 && row < rows && col >= 0 && col < cols) {
      const elevation = terrain.elevation[row]?.[col] ?? 0;
      const depth = depthFrame?.[row]?.[col] ?? 0;
      setHoverCell({ row, col, elevation, depth });
    }
  };

  const handleMouseLeave = () => {
    setHoverCell(null);
  };

  // Handle click to drop/toggle probe pin
  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!onSelectProbeCell || !terrain) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const col = Math.floor((x / rect.width) * cols);
    const row = Math.floor((y / rect.height) * rows);

    if (row >= 0 && row < rows && col >= 0 && col < cols) {
      const elevation = terrain.elevation[row]?.[col] ?? 0;
      onSelectProbeCell({ row, col, elevation });
    }
  };

  // Export current canvas frame as high-resolution PNG snapshot
  const handleDownloadSnapshot = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    if (!isMock) {
      const link = document.createElement('a');
      link.download = `hydrovision-flood-map-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      return;
    }

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    ctx.drawImage(canvas, 0, 0);

    ctx.save();
    ctx.translate(exportCanvas.width / 2, exportCanvas.height / 2);
    ctx.rotate(-Math.PI / 6);
    ctx.font = '900 42px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.fillText('MOCK DATA', 2, 2);

    ctx.fillStyle = 'rgba(245, 158, 11, 0.85)';
    ctx.fillText('MOCK DATA', 0, 0);

    ctx.font = 'bold 16px sans-serif';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.fillText('SIMULATED • NOT REAL RESULTS', 0, 36);
    ctx.restore();

    ctx.save();
    ctx.fillStyle = 'rgba(180, 83, 9, 0.9)';
    ctx.fillRect(12, 12, 130, 26);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px monospace';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('⚠️ MOCK DATA', 20, 25);
    ctx.restore();

    const link = document.createElement('a');
    link.download = `hydrovision-mock-flood-map-${Date.now()}.png`;
    link.href = exportCanvas.toDataURL('image/png');
    link.click();
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3 relative overflow-hidden text-slate-900">
      {/* Top Map Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-xs text-slate-700">
          <h3 className="font-bold text-slate-800">{title}</h3>
          <span className="text-slate-400">&middot;</span>
          <span className="font-mono text-slate-500">{terrain?.dx_m ?? 60.9} m/cell</span>
          <span className="text-slate-400">&middot;</span>
          <span className="font-mono text-slate-500">Marathahalli-Bellandur ORR</span>
        </div>

        {/* Basemap Switcher & Action Controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Streets vs Satellite */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
            <button
              onClick={() => setBasemapMode('streets')}
              className={`px-2.5 py-1 rounded-md transition font-medium ${
                basemapMode === 'streets'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Streets
            </button>
            <button
              onClick={() => setBasemapMode('satellite')}
              className={`px-2.5 py-1 rounded-md transition font-medium ${
                basemapMode === 'satellite'
                  ? 'bg-white text-slate-900 shadow-xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Satellite
            </button>
          </div>

          {/* Flow Vectors */}
          <button
            onClick={() => setShowFlowVectors(!showFlowVectors)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
              showFlowVectors
                ? 'bg-white text-slate-900 border-slate-300 shadow-xs font-semibold'
                : 'bg-slate-100 text-slate-600 border-slate-200 hover:bg-slate-200'
            }`}
          >
            Flow Vectors
          </button>

          {/* Layers (Grid) */}
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`px-2.5 py-1 rounded-lg border text-xs font-medium transition ${
              showGrid
                ? 'bg-slate-200 text-slate-900 border-slate-300'
                : 'bg-slate-100 text-slate-700 border-slate-200 hover:bg-slate-200'
            }`}
          >
            Grid
          </button>

          {/* Export */}
          <button
            onClick={handleDownloadSnapshot}
            className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 border border-slate-200 text-slate-700 text-xs font-medium transition"
          >
            Export
          </button>
        </div>
      </div>

      {/* Map View Container */}
      <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-100 border border-slate-200 flex items-center justify-center">
        {!terrain ? (
          <div className="w-full h-full bg-slate-100 flex flex-col items-center justify-center gap-3 animate-pulse p-6 text-slate-500">
            <div className="w-10 h-10 rounded-full border-2 border-brand-500/40 border-t-brand-600 animate-spin" />
            <span className="text-xs font-mono">Loading DEM terrain raster...</span>
          </div>
        ) : (
          <canvas
            ref={canvasRef}
            width={768}
            height={768}
            onClick={handleCanvasClick}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            className="w-full h-full object-contain cursor-crosshair rounded-lg"
          />
        )}

        {/* Loading Overlay when rolling out inference */}
        {isLoading && (
          <div className="absolute inset-0 bg-white/40 backdrop-blur-[1px] flex items-center justify-center pointer-events-none z-20">
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-full bg-white/95 border border-brand-200 text-brand-700 text-xs font-semibold shadow-xl">
              <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
              <span>Simulating surrogate...</span>
            </div>
          </div>
        )}

        {/* Standard North Arrow Indicator */}
        <div className="absolute top-3 right-3 px-2 py-0.5 rounded-lg bg-white/90 backdrop-blur border border-slate-200 shadow-xs flex items-center gap-1 pointer-events-none z-10">
          <span className="text-[11px] font-bold text-slate-700 font-mono">N &uarr;</span>
        </div>

        {/* Selected Probe Badge or Click Prompt */}
        {selectedProbeCell ? (
          <div className="absolute top-3 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-lg px-2.5 py-1 text-[11px] text-slate-700 font-mono shadow-xs flex items-center gap-1.5 z-10">
            <span>
              Probe: [{selectedProbeCell.row}, {selectedProbeCell.col}] &middot;{' '}
              {getCellLatLon(selectedProbeCell.row, selectedProbeCell.col).lat.toFixed(3)}&deg;N
            </span>
          </div>
        ) : (
          <div className="absolute top-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2.5 py-1 text-[11px] text-slate-700 font-mono shadow-xs pointer-events-none z-10">
            Click street to inspect water depth
          </div>
        )}

        {/* Indicative Flow Direction Overlay Pill at Bottom Left */}
        {showFlowVectors && (
          <div className="absolute bottom-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2.5 py-1 text-[11px] text-slate-700 font-mono shadow-xs pointer-events-none z-10 flex items-center gap-1.5">
            <span>Indicative flow direction</span>
          </div>
        )}

        {/* Live Hover Inspector Overlay */}
        {hoverCell && (
          <div className="absolute bottom-11 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-xl px-3 py-2 text-xs shadow-xl font-mono flex flex-col gap-0.5 pointer-events-none z-10 text-slate-800">
            <div className="flex items-center justify-between gap-4 text-slate-500 text-[10px] border-b border-slate-200 pb-1">
              <span>
                Cell [{hoverCell.row}, {hoverCell.col}] •{' '}
                {getCellLatLon(hoverCell.row, hoverCell.col).lat.toFixed(4)}°N,{' '}
                {getCellLatLon(hoverCell.row, hoverCell.col).lon.toFixed(4)}°E
              </span>
              <span className={hoverCell.depth >= 0.05 ? 'text-cyan-700 font-bold' : 'text-slate-400'}>
                {hoverCell.depth >= 0.05 ? 'INUNDATED' : 'DRY'}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Ground Elev (z):</span>
              <span className="font-bold text-slate-900">{hoverCell.elevation.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Flood Depth (h):</span>
              <span className={`font-bold ${hoverCell.depth >= 0.05 ? 'text-cyan-700' : 'text-slate-500'}`}>
                {hoverCell.depth.toFixed(3)} m ({(hoverCell.depth * 100).toFixed(0)} cm)
              </span>
            </div>
            <div className="flex justify-between gap-4 text-[10px] text-slate-400 pt-0.5">
              <span>Water Surface (z+h):</span>
              <span>{(hoverCell.elevation + hoverCell.depth).toFixed(2)} m</span>
            </div>
          </div>
        )}
      </div>

      {/* Colormap Legend Scale */}
      <div className="flex flex-col gap-1.5 pt-1">
        <div className="h-2 w-full rounded-full overflow-hidden flex shadow-inner border border-slate-200">
          <div className="w-[12%] bg-slate-200" title="Dry pavement (< 0.01m / 1cm)" />
          <div className="w-[20%] bg-gradient-to-r from-sky-400 to-cyan-500" title="1cm - 15cm (Thin sheet flow)" />
          <div className="w-[34%] bg-gradient-to-r from-cyan-500 to-blue-600" title="15cm - 60cm (Street curb overflow)" />
          <div className="w-[34%] bg-gradient-to-r from-blue-600 to-indigo-950" title="60cm - 2.0m+ (Deep deluge)" />
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 font-mono">
          <span>Dry (&lt;1cm)</span>
          <span>5cm Sheet flow</span>
          <span>15cm Curb breached</span>
          <span>60cm Vehicle hazard</span>
          <span>2.0m+ Deep deluge</span>
        </div>
      </div>
    </div>
  );
};

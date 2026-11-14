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
  isMock: _isMock = false,
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

  // Compute terrain hillshade once when terrain loads for crisp 3D relief under water
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
    const sinAlt = Math.sin(sunAlt);
    const cosAlt = Math.cos(sunAlt);

    for (let r = 0; r < tRows; r++) {
      for (let c = 0; c < tCols; c++) {
        const rPrev = Math.max(0, r - 1);
        const rNext = Math.min(tRows - 1, r + 1);
        const cPrev = Math.max(0, c - 1);
        const cNext = Math.min(tCols - 1, c + 1);

        const dzdx = ((elev[r]?.[cNext] ?? 0) - (elev[r]?.[cPrev] ?? 0)) / (2 * dx);
        const dzdy = ((elev[rNext]?.[c] ?? 0) - (elev[rPrev]?.[c] ?? 0)) / (2 * dx);

        const slope = Math.atan(Math.sqrt(dzdx * dzdx + dzdy * dzdy));
        const aspect = Math.atan2(dzdy, -dzdx);

        let shade = sinAlt * Math.cos(slope) + cosAlt * Math.sin(slope) * Math.cos(sunAz - aspect);
        shade = Math.max(0, Math.min(1, shade));
        const val = Math.round(shade * 255);

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

  // Subtle continuous animation loop for indicative flow vectors
  useEffect(() => {
    if (!showFlowVectors) return;
    const timer = setInterval(() => {
      setAnimTick((prev) => (prev + 1) % 100);
    }, 60);
    return () => clearInterval(timer);
  }, [showFlowVectors]);

  // Interpolated depth frame supporting continuous 60fps temporal blending
  const effectiveDepthFrame = useMemo(() => {
    if (!depthFrame) return null;
    if (!nextDepthFrame || frameProgress <= 0 || frameProgress >= 1) {
      return depthFrame;
    }
    const p = Math.min(1.0, Math.max(0.0, frameProgress));
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

    // Grid Mesh (always visible or toggled)
    ctx.strokeStyle = showGrid ? 'rgba(255, 255, 255, 0.45)' : 'rgba(255, 255, 255, 0.28)';
    ctx.lineWidth = 1.2;
    for (let i = 0; i <= 8; i++) {
      const pos = (i / 8) * width;
      ctx.beginPath();
      ctx.moveTo(pos, 0);
      ctx.lineTo(pos, height);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(0, pos);
      ctx.lineTo(width, pos);
      ctx.stroke();
    }

    // Arterial Road Corridor (Marathahalli-Bellandur ORR Highway)
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(0, height * 0.74);
    ctx.bezierCurveTo(width * 0.35, height * 0.65, width * 0.65, height * 0.52, width, height * 0.42);
    ctx.strokeStyle = 'rgba(245, 158, 11, 0.85)'; // Warm golden road corridor
    ctx.lineWidth = 7;
    ctx.lineCap = 'round';
    ctx.shadowColor = 'rgba(245, 158, 11, 0.35)';
    ctx.shadowBlur = 6;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, height * 0.74);
    ctx.bezierCurveTo(width * 0.35, height * 0.65, width * 0.65, height * 0.52, width, height * 0.42);
    ctx.strokeStyle = '#fef3c7'; // Inner road spine marking
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();

    // Composite hillshade relief under water so terrain topography reads clearly
    if (cachedHillshadeRef.current) {
      ctx.save();
      ctx.globalAlpha = 0.20;
      ctx.drawImage(cachedHillshadeRef.current, 0, 0, width, height);
      ctx.restore();
    }

    // 2. Realistic Fluid Flood Inundation Layer via Bilinear Upsampling & Square-Root Color Scale
    if (effectiveDepthFrame) {
      const upW = 128;
      const upH = 128;
      const upCanvas = document.createElement('canvas');
      upCanvas.width = upW;
      upCanvas.height = upH;
      const upCtx = upCanvas.getContext('2d');

      if (upCtx) {
        const imgData = upCtx.createImageData(upW, upH);
        const data = imgData.data;

        for (let y = 0; y < upH; y++) {
          const gy = (y / (upH - 1)) * (rows - 1);
          const r0 = Math.floor(gy);
          const r1 = Math.min(rows - 1, r0 + 1);
          const fy = gy - r0;

          for (let x = 0; x < upW; x++) {
            const gx = (x / (upW - 1)) * (cols - 1);
            const c0 = Math.floor(gx);
            const c1 = Math.min(cols - 1, c0 + 1);
            const fx = gx - c0;

            const d00 = effectiveDepthFrame[r0]?.[c0] ?? 0;
            const d01 = effectiveDepthFrame[r0]?.[c1] ?? 0;
            const d10 = effectiveDepthFrame[r1]?.[c0] ?? 0;
            const d11 = effectiveDepthFrame[r1]?.[c1] ?? 0;

            // Bilinear interpolation across 4 grid cell corners
            const d =
              (1 - fx) * (1 - fy) * d00 +
              fx * (1 - fy) * d01 +
              (1 - fx) * fy * d10 +
              fx * fy * d11;

            const idx = (y * upW + x) * 4;

            // Depths under 1 cm (0.01 m) remain transparent
            if (d >= 0.01) {
              // Non-linear square-root perceptual depth scaling: 0 at 1cm, 1.0 at 2.0m depth
              const t = Math.min(1.0, Math.sqrt((d - 0.01) / 1.99));

              let r: number, g: number, b: number, a: number;
              if (t < 0.25) {
                // 1cm - 15cm: Sheet flow (translucent sky-cyan)
                const s = t / 0.25;
                r = Math.round(56 * (1 - s) + 14 * s);
                g = Math.round(189 * (1 - s) + 165 * s);
                b = Math.round(248 * (1 - s) + 233 * s);
                a = Math.round((0.35 + 0.35 * s) * 255);
              } else if (t < 0.55) {
                // 15cm - 60cm: Street curb flow (vibrant azure)
                const s = (t - 0.25) / 0.3;
                r = Math.round(14 * (1 - s) + 2 * s);
                g = Math.round(165 * (1 - s) + 132 * s);
                b = Math.round(233 * (1 - s) + 199 * s);
                a = Math.round((0.70 + 0.15 * s) * 255);
              } else if (t < 0.85) {
                // 60cm - 1.4m: Deep car-submerging flow (royal cobalt)
                const s = (t - 0.55) / 0.3;
                r = Math.round(2 * (1 - s) + 30 * s);
                g = Math.round(132 * (1 - s) + 64 * s);
                b = Math.round(199 * (1 - s) + 175 * s);
                a = Math.round((0.85 + 0.08 * s) * 255);
              } else {
                // > 1.4m: Oceanic indigo retention storage
                const s = (t - 0.85) / 0.15;
                r = Math.round(30 * (1 - s) + 15 * s);
                g = Math.round(64 * (1 - s) + 23 * s);
                b = Math.round(175 * (1 - s) + 72 * s);
                a = Math.round((0.93 + 0.05 * s) * 255);
              }

              data[idx] = r;
              data[idx + 1] = g;
              data[idx + 2] = b;
              data[idx + 3] = a;
            }
          }
        }
        upCtx.putImageData(imgData, 0, 0);

        // Composite smooth upsampled fluid onto main canvas with browser filtering
        ctx.save();
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(upCanvas, 0, 0, width, height);

        // Specular water sheen overlay for realistic liquid appearance
        ctx.globalCompositeOperation = 'screen';
        const sheenGrad = ctx.createLinearGradient(0, 0, width, height);
        sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.09)');
        sheenGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.05)');
        sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0.03)');
        ctx.fillStyle = sheenGrad;
        ctx.fillRect(0, 0, width, height);
        ctx.restore();
      }
    }

    // 3. Indicative Flow Direction Streamlines (derived from water surface gradient eta = z + h)
    if (showFlowVectors && effectiveDepthFrame && terrain) {
      ctx.save();
      const elev = terrain.elevation;
      const dx = terrain.dx_m || 60.9;
      const offsetFrac = (animTick % 20) / 20.0;

      // Sample every 4th cell for clean, readable vector spacing
      for (let r = 2; r < rows - 2; r += 4) {
        for (let c = 2; c < cols - 2; c += 4) {
          const h = effectiveDepthFrame[r]?.[c] ?? 0;
          if (h >= 0.02) {
            const etaW = (elev[r]?.[c - 1] ?? 0) + (effectiveDepthFrame[r]?.[c - 1] ?? 0);
            const etaE = (elev[r]?.[c + 1] ?? 0) + (effectiveDepthFrame[r]?.[c + 1] ?? 0);
            const etaN = (elev[r - 1]?.[c] ?? 0) + (effectiveDepthFrame[r - 1]?.[c] ?? 0);
            const etaS = (elev[r + 1]?.[c] ?? 0) + (effectiveDepthFrame[r + 1]?.[c] ?? 0);

            const dEtadx = (etaE - etaW) / (2 * dx);
            const dEtady = (etaS - etaN) / (2 * dx);
            const gradMag = Math.sqrt(dEtadx * dEtadx + dEtady * dEtady);

            if (gradMag > 0.0002) {
              const angle = Math.atan2(-dEtady, -dEtadx); // Downhill flow angle
              const centerX = (c + 0.5) * cellW;
              const centerY = (r + 0.5) * cellH;

              const arrowLen = Math.min(cellW * 1.5, Math.max(cellW * 0.7, gradMag * 4000));
              const startX = centerX - Math.cos(angle) * (arrowLen * 0.5) + Math.cos(angle) * (offsetFrac * 6);
              const startY = centerY - Math.sin(angle) * (arrowLen * 0.5) + Math.sin(angle) * (offsetFrac * 6);
              const endX = startX + Math.cos(angle) * arrowLen;
              const endY = startY + Math.sin(angle) * arrowLen;

              ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)';
              ctx.lineWidth = 1.2;
              ctx.beginPath();
              ctx.moveTo(startX, startY);
              ctx.lineTo(endX, endY);
              ctx.stroke();

              const tipSize = 3;
              ctx.fillStyle = '#ffffff';
              ctx.beginPath();
              ctx.moveTo(endX, endY);
              ctx.lineTo(
                endX - tipSize * Math.cos(angle - Math.PI / 6),
                endY - tipSize * Math.sin(angle - Math.PI / 6)
              );
              ctx.lineTo(
                endX - tipSize * Math.cos(angle + Math.PI / 6),
                endY - tipSize * Math.sin(angle + Math.PI / 6)
              );
              ctx.closePath();
              ctx.fill();
            }
          }
        }
      }
      ctx.restore();
    }

    // 4. Active Probe Pin Marker (red circle with white center)
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
    effectiveDepthFrame,
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

    const link = document.createElement('a');
    link.download = `hydrovision-flood-map-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
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

      {/* Colormap Legend Scale (Square-Root Non-Linear Perceptual Ramp) */}
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

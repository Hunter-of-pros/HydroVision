import React, { useRef, useEffect, useState, useMemo } from 'react';
import {
  Loader2,
  Camera,
  ExternalLink,
  Navigation,
  AlertTriangle,
  X,
  Waves,
  Info,
} from 'lucide-react';
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
  const [isStreetViewOpen, setIsStreetViewOpen] = useState<boolean>(false);

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

  // Active cell for Street View (either selected probe cell or default hotspot)
  const activeStreetCell = useMemo(() => {
    const r = selectedProbeCell?.row ?? 38;
    const c = selectedProbeCell?.col ?? 26;
    const { lat, lon } = getCellLatLon(r, c);
    const depth = effectiveDepthFrame?.[r]?.[c] ?? depthFrame?.[r]?.[c] ?? 0;
    const elevation = terrain?.elevation[r]?.[c] ?? 878.4;
    return { row: r, col: c, lat, lon, depth, elevation };
  }, [selectedProbeCell, effectiveDepthFrame, depthFrame, terrain, rows, cols]);

  const googleStreetViewUrl = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${activeStreetCell.lat.toFixed(6)},${activeStreetCell.lon.toFixed(6)}`;
  const googleMapsSearchUrl = `https://www.google.com/maps/search/?api=1&query=${activeStreetCell.lat.toFixed(6)},${activeStreetCell.lon.toFixed(6)}`;

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

          {/* Ground Level / Street View Simulator Button */}
          <button
            onClick={() => setIsStreetViewOpen(true)}
            className="px-2.5 py-1 rounded-lg bg-sky-50 border border-sky-200 hover:bg-sky-100 text-sky-700 text-xs font-semibold flex items-center gap-1.5 transition shadow-2xs"
            title="Open Street-Level Cross-Section Simulator"
          >
            <Camera className="w-3.5 h-3.5 text-sky-600" />
            <span>Ground Level</span>
          </button>

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
          <div
            onClick={() => setIsStreetViewOpen(true)}
            className="absolute top-3 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-lg px-2.5 py-1 text-[11px] text-slate-700 font-mono shadow-xs flex items-center gap-1.5 z-10 cursor-pointer hover:bg-sky-50 hover:border-sky-300 transition"
            title="Click to open Street-Level Cross-Section Simulator"
          >
            <span>
              Probe: [{selectedProbeCell.row}, {selectedProbeCell.col}] &middot;{' '}
              {getCellLatLon(selectedProbeCell.row, selectedProbeCell.col).lat.toFixed(3)}&deg;N
            </span>
            <Camera className="w-3 h-3 text-sky-600 ml-1" />
          </div>
        ) : (
          <div
            onClick={() => setIsStreetViewOpen(true)}
            className="absolute top-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2.5 py-1 text-[11px] text-slate-700 font-mono shadow-xs cursor-pointer hover:bg-slate-50 transition z-10"
            title="Click to open Ground-Level Cross-Section Simulator"
          >
            Click street to inspect &middot; <span className="text-sky-600 font-medium">Ground Level &rarr;</span>
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

      {/* Street-Level Cross-Section Simulator & Google Street View Modal */}
      {isStreetViewOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-5 shadow-2xl flex flex-col gap-4 max-h-[92vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-sky-50 text-sky-600 border border-sky-100">
                  <Camera className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    Street-Level Cross-Section Simulator
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    Marathahalli–Bellandur ORR • Cell [{activeStreetCell.row}, {activeStreetCell.col}] • {activeStreetCell.lat.toFixed(4)}°N, {activeStreetCell.lon.toFixed(4)}°E
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsStreetViewOpen(false)}
                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition"
                title="Close Simulator"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* GPS Location & Live Depth Diagnostics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono font-semibold">Latitude</span>
                <p className="text-sm font-bold text-slate-900 font-mono">{activeStreetCell.lat.toFixed(5)}° N</p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono font-semibold">Longitude</span>
                <p className="text-sm font-bold text-slate-900 font-mono">{activeStreetCell.lon.toFixed(5)}° E</p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono font-semibold">Ground Elevation</span>
                <p className="text-sm font-bold text-sky-700 font-mono">
                  {activeStreetCell.elevation.toFixed(1)} m DEM
                </p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono font-semibold">Simulated Flood Depth</span>
                <p className="text-sm font-bold text-sky-600 font-mono">
                  {(activeStreetCell.depth * 100).toFixed(1)} cm ({activeStreetCell.depth.toFixed(3)} m)
                </p>
              </div>
            </div>

            {/* Dynamic Street Cross-Section Cutaway Simulation */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col gap-3 relative overflow-hidden shadow-sm">
              <div className="flex items-center justify-between text-xs font-bold border-b border-slate-200 pb-2.5">
                <span className="flex items-center gap-2 text-slate-800">
                  <Waves className="w-4 h-4 text-sky-600" />
                  <span>Dynamic Hydraulic Cutaway (Water Level vs. Vehicles &amp; Pedestrians)</span>
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono tracking-tight ${
                    activeStreetCell.depth >= 1.0
                      ? 'bg-rose-100 text-rose-800 border border-rose-300'
                      : activeStreetCell.depth >= 0.6
                      ? 'bg-red-100 text-red-800 border border-red-300'
                      : activeStreetCell.depth >= 0.3
                      ? 'bg-amber-100 text-amber-900 border border-amber-300'
                      : activeStreetCell.depth >= 0.15
                      ? 'bg-sky-100 text-sky-800 border border-sky-300'
                      : activeStreetCell.depth >= 0.05
                      ? 'bg-cyan-100 text-cyan-800 border border-cyan-300'
                      : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  }`}
                >
                  {activeStreetCell.depth >= 1.0
                    ? 'ROOF SUBMERGED (100cm+)'
                    : activeStreetCell.depth >= 0.6
                    ? 'INTAKE FLOODED (60cm+)'
                    : activeStreetCell.depth >= 0.3
                    ? 'EXHAUST SUBMERGED (30cm+)'
                    : activeStreetCell.depth >= 0.15
                    ? 'SIDEWALK BREACHED (15cm+)'
                    : activeStreetCell.depth >= 0.05
                    ? 'SHALLOW SHEET FLOW'
                    : 'DRY PAVEMENT'}
                </span>
              </div>

              {/* SVG Urban Street Cross-Section Graphic */}
              <div className="relative h-56 w-full bg-gradient-to-b from-sky-50 via-sky-50/40 to-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-inner">
                {/* Background Urban Skylines */}
                <svg className="absolute inset-0 w-full h-full opacity-30" preserveAspectRatio="none">
                  <rect x="5%" y="40%" width="12%" height="60%" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
                  <rect x="20%" y="25%" width="15%" height="75%" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
                  <rect x="40%" y="45%" width="10%" height="55%" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
                  <rect x="55%" y="30%" width="16%" height="70%" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
                  <rect x="75%" y="38%" width="14%" height="62%" fill="#cbd5e1" stroke="#94a3b8" strokeWidth="0.5" />
                </svg>

                {/* Horizontal Guide Lines across Graphic */}
                <div className="absolute inset-x-0 bottom-[142px] border-b border-dashed border-rose-300/60 pointer-events-none" />
                <div className="absolute inset-x-0 bottom-[98px] border-b border-dashed border-orange-300/60 pointer-events-none" />
                <div className="absolute inset-x-0 bottom-[65px] border-b border-dashed border-amber-300/60 pointer-events-none" />
                <div className="absolute inset-x-0 bottom-[48px] border-b border-dashed border-sky-300/60 pointer-events-none" />

                {/* Sidewalk & Concrete Curb (Left side, exactly 15cm scale curb) */}
                <div className="absolute bottom-0 left-0 w-32 h-14 bg-gradient-to-b from-slate-200 to-slate-300 border-t-2 border-r-2 border-slate-400 z-10 flex flex-col items-center justify-center shadow-xs">
                  <span className="text-[10px] text-slate-800 font-mono font-bold">Sidewalk</span>
                  <span className="text-[9px] text-sky-800 font-mono font-semibold">15cm Curb</span>
                </div>

                {/* Asphalt Road Surface */}
                <div className="absolute bottom-0 left-32 right-0 h-8 bg-gradient-to-b from-slate-700 to-slate-800 border-t-2 border-slate-900 flex items-center justify-around z-10 shadow-inner">
                  <div className="w-10 h-1 bg-amber-400 rounded-full shadow-xs" />
                  <div className="w-10 h-1 bg-amber-400 rounded-full shadow-xs" />
                  <div className="w-10 h-1 bg-amber-400 rounded-full shadow-xs" />
                  <div className="w-10 h-1 bg-amber-400 rounded-full shadow-xs" />
                </div>

                {/* Vehicle Silhouette (sitting on asphalt road) */}
                <div className="absolute bottom-8 left-48 z-15 w-44 h-24 pointer-events-none">
                  <svg viewBox="0 0 160 80" className="w-full h-full drop-shadow-md">
                    {/* Car Chassis */}
                    <path
                      d="M 15 52 L 25 36 L 56 26 L 105 26 L 126 36 L 148 44 L 152 60 L 138 60 A 12 12 0 0 1 114 60 L 52 60 A 12 12 0 0 1 28 60 L 10 60 Z"
                      fill="#0284c7"
                      stroke="#0369a1"
                      strokeWidth="1.5"
                    />
                    {/* Windows */}
                    <path d="M 58 29 L 80 29 L 80 46 L 39 46 Z" fill="#e0f2fe" stroke="#38bdf8" strokeWidth="1" />
                    <path d="M 85 29 L 104 29 L 121 46 L 85 46 Z" fill="#e0f2fe" stroke="#38bdf8" strokeWidth="1" />
                    {/* Headlight & Taillight */}
                    <path d="M 148 48 L 152 52 L 148 54 Z" fill="#fef08a" />
                    <path d="M 15 48 L 12 52 L 15 54 Z" fill="#ef4444" />
                    {/* Wheels */}
                    <circle cx="40" cy="60" r="12" fill="#1e293b" stroke="#475569" strokeWidth="2" />
                    <circle cx="126" cy="60" r="12" fill="#1e293b" stroke="#475569" strokeWidth="2" />
                    <circle cx="40" cy="60" r="4.5" fill="#cbd5e1" />
                    <circle cx="126" cy="60" r="4.5" fill="#cbd5e1" />
                  </svg>
                </div>

                {/* Dynamic Water Layer */}
                {activeStreetCell.depth > 0 && (
                  <div
                    className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-sky-600/70 via-sky-400/55 to-cyan-300/40 z-20 transition-all duration-300 border-t-2 border-cyan-400 backdrop-blur-[0.5px]"
                    style={{
                      height: `${Math.min(
                        180,
                        Math.max(8, (activeStreetCell.depth / 1.0) * 110 + 32)
                      )}px`,
                    }}
                  >
                    {/* Surface ripple */}
                    <div className="w-full h-1 bg-white/70 animate-pulse" />
                    <div className="px-3 pt-1.5 flex justify-between items-center text-[11px] font-mono font-bold text-sky-950">
                      <span className="bg-white/90 backdrop-blur px-2 py-0.5 rounded-full border border-sky-300 shadow-2xs">
                        Simulated Water: {(activeStreetCell.depth * 100).toFixed(1)} cm
                      </span>
                      <span className="bg-white/90 backdrop-blur px-2 py-0.5 rounded-full border border-sky-300 shadow-2xs">
                        h = {activeStreetCell.depth.toFixed(3)} m
                      </span>
                    </div>
                  </div>
                )}

                {/* Water Height Reference Markers on Right Edge */}
                <div className="absolute right-2.5 bottom-8 top-3 flex flex-col justify-between text-[10px] font-mono border-l-2 border-dashed border-slate-300 pl-2 z-30 pointer-events-none">
                  <span className="text-rose-700 font-bold bg-white/95 px-1.5 py-0.5 rounded border border-rose-200 shadow-2xs">100cm (Roof)</span>
                  <span className="text-red-700 font-bold bg-white/95 px-1.5 py-0.5 rounded border border-red-200 shadow-2xs">60cm (Intake)</span>
                  <span className="text-amber-700 font-bold bg-white/95 px-1.5 py-0.5 rounded border border-amber-200 shadow-2xs">30cm (Exhaust)</span>
                  <span className="text-sky-700 font-bold bg-white/95 px-1.5 py-0.5 rounded border border-sky-200 shadow-2xs">15cm (Sidewalk)</span>
                  <span className="text-slate-600 font-bold bg-white/95 px-1.5 py-0.5 rounded border border-slate-200 shadow-2xs">0cm (Road)</span>
                </div>
              </div>

              {/* Dynamic Physical Guidance Message */}
              <div
                className={`text-xs flex items-start gap-2.5 p-3 rounded-xl border transition shadow-2xs ${
                  activeStreetCell.depth >= 0.6
                    ? 'bg-rose-50 border-rose-200 text-rose-950'
                    : activeStreetCell.depth >= 0.3
                    ? 'bg-amber-50 border-amber-200 text-amber-950'
                    : activeStreetCell.depth >= 0.15
                    ? 'bg-sky-50 border-sky-200 text-sky-950'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-950'
                }`}
              >
                <AlertTriangle
                  className={`w-4 h-4 shrink-0 mt-0.5 ${
                    activeStreetCell.depth >= 0.6
                      ? 'text-rose-600'
                      : activeStreetCell.depth >= 0.3
                      ? 'text-amber-600'
                      : activeStreetCell.depth >= 0.15
                      ? 'text-sky-600'
                      : 'text-emerald-600'
                  }`}
                />
                <div>
                  <span className="font-bold">
                    {activeStreetCell.depth >= 0.6
                      ? 'Engine Air Intake Submerged (Catastrophic Failure): '
                      : activeStreetCell.depth >= 0.3
                      ? 'Vehicle Exhaust Submerged (Engine Stalling): '
                      : activeStreetCell.depth >= 0.15
                      ? 'Sidewalk Curb Breached (Pedestrian & Travel Hazard): '
                      : 'Street Traversible: '}
                  </span>
                  <span className="opacity-90">
                    {activeStreetCell.depth >= 1.0
                      ? 'Water level exceeds 100 cm (roof level). Vehicles completely submerged. Severe life-safety emergency; evacuation directive active.'
                      : activeStreetCell.depth >= 0.6
                      ? 'Water level exceeds 60 cm (air intake height). Water enters engine air intake causing immediate hydraulic lock (catastrophic engine failure). Street impassable to all standard vehicles.'
                      : activeStreetCell.depth >= 0.3
                      ? 'Water level exceeds 30 cm (average vehicle exhaust height). Backpressure enters exhaust tailpipes causing engines to flood and stall.'
                      : activeStreetCell.depth >= 0.15
                      ? 'Water exceeds 15 cm (raised concrete sidewalk curb). Walking on sidewalks becomes hazardous; high hydroplaning risk for two-wheelers and sedans.'
                      : 'Water depth is beneath the 15 cm sidewalk curb. Street traffic can proceed with reduced speed.'}
                  </span>
                </div>
              </div>
            </div>

            {/* Term Reference & Engineering Purpose Table */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                <Info className="w-4 h-4 text-sky-600" />
                <span>Street-Level Thresholds &amp; Technical Purpose</span>
              </div>
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold font-mono text-[11px]">
                    <tr>
                      <th className="py-2 px-3">Threshold</th>
                      <th className="py-2 px-3">Physical Height</th>
                      <th className="py-2 px-3">What It Means &amp; Engineering Purpose</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    <tr className={activeStreetCell.depth >= 0.15 && activeStreetCell.depth < 0.3 ? 'bg-amber-50/70 font-medium' : ''}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0" />
                        Sidewalk
                      </td>
                      <td className="py-2.5 px-3 font-mono font-bold text-sky-700">15 cm</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        The raised concrete pedestrian curb (15 cm). Once water rises past this line, walking on sidewalks becomes hazardous.
                      </td>
                    </tr>
                    <tr className={activeStreetCell.depth >= 0.3 && activeStreetCell.depth < 0.6 ? 'bg-orange-50/70 font-medium' : ''}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0" />
                        Exhaust
                      </td>
                      <td className="py-2.5 px-3 font-mono font-bold text-amber-700">30 cm</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        Average vehicle exhaust height. If water reaches this height, backpressure can flood the exhaust and stall the engine.
                      </td>
                    </tr>
                    <tr className={activeStreetCell.depth >= 0.6 && activeStreetCell.depth < 1.0 ? 'bg-red-50/70 font-medium' : ''}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-orange-500 shrink-0" />
                        Intake
                      </td>
                      <td className="py-2.5 px-3 font-mono font-bold text-orange-700">60 cm</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        Engine air intake height. If water enters the air intake, the engine suffers hydraulic lock (catastrophic failure).
                      </td>
                    </tr>
                    <tr className={activeStreetCell.depth >= 1.0 ? 'bg-rose-50/70 font-medium' : ''}>
                      <td className="py-2.5 px-3 font-semibold text-slate-900 flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0" />
                        Roof
                      </td>
                      <td className="py-2.5 px-3 font-mono font-bold text-rose-700">100 cm+</td>
                      <td className="py-2.5 px-3 text-slate-600">
                        Severe deluge level where vehicles are partially or completely submerged.
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Action Buttons: Google Street View (360° Panorama) & Google Maps */}
            <div className="flex flex-col gap-2 pt-1 border-t border-slate-200">
              <div className="flex flex-col sm:flex-row gap-2.5">
                <a
                  href={googleStreetViewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-700 hover:to-blue-700 text-white font-semibold text-xs shadow-md transition"
                >
                  <Camera className="w-4 h-4" />
                  <span>Google Street View (360° Panorama)</span>
                  <ExternalLink className="w-3.5 h-3.5 ml-1" />
                </a>

                <a
                  href={googleMapsSearchUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs border border-slate-200 transition"
                >
                  <Navigation className="w-4 h-4 text-emerald-600" />
                  <span>View in Google Maps</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
              <p className="text-[11px] text-slate-500 text-center">
                Directly launches the live 360-degree Google Street View at this precise latitude and longitude so officials can visually cross-check trees, gutters, and low-lying walls.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

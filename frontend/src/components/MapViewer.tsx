import React, { useRef, useEffect, useState, useMemo } from 'react';
import {
  Compass,
  Layers,
  Download,
  MapPin,
  Loader2,
  Camera,
  ExternalLink,
  X,
  Map as MapIcon,
  Navigation,
  AlertTriangle,
  Waves,
  Box,
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
  isSolverComparison = false,
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
  const [basemapMode, setBasemapMode] = useState<'streets' | 'satellite' | 'topo'>('streets');
  const [viewAngle, setViewAngle] = useState<'2d' | '3d'>('2d');
  const show3DBuildings = true;
  const [isStreetViewOpen, setIsStreetViewOpen] = useState<boolean>(false);
  const [imagesLoaded, setImagesLoaded] = useState<boolean>(false);

  const streetsImgRef = useRef<HTMLImageElement | null>(null);
  const satImgRef = useRef<HTMLImageElement | null>(null);
  const topoImgRef = useRef<HTMLImageElement | null>(null);

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
      if (loadedCount >= 3) {
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

    const topo = new Image();
    topo.src = '/basemap_topo.png';
    topo.onload = () => {
      topoImgRef.current = topo;
      checkLoaded();
    };
    topo.onerror = () => checkLoaded();
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

  // Urban 3D building footprints for Marathahalli-Bellandur corridor
  const urbanBuildings = useMemo(() => {
    // Generate deterministic urban building blocks aligned to non-flooding high-ground parcels
    const list: Array<{ r: number; c: number; w: number; h: number; height: number }> = [];
    const seed = 42;
    for (let r = 8; r < 56; r += 6) {
      for (let c = 8; c < 56; c += 6) {
        // Skip lake lowlands in south-east
        if (r > 38 && c > 36) continue;
        const pseudo = ((r * 13 + c * 37 + seed) % 100) / 100;
        if (pseudo > 0.35) {
          list.push({
            r: r + Math.floor(pseudo * 2),
            c: c + Math.floor(pseudo * 2),
            w: 2 + Math.floor(pseudo * 2.5),
            h: 2 + Math.floor(pseudo * 2.5),
            height: 12 + Math.floor(pseudo * 24), // building height in meters
          });
        }
      }
    }
    return list;
  }, []);

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
      ctx.fillStyle = 'rgba(15, 23, 42, 0.10)';
      ctx.fillRect(0, 0, width, height);
    } else if (basemapMode === 'satellite' && satImgRef.current) {
      ctx.drawImage(satImgRef.current, 0, 0, width, height);
      ctx.fillStyle = 'rgba(15, 23, 42, 0.15)';
      ctx.fillRect(0, 0, width, height);
    } else if (basemapMode === 'topo' && topoImgRef.current) {
      ctx.drawImage(topoImgRef.current, 0, 0, width, height);
    } else {
      // Fallback procedural elevation relief
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const elev = terrain.elevation[r]?.[c] ?? 880;
          const normElev = Math.max(0, Math.min(1, (elev - minElev) / Math.max(1, maxElev - minElev)));
          // Emerald to ochre hypsometric tint
          const red = Math.floor(34 + normElev * 140);
          const green = Math.floor(110 + normElev * 40);
          const blue = Math.floor(70 + normElev * 20);
          ctx.fillStyle = `rgb(${red}, ${green}, ${blue})`;
          ctx.fillRect(c * cellW, r * cellH, cellW + 0.5, cellH + 0.5);
        }
      }
    }

    // Composite hillshade relief under water so terrain topography reads clearly
    if (cachedHillshadeRef.current) {
      ctx.save();
      ctx.globalAlpha = 0.22;
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

    // 3. 3D Extruded Urban Building Blocks (matching 3D isometric perspective reference)
    if (show3DBuildings && viewAngle === '3d') {
      ctx.save();
      for (const b of urbanBuildings) {
        const bx = b.c * cellW;
        const by = b.r * cellH;
        const bw = b.w * cellW;
        const bh = b.h * cellH;
        const hOffset = Math.min(28, (b.height / 30) * 16);

        // Building shadow
        ctx.fillStyle = 'rgba(15, 23, 42, 0.35)';
        ctx.fillRect(bx + 4, by + 4, bw, bh);

        // Building Walls (isometric extrusion south & east)
        ctx.fillStyle = '#cbd5e1'; // light slate wall
        ctx.beginPath();
        ctx.moveTo(bx, by + bh);
        ctx.lineTo(bx + bw, by + bh);
        ctx.lineTo(bx + bw, by + bh + hOffset * 0.5);
        ctx.lineTo(bx, by + bh + hOffset * 0.5);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Building Rooftop (white block with dark contour, matching reference image)
        ctx.fillStyle = '#f8fafc';
        ctx.fillRect(bx, by - hOffset * 0.5, bw, bh);
        ctx.strokeStyle = '#334155';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(bx, by - hOffset * 0.5, bw, bh);
      }
      ctx.restore();
    }

    // 4. Optional Grid Lines
    if (showGrid) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
      ctx.lineWidth = 0.75;
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          ctx.strokeRect(c * cellW, r * cellH, cellW, cellH);
        }
      }
    }

    // 5. Active Probe Pin Marker
    if (selectedProbeCell) {
      const pinX = (selectedProbeCell.col + 0.5) * cellW;
      const pinY = (selectedProbeCell.row + 0.5) * cellH;

      ctx.save();
      ctx.beginPath();
      ctx.arc(pinX, pinY, 10, 0, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(34, 211, 238, 0.95)';
      ctx.lineWidth = 2.5;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(pinX, pinY, 4.5, 0, 2 * Math.PI);
      ctx.fillStyle = '#06b6d4';
      ctx.shadowColor = '#22d3ee';
      ctx.shadowBlur = 14;
      ctx.fill();
      ctx.restore();
    }
  }, [
    terrain,
    depthFrame,
    rows,
    cols,
    minElev,
    maxElev,
    showGrid,
    basemapMode,
    viewAngle,
    show3DBuildings,
    imagesLoaded,
    selectedProbeCell,
    urbanBuildings,
  ]);

  // Cell Coordinates Calculation
  const getCellLatLon = (r: number, c: number) => {
    const lat = maxLat - ((r + 0.5) / rows) * (maxLat - minLat);
    const lon = minLon + ((c + 0.5) / cols) * (maxLon - minLon);
    return { lat, lon };
  };

  // Active cell for Street View (either selected probe cell or center ORR)
  const activeStreetCell = useMemo(() => {
    const r = selectedProbeCell?.row ?? 32;
    const c = selectedProbeCell?.col ?? 32;
    const { lat, lon } = getCellLatLon(r, c);
    const depth = depthFrame?.[r]?.[c] ?? 0;
    const elevation = terrain?.elevation[r]?.[c] ?? 878;
    return { row: r, col: c, lat, lon, depth, elevation };
  }, [selectedProbeCell, depthFrame, terrain, rows, cols]);

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

  // Google Street View 360 link for current coordinate
  const googleStreetViewUrl = `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=${activeStreetCell.lat.toFixed(6)},${activeStreetCell.lon.toFixed(6)}`;
  const googleMapsSearchUrl = `https://www.google.com/maps/search/?api=1&query=${activeStreetCell.lat.toFixed(6)},${activeStreetCell.lon.toFixed(6)}`;

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-3 relative overflow-hidden text-slate-900">
      {/* Top Map Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isSolverComparison ? 'bg-amber-500' : 'bg-brand-500 animate-pulse'
            }`}
          />
          <h3 className="text-sm font-bold text-slate-900 tracking-wide">{title}</h3>
          <span className="text-[10px] text-slate-500 font-mono px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
            {terrain?.dx_m ?? 60.9}m/cell • Marathahalli-Bellandur ORR
          </span>
        </div>

        {/* Basemap Switcher & Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* 2D Plan vs 3D Oblique Perspective Toggle (matching reference image) */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
            <button
              onClick={() => setViewAngle('2d')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                viewAngle === '2d'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="2D Top-Down Plan View"
            >
              <span>2D Map</span>
            </button>
            <button
              onClick={() => setViewAngle('3d')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                viewAngle === '3d'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="3D Oblique Urban Street Perspective"
            >
              <Box className="w-3.5 h-3.5" />
              <span>3D Street View</span>
            </button>
          </div>

          {/* Basemap Toggle Group (Streets, Satellite, Topo) */}
          <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
            <button
              onClick={() => setBasemapMode('streets')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                basemapMode === 'streets'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Real Esri / OSM Labeled Street Network (No API key needed)"
            >
              <MapIcon className="w-3 h-3" />
              <span>Streets</span>
            </button>
            <button
              onClick={() => setBasemapMode('satellite')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                basemapMode === 'satellite'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Real Satellite Aerial Photography"
            >
              <span>Satellite</span>
            </button>
            <button
              onClick={() => setBasemapMode('topo')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                basemapMode === 'topo'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
              title="Hillshaded Digital Elevation Topography"
            >
              <span>Topo</span>
            </button>
          </div>

          {/* Real Street View Simulator Modal Launcher */}
          <button
            onClick={() => setIsStreetViewOpen(true)}
            className="px-2.5 py-1.5 rounded-lg bg-cyan-50 border border-cyan-200 hover:bg-cyan-100 text-cyan-800 text-xs font-semibold flex items-center gap-1.5 transition shadow-xs"
            title="Open Street-Level Flood Simulator"
          >
            <Camera className="w-3.5 h-3.5 text-cyan-600" />
            <span className="hidden sm:inline">Ground Level</span>
          </button>

          {/* Indicative Flow Vectors Toggle */}
          <button
            onClick={() => setShowFlowVectors(!showFlowVectors)}
            className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 text-xs ${
              showFlowVectors
                ? 'bg-cyan-50 text-cyan-800 border border-cyan-200'
                : 'text-slate-600 hover:text-slate-900'
            }`}
            title="Toggle Indicative Flow Direction (Water Surface Gradient)"
          >
            <Navigation className="w-3 h-3 rotate-45 text-cyan-600" />
            <span className="hidden sm:inline">Flow Vectors</span>
          </button>

          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition ${
              showGrid
                ? 'bg-slate-200 text-slate-900 border-slate-300'
                : 'bg-slate-100 text-slate-600 border-slate-200 hover:text-slate-900 hover:bg-slate-200'
            }`}
            title="Toggle grid mesh overlay"
          >
            <Layers className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleDownloadSnapshot}
            className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 hover:bg-slate-200 text-slate-600 hover:text-slate-900 text-xs flex items-center gap-1 transition"
            title="Export high-res snapshot PNG"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Map Perspective View Container (Supports 3D Oblique Tilt) */}
      <div
        className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-100 border border-slate-200 flex items-center justify-center transition-all duration-500"
        style={{
          perspective: viewAngle === '3d' ? '1200px' : 'none',
        }}
      >
        <div
          className="w-full h-full flex items-center justify-center transition-transform duration-500 origin-center"
          style={{
            transform:
              viewAngle === '3d'
                ? 'rotateX(42deg) rotateZ(-12deg) scale(0.92) translateY(10px)'
                : 'none',
            boxShadow:
              viewAngle === '3d'
                ? '0 20px 40px -10px rgba(0, 0, 0, 0.2), 0 10px 20px -10px rgba(0, 0, 0, 0.15)'
                : 'none',
          }}
        >
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
        </div>

        {/* Loading Overlay when rolling out inference */}
        {isLoading && (
          <div className="absolute inset-0 bg-white/40 backdrop-blur-[1px] flex items-center justify-center pointer-events-none z-20">
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-full bg-white/95 border border-brand-200 text-brand-700 text-xs font-semibold shadow-xl">
              <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
              <span>Simulating surrogate...</span>
            </div>
          </div>
        )}

        {/* North Arrow Indicator */}
        <div className="absolute top-3 right-3 p-1.5 rounded-xl bg-white/90 backdrop-blur border border-slate-200 shadow-sm flex flex-col items-center pointer-events-none z-10">
          <Compass className="w-4 h-4 text-cyan-600" />
          <span className="text-[9px] font-bold text-slate-700 font-mono">N</span>
        </div>

        {/* Perspective Badge */}
        {viewAngle === '3d' && (
          <div className="absolute top-3 right-12 bg-white/90 backdrop-blur border border-brand-200 rounded-lg px-2.5 py-1 text-[10px] font-semibold text-brand-700 font-mono shadow-sm pointer-events-none z-10 flex items-center gap-1.5">
            <Box className="w-3 h-3 text-brand-600" />
            <span>3D Oblique Urban View</span>
          </div>
        )}

        {/* Indicative Flow Direction Overlay Pill */}
        {showFlowVectors && (
          <div className="absolute top-3 right-3 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2 py-0.5 text-[10px] text-cyan-800 font-mono shadow-sm pointer-events-none z-10 flex items-center gap-1">
            <Navigation className="w-2.5 h-2.5 rotate-45 text-cyan-600" />
            <span>Indicative flow direction</span>
          </div>
        )}

        {/* Selected Probe Badge with Street View trigger */}
        {selectedProbeCell ? (
          <div
            onClick={() => setIsStreetViewOpen(true)}
            className="absolute top-3 left-3 bg-white/95 backdrop-blur border border-cyan-300 rounded-lg px-2.5 py-1 text-[11px] text-cyan-800 font-mono shadow-md flex items-center gap-1.5 z-10 cursor-pointer hover:bg-cyan-50 transition"
            title="Click to view Street View at probe"
          >
            <MapPin className="w-3.5 h-3.5 text-cyan-600" />
            <span>
              Probe: [{selectedProbeCell.row}, {selectedProbeCell.col}] • {activeStreetCell.lat.toFixed(4)}°N
            </span>
            <Camera className="w-3 h-3 text-cyan-600 ml-1" />
          </div>
        ) : (
          <div className="absolute top-3 left-3 bg-white/90 backdrop-blur border border-slate-200 rounded-lg px-2 py-0.5 text-[10px] text-slate-600 font-mono shadow-sm pointer-events-none z-10">
            🗺️ Click street to inspect water depth
          </div>
        )}

        {/* Live Hover Inspector Overlay */}
        {hoverCell && (
          <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur border border-slate-200 rounded-xl px-3 py-2 text-xs shadow-xl font-mono flex flex-col gap-0.5 pointer-events-none z-10 text-slate-800">
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
        <div className="h-2.5 w-full rounded-full overflow-hidden flex shadow-inner border border-slate-200">
          <div className="w-[8%] bg-slate-200" title="Dry pavement (< 0.01m / 1cm)" />
          <div className="w-[22%] bg-gradient-to-r from-sky-400 to-cyan-500" title="1cm - 15cm (Thin sheet flow)" />
          <div className="w-[35%] bg-gradient-to-r from-cyan-500 to-blue-600" title="15cm - 60cm (Street curb overflow)" />
          <div className="w-[35%] bg-gradient-to-r from-blue-600 to-indigo-950" title="60cm - 2.0m+ (Deep deluge)" />
        </div>
        <div className="flex justify-between text-[10px] text-slate-500 font-mono">
          <span>Dry (&lt;1cm)</span>
          <span>5cm (Sheet flow)</span>
          <span>15cm (Curb breached)</span>
          <span>60cm (Vehicle hazard)</span>
          <span>2.0m+ (Deep deluge)</span>
        </div>
      </div>

      {/* Real Street View & Inundation Simulation Modal */}
      {isStreetViewOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-2xl max-w-2xl w-full p-5 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto text-slate-900">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-cyan-600" />
                <div>
                  <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                    Real Google Street View &amp; Flood Level Simulator
                  </h3>
                  <p className="text-xs text-slate-500 font-mono">
                    Marathahalli–Bellandur Outer Ring Road • Cell [{activeStreetCell.row},{' '}
                    {activeStreetCell.col}]
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsStreetViewOpen(false)}
                className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* GPS Location & Live Depth Diagnostics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Latitude</span>
                <p className="text-sm font-bold text-slate-900 font-mono">{activeStreetCell.lat.toFixed(5)}° N</p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Longitude</span>
                <p className="text-sm font-bold text-slate-900 font-mono">{activeStreetCell.lon.toFixed(5)}° E</p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Ground Elevation</span>
                <p className="text-sm font-bold text-cyan-700 font-mono">
                  {activeStreetCell.elevation.toFixed(2)} m
                </p>
              </div>
              <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <span className="text-[10px] text-slate-500 uppercase font-mono">Simulation Depth</span>
                <p className="text-sm font-bold text-cyan-700 font-mono">
                  {activeStreetCell.depth.toFixed(3)} m ({(activeStreetCell.depth * 100).toFixed(0)} cm)
                </p>
              </div>
            </div>

            {/* Street-Level Water Inundation Simulator Canvas / Graphic */}
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 flex flex-col gap-3 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-slate-700 font-semibold border-b border-slate-200 pb-2">
                <span className="flex items-center gap-1.5 text-cyan-700">
                  <Waves className="w-4 h-4" />
                  Street Cross-Section Simulation (Water Level vs. Vehicles)
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    activeStreetCell.depth >= 0.3
                      ? 'bg-rose-50 text-rose-700 border border-rose-200'
                      : activeStreetCell.depth >= 0.15
                      ? 'bg-amber-50 text-amber-800 border border-amber-200'
                      : activeStreetCell.depth >= 0.05
                      ? 'bg-cyan-50 text-cyan-700 border border-cyan-200'
                      : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  }`}
                >
                  {activeStreetCell.depth >= 0.6
                    ? 'CRITICAL DELUGE'
                    : activeStreetCell.depth >= 0.3
                    ? 'ROAD CUTOFF'
                    : activeStreetCell.depth >= 0.15
                    ? 'VEHICLE HAZARD'
                    : activeStreetCell.depth >= 0.05
                    ? 'SHALLOW POOL'
                    : 'DRY PAVEMENT'}
                </span>
              </div>

              {/* Dynamic Street Cross-Section SVG */}
              <div className="relative h-44 w-full bg-slate-100 rounded-lg overflow-hidden border border-slate-200 flex items-end">
                {/* Sky / Urban Backdrop */}
                <div className="absolute inset-0 bg-gradient-to-b from-sky-100 via-sky-50 to-slate-100" />

                {/* City skyline silhouettes */}
                <svg className="absolute inset-0 w-full h-full opacity-20" preserveAspectRatio="none">
                  <rect x="5%" y="45%" width="12%" height="55%" fill="#0284c7" />
                  <rect x="20%" y="30%" width="15%" height="70%" fill="#0284c7" />
                  <rect x="40%" y="50%" width="10%" height="50%" fill="#0284c7" />
                  <rect x="55%" y="35%" width="16%" height="65%" fill="#0284c7" />
                  <rect x="75%" y="40%" width="14%" height="60%" fill="#0284c7" />
                </svg>

                {/* Sidewalk & Concrete Curb (Left side, 15cm high) */}
                <div className="absolute bottom-0 left-0 w-28 h-10 bg-slate-300 border-t-2 border-r-2 border-slate-400 z-10 flex items-center justify-center">
                  <span className="text-[9px] text-slate-700 font-mono font-bold">Sidewalk (15cm)</span>
                </div>

                {/* Asphalt Road Surface */}
                <div className="absolute bottom-0 left-28 right-0 h-6 bg-slate-800 border-t-2 border-slate-600 flex items-center justify-around z-10">
                  <div className="w-8 h-1 bg-amber-400" />
                  <div className="w-8 h-1 bg-amber-400" />
                  <div className="w-8 h-1 bg-amber-400" />
                  <div className="w-8 h-1 bg-amber-400" />
                </div>

                {/* Car Silhouette (placed on the street) */}
                <div className="absolute bottom-6 left-48 z-15 w-40 h-20 pointer-events-none">
                  <svg viewBox="0 0 160 80" className="w-full h-full drop-shadow-md">
                    {/* Car Body */}
                    <path
                      d="M 15 50 L 25 35 L 55 25 L 105 25 L 125 35 L 148 42 L 152 58 L 138 58 A 12 12 0 0 1 114 58 L 52 58 A 12 12 0 0 1 28 58 L 10 58 Z"
                      fill="#0284c7"
                    />
                    {/* Windows */}
                    <path d="M 57 28 L 80 28 L 80 44 L 38 44 Z" fill="#e0f2fe" opacity="0.9" />
                    <path d="M 85 28 L 104 28 L 120 44 L 85 44 Z" fill="#e0f2fe" opacity="0.9" />
                    {/* Wheels */}
                    <circle cx="40" cy="58" r="11" fill="#1e293b" stroke="#64748b" strokeWidth="2" />
                    <circle cx="126" cy="58" r="11" fill="#1e293b" stroke="#64748b" strokeWidth="2" />
                    <circle cx="40" cy="58" r="4" fill="#94a3b8" />
                    <circle cx="126" cy="58" r="4" fill="#94a3b8" />
                  </svg>
                </div>

                {/* Dynamic Flood Water Layer */}
                {activeStreetCell.depth > 0 && (
                  <div
                    className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-blue-600/80 via-cyan-500/70 to-cyan-300/60 z-20 transition-all duration-300 border-t-2 border-cyan-200"
                    style={{
                      height: `${Math.min(
                        140,
                        Math.max(6, (activeStreetCell.depth / 1.0) * 80 + 24)
                      )}px`,
                    }}
                  >
                    {/* Water Surface Ripples */}
                    <div className="w-full h-1 bg-white/50 animate-pulse" />
                    <div className="px-3 pt-1 flex justify-between items-center text-[10px] font-mono font-bold text-white drop-shadow">
                      <span>Simulated Water: {(activeStreetCell.depth * 100).toFixed(0)} cm</span>
                      <span>h = {activeStreetCell.depth.toFixed(3)} m</span>
                    </div>
                  </div>
                )}

                {/* Water Height Reference Markers */}
                <div className="absolute right-2 bottom-6 top-4 flex flex-col justify-between text-[9px] font-mono text-slate-500 border-l border-dashed border-slate-300 pl-1 z-30 pointer-events-none">
                  <span className="text-rose-600 font-bold">100cm (Roof)</span>
                  <span className="text-amber-600 font-bold">60cm (Intake)</span>
                  <span className="text-amber-700 font-bold">30cm (Exhaust)</span>
                  <span className="text-cyan-700 font-bold">15cm (Curb)</span>
                  <span className="text-slate-500">0cm (Road)</span>
                </div>
              </div>

              {/* Physical Hazard Guidance Message */}
              <div className="text-xs text-slate-700 flex items-start gap-2 bg-white p-2.5 rounded-lg border border-slate-200 shadow-xs">
                <AlertTriangle
                  className={`w-4 h-4 shrink-0 mt-0.5 ${
                    activeStreetCell.depth >= 0.3
                      ? 'text-rose-600'
                      : activeStreetCell.depth >= 0.15
                      ? 'text-amber-600'
                      : 'text-cyan-600'
                  }`}
                />
                <div>
                  <span className="font-bold text-slate-900">
                    {activeStreetCell.depth >= 0.3
                      ? 'Severe Road Inundation — Structural Danger: '
                      : activeStreetCell.depth >= 0.15
                      ? 'Vehicle Travel Warning: '
                      : 'Street Traversible: '}
                  </span>
                  {activeStreetCell.depth >= 0.6
                    ? 'Water level exceeds 60 cm. Street impassable to all emergency access vehicles. Ground-floor structural inundation expected.'
                    : activeStreetCell.depth >= 0.3
                    ? 'Water has reached 30 cm, entering typical vehicle exhaust tailpipes and air intakes. Standard sedans will stall.'
                    : activeStreetCell.depth >= 0.15
                    ? 'Water has breached the 15 cm concrete road curb and is entering wheel hubs. High hydroplaning hazard.'
                    : 'Water depth is beneath curb height. Street traffic can proceed with reduced speed.'}
                </div>
              </div>
            </div>

            {/* Google Street View 360 & Google Maps Launch Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <a
                href={googleStreetViewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs shadow-md shadow-cyan-600/20 transition"
              >
                <Camera className="w-4 h-4" />
                <span>Open in Google Street View (360° Panorama)</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </a>

              <a
                href={googleMapsSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-xs border border-slate-200 transition"
              >
                <Navigation className="w-4 h-4 text-emerald-600" />
                <span>View on Google Maps</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

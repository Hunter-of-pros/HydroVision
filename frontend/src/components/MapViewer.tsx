import React, { useRef, useEffect, useState, useMemo } from 'react';
import { Compass, Layers, Download, MapPin } from 'lucide-react';
import { TerrainData } from '../types';

interface MapViewerProps {
  terrain: TerrainData | null;
  depthFrame: number[][] | null; // 64x64 depth in meters
  title?: string;
  isSolverComparison?: boolean;
  selectedProbeCell?: { row: number; col: number } | null;
  onSelectProbeCell?: (cell: { row: number; col: number; elevation: number } | null) => void;
  isMock?: boolean;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  terrain,
  depthFrame,
  title = 'Urban Flood Inundation Map',
  isSolverComparison = false,
  selectedProbeCell,
  onSelectProbeCell,
  isMock = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoverCell, setHoverCell] = useState<{
    row: number;
    col: number;
    elevation: number;
    depth: number;
  } | null>(null);

  const [showGrid, setShowGrid] = useState<boolean>(false);
  const smoothInterpolation = true;

  const rows = terrain?.shape[0] || 64;
  const cols = terrain?.shape[1] || 64;

  // Precompute min/max terrain elevation
  const { minElev, maxElev } = useMemo(() => {
    if (!terrain) return { minElev: 80, maxElev: 100 };
    return {
      minElev: terrain.min_elevation,
      maxElev: terrain.max_elevation,
    };
  }, [terrain]);

  // Render raster cells on canvas whenever depthFrame or terrain changes
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

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const elev = terrain.elevation[r]?.[c] ?? 90;
        const depth = depthFrame?.[r]?.[c] ?? 0;

        // Base terrain shading (topographic slope descending toward SE)
        const normElev = Math.max(0, Math.min(1, (elev - minElev) / Math.max(1, maxElev - minElev)));
        const terrainLum = Math.floor(18 + normElev * 28);
        let rColor = terrainLum;
        let gColor = terrainLum + 4;
        let bColor = terrainLum + 8;

        if (depth >= 0.05) {
          // Water inundation colormap
          const maxDepthDisplay = 2.0;
          const normDepth = Math.max(0, Math.min(1, depth / maxDepthDisplay));

          if (normDepth < 0.25) {
            // Shallow (0.05 - 0.5m): Electric cyan
            rColor = Math.floor(14 + (1 - normDepth) * 40);
            gColor = Math.floor(165 + normDepth * 50);
            bColor = Math.floor(233 + normDepth * 22);
          } else if (normDepth < 0.65) {
            // Moderate (0.5m - 1.3m): Royal blue
            rColor = Math.floor(2 + (1 - normDepth) * 30);
            gColor = Math.floor(132 - normDepth * 60);
            bColor = Math.floor(220 + normDepth * 35);
          } else {
            // Severe (> 1.3m): Deep indigo / navy
            rColor = Math.floor(67 - normDepth * 20);
            gColor = Math.floor(56 - normDepth * 20);
            bColor = Math.floor(202 + normDepth * 50);
          }
        }

        ctx.fillStyle = `rgb(${rColor}, ${gColor}, ${bColor})`;
        ctx.fillRect(c * cellW, r * cellH, cellW + (smoothInterpolation ? 0.5 : 0), cellH + (smoothInterpolation ? 0.5 : 0));

        if (showGrid) {
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
          ctx.strokeRect(c * cellW, r * cellH, cellW, cellH);
        }
      }
    }

    // Draw active probe pin marker if selected
    if (selectedProbeCell) {
      const pinX = (selectedProbeCell.col + 0.5) * cellW;
      const pinY = (selectedProbeCell.row + 0.5) * cellH;

      ctx.save();
      // Outer pulse ring
      ctx.beginPath();
      ctx.arc(pinX, pinY, 9, 0, 2 * Math.PI);
      ctx.strokeStyle = 'rgba(34, 211, 238, 0.8)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Inner glowing point
      ctx.beginPath();
      ctx.arc(pinX, pinY, 4, 0, 2 * Math.PI);
      ctx.fillStyle = '#06b6d4';
      ctx.shadowColor = '#22d3ee';
      ctx.shadowBlur = 10;
      ctx.fill();
      ctx.restore();
    }
  }, [terrain, depthFrame, rows, cols, minElev, maxElev, showGrid, smoothInterpolation, selectedProbeCell]);

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

    // Stamp visible "MOCK DATA" watermark on exported image when mock
    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width;
    exportCanvas.height = canvas.height;
    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    // Draw base map frame
    ctx.drawImage(canvas, 0, 0);

    // Diagonal semi-transparent watermark across center
    ctx.save();
    ctx.translate(exportCanvas.width / 2, exportCanvas.height / 2);
    ctx.rotate(-Math.PI / 6);
    ctx.font = '900 42px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Shadow
    ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
    ctx.fillText('MOCK DATA', 2, 2);

    // Main watermark text
    ctx.fillStyle = 'rgba(245, 158, 11, 0.85)';
    ctx.fillText('MOCK DATA', 0, 0);

    // Subtitle
    ctx.font = 'bold 16px sans-serif';
    ctx.fillStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.fillText('SIMULATED • NOT REAL RESULTS', 0, 36);
    ctx.restore();

    // Top-left prominent badge
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
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col gap-3 relative overflow-hidden">
      {/* Top Map Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isSolverComparison ? 'bg-amber-400' : 'bg-brand-400 animate-pulse'
            }`}
          />
          <h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>
          <span className="text-[10px] text-slate-400 font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
            64 x 64 ({terrain?.dx_m ?? 40}m/cell)
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition ${
              showGrid
                ? 'bg-slate-700 text-white border-slate-600'
                : 'bg-slate-800/80 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Toggle grid overlay"
          >
            <Layers className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Grid</span>
          </button>

          <button
            onClick={handleDownloadSnapshot}
            className="p-1.5 rounded-lg bg-slate-800/80 border border-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs flex items-center gap-1 transition"
            title="Export high-res snapshot PNG"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Canvas Map Container */}
      <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center">
        <canvas
          ref={canvasRef}
          width={512}
          height={512}
          onClick={handleCanvasClick}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="w-full h-full object-contain cursor-crosshair"
        />

        {/* North Arrow Indicator */}
        <div className="absolute top-3 right-3 p-1.5 rounded-xl bg-slate-900/80 backdrop-blur border border-slate-700/60 shadow flex flex-col items-center pointer-events-none">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span className="text-[9px] font-bold text-slate-300 font-mono">N</span>
        </div>

        {/* Selected Probe Badge */}
        {selectedProbeCell && (
          <div className="absolute top-3 left-3 bg-cyan-950/90 backdrop-blur border border-cyan-500/50 rounded-lg px-2.5 py-1 text-[11px] text-cyan-300 font-mono shadow flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-cyan-400" />
            <span>Probe: [{selectedProbeCell.row}, {selectedProbeCell.col}]</span>
          </div>
        )}

        {/* Live Hover Inspector Overlay */}
        {hoverCell && (
          <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur border border-slate-700/80 rounded-xl px-3 py-2 text-xs shadow-2xl font-mono flex flex-col gap-0.5 pointer-events-none">
            <div className="flex items-center justify-between gap-4 text-slate-400 text-[10px] border-b border-slate-800 pb-1">
              <span>Cell [{hoverCell.row}, {hoverCell.col}]</span>
              <span className={hoverCell.depth >= 0.05 ? 'text-cyan-400 font-bold' : 'text-slate-500'}>
                {hoverCell.depth >= 0.05 ? 'INUNDATED' : 'DRY'}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Ground Elev (z):</span>
              <span className="font-bold text-slate-200">{hoverCell.elevation.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Flood Depth (h):</span>
              <span className={`font-bold ${hoverCell.depth >= 0.05 ? 'text-cyan-300' : 'text-slate-400'}`}>
                {hoverCell.depth.toFixed(3)} m
              </span>
            </div>
            <div className="flex justify-between gap-4 text-[10px] text-slate-500 pt-0.5">
              <span>Water Surface (z+h):</span>
              <span>{(hoverCell.elevation + hoverCell.depth).toFixed(2)} m</span>
            </div>
          </div>
        )}
      </div>

      {/* Colormap Legend Scale */}
      <div className="flex flex-col gap-1.5 pt-1">
        <div className="h-2.5 w-full rounded-full overflow-hidden flex shadow-inner">
          <div className="w-[10%] bg-slate-800" title="Dry terrain (< 0.05m)" />
          <div className="w-[25%] bg-gradient-to-r from-sky-400 to-cyan-500" title="0.05m - 0.5m" />
          <div className="w-[35%] bg-gradient-to-r from-cyan-500 to-blue-600" title="0.5m - 1.2m" />
          <div className="w-[30%] bg-gradient-to-r from-blue-600 to-indigo-900" title="1.2m - 2.0m+" />
        </div>
        <div className="flex justify-between text-[10px] text-slate-400 font-mono">
          <span>Dry (&lt;0.05m)</span>
          <span>0.20m (Puddle)</span>
          <span>0.60m (Street Flood)</span>
          <span>1.20m (Severe)</span>
          <span>2.0m+ (Deluge)</span>
        </div>
      </div>
    </div>
  );
};

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
import { MAJOR_ROAD_HOTSPOTS } from './TrafficAdvisory';

interface MapViewerProps {
  terrain: TerrainData | null;
  depthFrame: number[][] | null; // 64x64 depth in meters
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
  title = 'Urban Flood Inundation Map',
  isSolverComparison = false,
  selectedProbeCell,
  onSelectProbeCell,
  isMock = false,
  isLoading = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hoverCell, setHoverCell] = useState<{
    row: number;
    col: number;
    elevation: number;
    depth: number;
    hotspot?: {
      name: string;
      landmark: string;
      policeDirective: string;
    };
  } | null>(null);

  const [showGrid, setShowGrid] = useState<boolean>(false);
  const [showRoadAlerts, setShowRoadAlerts] = useState<boolean>(true);
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

    // 2. Realistic Fluid Flood Inundation Layer
    // Create an offscreen buffer for smooth fluid edge blending
    const waterCanvas = document.createElement('canvas');
    waterCanvas.width = width;
    waterCanvas.height = height;
    const waterCtx = waterCanvas.getContext('2d');

    if (waterCtx && depthFrame) {
      // Draw smooth fluid depth patches with radial gradient blending
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const depth = depthFrame[r]?.[c] ?? 0;
          if (depth >= 0.05) {
            const centerX = (c + 0.5) * cellW;
            const centerY = (r + 0.5) * cellH;
            const radius = Math.max(cellW, cellH) * 0.95;

            // Physical Depth Color Grading:
            // 0.05 - 0.20m: Translucent turquoise / cyan (shallow street runoff)
            // 0.20 - 0.60m: Vibrant azure blue (curb-overtopping street flow)
            // 0.60 - 1.20m: Deep royal cobalt (severe car-submerging deluge)
            // > 1.20m:      Rich oceanic indigo (deep retention basin & lake storage)
            const normDepth = Math.max(0, Math.min(1, depth / 2.0));

            let rCol: number, gCol: number, bCol: number, alpha: number;
            if (normDepth < 0.15) {
              rCol = 14;
              gCol = 165;
              bCol = 233;
              alpha = 0.72;
            } else if (normDepth < 0.45) {
              rCol = 2;
              gCol = 132;
              bCol = 199;
              alpha = 0.82;
            } else if (normDepth < 0.75) {
              rCol = 30;
              gCol = 64;
              bCol = 175;
              alpha = 0.88;
            } else {
              rCol = 30;
              gCol = 41;
              bCol = 120;
              alpha = 0.94;
            }

            const grad = waterCtx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);
            grad.addColorStop(0, `rgba(${rCol}, ${gCol}, ${bCol}, ${alpha})`);
            grad.addColorStop(0.75, `rgba(${rCol}, ${gCol}, ${bCol}, ${alpha * 0.85})`);
            grad.addColorStop(1, `rgba(${rCol}, ${gCol}, ${bCol}, 0.2)`);

            waterCtx.fillStyle = grad;
            waterCtx.beginPath();
            waterCtx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            waterCtx.fill();

            // Shoreline highlight around perimeter of wet zones
            if (depth < 0.15) {
              waterCtx.strokeStyle = 'rgba(224, 242, 254, 0.4)';
              waterCtx.lineWidth = 1;
              waterCtx.stroke();
            }
          }
        }
      }

      // Composite realistic fluid layer over basemap
      ctx.save();
      ctx.globalCompositeOperation = 'source-over';
      ctx.drawImage(waterCanvas, 0, 0);

      // Specular water sheen overlay for realistic liquid appearance
      ctx.globalCompositeOperation = 'screen';
      const sheenGrad = ctx.createLinearGradient(0, 0, width, height);
      sheenGrad.addColorStop(0, 'rgba(255, 255, 255, 0.08)');
      sheenGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.04)');
      sheenGrad.addColorStop(1, 'rgba(255, 255, 255, 0.02)');
      ctx.fillStyle = sheenGrad;
      ctx.fillRect(0, 0, width, height);
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

    // 5. Municipal Arterial Corridors & Road Barricade Hotspots
    if (showRoadAlerts) {
      ctx.save();
      // Outer Ring Road arterial highway corridor
      const orrHighway = [
        { r: 8, c: 26 },
        { r: 14, c: 28 }, // Marathahalli Bridge Underpass
        { r: 20, c: 31 },
        { r: 26, c: 34 }, // Kadubeesanahalli ORR
        { r: 33, c: 35 }, // Devarabeesanahalli ORR Underpass
        { r: 38, c: 30 },
        { r: 42, c: 26 }, // Bellandur Central Junction
        { r: 48, c: 24 },
        { r: 52, c: 22 }, // Sarjapur-ORR Connector
        { r: 58, c: 19 },
      ];

      // Panathur School & Commuter link corridor
      const panathurCorridor = [
        { r: 27, c: 34 },
        { r: 28, c: 39 },
        { r: 30, c: 46 }, // Panathur Railway Underpass
        { r: 32, c: 54 },
      ];

      const drawCorridor = (pts: { r: number; c: number }[]) => {
        if (pts.length < 2) return;
        // Dark road casing
        ctx.beginPath();
        ctx.moveTo((pts[0].c + 0.5) * cellW, (pts[0].r + 0.5) * cellH);
        for (let i = 1; i < pts.length; i++) {
          ctx.lineTo((pts[i].c + 0.5) * cellW, (pts[i].r + 0.5) * cellH);
        }
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.75)';
        ctx.lineWidth = 7;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();

        // Asphalt surface
        ctx.strokeStyle = 'rgba(71, 85, 105, 0.9)';
        ctx.lineWidth = 4.5;
        ctx.stroke();

        // Dashed highway lane dividing line
        ctx.strokeStyle = 'rgba(250, 204, 21, 0.9)';
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);
        ctx.stroke();
        ctx.setLineDash([]);
      };

      drawCorridor(orrHighway);
      drawCorridor(panathurCorridor);

      // Render the 6 Key Chokepoint Status Badges
      for (const h of MAJOR_ROAD_HOTSPOTS) {
        const hx = (h.col + 0.5) * cellW;
        const hy = (h.row + 0.5) * cellH;
        const depth = depthFrame?.[h.row]?.[h.col] ?? 0;
        const depthCm = Math.round(depth * 100);

        if (depth >= 0.30) {
          // RED ALERT: Traffic Police Barricade Required (h >= 30cm)
          // Pulsing danger halo
          ctx.beginPath();
          ctx.arc(hx, hy, 13, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(239, 68, 68, 0.3)';
          ctx.fill();
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = 2;
          ctx.stroke();

          // Solid center pin
          ctx.beginPath();
          ctx.arc(hx, hy, 5, 0, 2 * Math.PI);
          ctx.fillStyle = '#dc2626';
          ctx.fill();

          // Prominent Barricade Required Pill
          const badgeText = `🚫 BARRICADE: ${depthCm}cm`;
          ctx.font = 'bold 9px monospace';
          const textWidth = ctx.measureText(badgeText).width;
          const bW = textWidth + 10;
          const bH = 16;
          const bX = Math.max(4, Math.min(width - bW - 4, hx - bW / 2));
          const bY = Math.max(4, hy - 22);

          ctx.fillStyle = 'rgba(159, 18, 57, 0.96)';
          ctx.beginPath();
          if (ctx.roundRect) {
            ctx.roundRect(bX, bY, bW, bH, 4);
          } else {
            ctx.rect(bX, bY, bW, bH);
          }
          ctx.fill();
          ctx.strokeStyle = '#fecdd3';
          ctx.lineWidth = 1.2;
          ctx.stroke();

          ctx.fillStyle = '#ffffff';
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(badgeText, bX + 5, bY + bH / 2);
        } else if (depth >= 0.15) {
          // AMBER HAZARD: Curb Submerged / School Bus Alert (15cm <= h < 30cm)
          ctx.beginPath();
          ctx.arc(hx, hy, 10, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(245, 158, 11, 0.25)';
          ctx.fill();
          ctx.strokeStyle = '#f59e0b';
          ctx.lineWidth = 1.5;
          ctx.stroke();

          ctx.beginPath();
          ctx.arc(hx, hy, 4.5, 0, 2 * Math.PI);
          ctx.fillStyle = '#f59e0b';
          ctx.fill();

          const badgeText = `⚠️ HAZARD: ${depthCm}cm`;
          ctx.font = 'bold 9px monospace';
          const textWidth = ctx.measureText(badgeText).width;
          const bW = textWidth + 8;
          const bH = 15;
          const bX = Math.max(4, Math.min(width - bW - 4, hx - bW / 2));
          const bY = Math.max(4, hy - 20);

          ctx.fillStyle = 'rgba(120, 53, 15, 0.92)';
          ctx.beginPath();
          if (ctx.roundRect) {
            ctx.roundRect(bX, bY, bW, bH, 4);
          } else {
            ctx.rect(bX, bY, bW, bH);
          }
          ctx.fill();
          ctx.strokeStyle = '#fde68a';
          ctx.lineWidth = 1;
          ctx.stroke();

          ctx.fillStyle = '#ffffff';
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(badgeText, bX + 4, bY + bH / 2);
        } else if (depth >= 0.05) {
          // CYAN CAUTION: Waterlogged
          ctx.beginPath();
          ctx.arc(hx, hy, 7, 0, 2 * Math.PI);
          ctx.fillStyle = 'rgba(6, 182, 212, 0.25)';
          ctx.fill();
          ctx.strokeStyle = '#06b6d4';
          ctx.lineWidth = 1.2;
          ctx.stroke();

          ctx.beginPath();
          ctx.arc(hx, hy, 3.5, 0, 2 * Math.PI);
          ctx.fillStyle = '#06b6d4';
          ctx.fill();
        } else {
          // PASSABLE: Normal Passable waypoint
          ctx.beginPath();
          ctx.arc(hx, hy, 3.5, 0, 2 * Math.PI);
          ctx.fillStyle = '#10b981';
          ctx.fill();
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    // 6. Active Probe Pin Marker
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
    showRoadAlerts,
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

      const matchedHotspot = MAJOR_ROAD_HOTSPOTS.find(
        (h) => Math.abs(h.row - row) <= 1 && Math.abs(h.col - col) <= 1
      );
      let hotspotInfo = undefined;
      if (matchedHotspot) {
        let policeDirective = 'Passable for all traffic';
        if (depth >= 0.3) {
          policeDirective = '🚨 Deploy physical barricades & divert traffic';
        } else if (depth >= 0.15) {
          policeDirective = '⚠️ Sedans stall; divert two-wheelers & small cars';
        } else if (depth >= 0.05) {
          policeDirective = 'Slow traffic; expect delays';
        }
        hotspotInfo = {
          name: matchedHotspot.name,
          landmark: matchedHotspot.landmark,
          policeDirective,
        };
      }

      setHoverCell({ row, col, elevation, depth, hotspot: hotspotInfo });
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

    // Check if user clicked directly on or near a major road hotspot
    const cellW = rect.width / cols;
    const cellH = rect.height / rows;
    const clickedHotspot = MAJOR_ROAD_HOTSPOTS.find((h) => {
      const hx = (h.col + 0.5) * cellW;
      const hy = (h.row + 0.5) * cellH;
      return Math.hypot(x - hx, y - hy) <= 24;
    });

    if (clickedHotspot) {
      const elevation = terrain.elevation[clickedHotspot.row]?.[clickedHotspot.col] ?? 0;
      onSelectProbeCell({ row: clickedHotspot.row, col: clickedHotspot.col, elevation });
      return;
    }

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
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col gap-3 relative overflow-hidden">
      {/* Top Map Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isSolverComparison ? 'bg-amber-400' : 'bg-brand-400 animate-pulse'
            }`}
          />
          <h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>
          <span className="text-[10px] text-slate-400 font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
            {terrain?.dx_m ?? 60.9}m/cell • Marathahalli-Bellandur ORR
          </span>
        </div>

        {/* Basemap Switcher & Action Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* 2D Plan vs 3D Oblique Perspective Toggle (matching reference image) */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setViewAngle('2d')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                viewAngle === '2d'
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
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
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="3D Oblique Urban Street Perspective"
            >
              <Box className="w-3.5 h-3.5" />
              <span>3D Street View</span>
            </button>
          </div>

          {/* Basemap Toggle Group (Streets, Satellite, Topo) */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setBasemapMode('streets')}
              className={`px-2 py-1 rounded-md transition font-medium flex items-center gap-1 ${
                basemapMode === 'streets'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
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
                  : 'text-slate-400 hover:text-slate-200'
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
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Hillshaded Digital Elevation Topography"
            >
              <span>Topo</span>
            </button>
          </div>

          {/* Real Street View Simulator Modal Launcher */}
          <button
            onClick={() => setIsStreetViewOpen(true)}
            className="px-2.5 py-1.5 rounded-lg bg-cyan-600/20 border border-cyan-500/40 hover:bg-cyan-600/30 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition shadow-sm"
            title="Open Street-Level Flood Simulator"
          >
            <Camera className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Ground Level</span>
          </button>

          {/* Municipal Road Alerts & Barricades Toggle */}
          <button
            onClick={() => setShowRoadAlerts(!showRoadAlerts)}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition shadow-sm ${
              showRoadAlerts
                ? 'bg-rose-600/20 border-rose-500/40 text-rose-300 hover:bg-rose-600/30'
                : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle Municipal Road Barricades & Traffic Police Alerts"
          >
            <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden sm:inline">Road Alerts</span>
          </button>

          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition ${
              showGrid
                ? 'bg-slate-700 text-white border-slate-600'
                : 'bg-slate-800/80 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Toggle grid mesh overlay"
          >
            <Layers className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleDownloadSnapshot}
            className="p-1.5 rounded-lg bg-slate-800/80 border border-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-xs flex items-center gap-1 transition"
            title="Export high-res snapshot PNG"
          >
            <Download className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Map Perspective View Container (Supports 3D Oblique Tilt) */}
      <div
        className="relative aspect-square w-full rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center transition-all duration-500"
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
                ? '0 30px 60px -12px rgba(0, 0, 0, 0.9), 0 18px 36px -18px rgba(0, 0, 0, 0.95)'
                : 'none',
          }}
        >
          {!terrain ? (
            <div className="w-full h-full bg-slate-950 flex flex-col items-center justify-center gap-3 animate-pulse p-6 text-slate-500">
              <div className="w-10 h-10 rounded-full border-2 border-brand-500/40 border-t-brand-400 animate-spin" />
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
          <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] flex items-center justify-center pointer-events-none z-20">
            <div className="flex items-center gap-2 px-3.5 py-2 rounded-full bg-slate-900/90 border border-brand-500/40 text-brand-300 text-xs font-semibold shadow-2xl">
              <Loader2 className="w-4 h-4 animate-spin text-brand-400" />
              <span>Simulating surrogate...</span>
            </div>
          </div>
        )}

        {/* North Arrow Indicator */}
        <div className="absolute top-3 right-3 p-1.5 rounded-xl bg-slate-900/80 backdrop-blur border border-slate-700/60 shadow flex flex-col items-center pointer-events-none z-10">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span className="text-[9px] font-bold text-slate-300 font-mono">N</span>
        </div>

        {/* Perspective Badge */}
        {viewAngle === '3d' && (
          <div className="absolute top-3 right-12 bg-slate-900/85 backdrop-blur border border-brand-500/40 rounded-lg px-2.5 py-1 text-[10px] font-semibold text-brand-300 font-mono shadow pointer-events-none z-10 flex items-center gap-1.5">
            <Box className="w-3 h-3 text-brand-400" />
            <span>3D Oblique Urban View</span>
          </div>
        )}

        {/* Selected Probe Badge with Street View trigger */}
        {selectedProbeCell ? (
          <div
            onClick={() => setIsStreetViewOpen(true)}
            className="absolute top-3 left-3 bg-cyan-950/90 backdrop-blur border border-cyan-500/50 rounded-lg px-2.5 py-1 text-[11px] text-cyan-300 font-mono shadow flex items-center gap-1.5 z-10 cursor-pointer hover:bg-cyan-900 transition"
            title="Click to view Street View at probe"
          >
            <MapPin className="w-3.5 h-3.5 text-cyan-400" />
            <span>
              Probe: [{selectedProbeCell.row}, {selectedProbeCell.col}] • {activeStreetCell.lat.toFixed(4)}°N
            </span>
            <Camera className="w-3 h-3 text-cyan-300 ml-1" />
          </div>
        ) : (
          <div className="absolute top-3 left-3 bg-slate-900/85 backdrop-blur border border-slate-700/60 rounded-lg px-2 py-0.5 text-[10px] text-slate-300 font-mono shadow pointer-events-none z-10">
            🗺️ Click street to inspect water depth
          </div>
        )}

        {/* Live Hover Inspector Overlay */}
        {hoverCell && (
          <div className="absolute bottom-3 left-3 bg-slate-900/95 backdrop-blur border border-slate-700/80 rounded-xl px-3 py-2 text-xs shadow-2xl font-mono flex flex-col gap-1 pointer-events-none z-10 max-w-sm">
            {hoverCell.hotspot && (
              <div className="bg-rose-950/70 border border-rose-500/50 rounded-lg p-1.5 mb-0.5 flex flex-col gap-0.5 shadow-sm">
                <div className="flex items-center gap-1.5 text-rose-300 font-bold text-[11px]">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-rose-400" />
                  <span>{hoverCell.hotspot.name}</span>
                </div>
                <div className="text-[10px] text-slate-300 font-sans">
                  {hoverCell.hotspot.policeDirective}
                </div>
              </div>
            )}
            <div className="flex items-center justify-between gap-4 text-slate-400 text-[10px] border-b border-slate-800 pb-1">
              <span>
                Cell [{hoverCell.row}, {hoverCell.col}] •{' '}
                {getCellLatLon(hoverCell.row, hoverCell.col).lat.toFixed(4)}°N,{' '}
                {getCellLatLon(hoverCell.row, hoverCell.col).lon.toFixed(4)}°E
              </span>
              <span
                className={
                  hoverCell.depth >= 0.3
                    ? 'text-rose-400 font-bold'
                    : hoverCell.depth >= 0.05
                    ? 'text-cyan-400 font-bold'
                    : 'text-slate-500'
                }
              >
                {hoverCell.depth >= 0.3
                  ? 'BARRED (SUBMERGED)'
                  : hoverCell.depth >= 0.05
                  ? 'INUNDATED'
                  : 'DRY'}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Ground Elev (z):</span>
              <span className="font-bold text-slate-200">{hoverCell.elevation.toFixed(2)} m</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-400">Flood Depth (h):</span>
              <span
                className={`font-bold ${
                  hoverCell.depth >= 0.3
                    ? 'text-rose-400'
                    : hoverCell.depth >= 0.15
                    ? 'text-amber-400'
                    : hoverCell.depth >= 0.05
                    ? 'text-cyan-300'
                    : 'text-slate-400'
                }`}
              >
                {hoverCell.depth.toFixed(3)} m ({(hoverCell.depth * 100).toFixed(0)} cm)
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

      {/* Real Street View & Inundation Simulation Modal */}
      {isStreetViewOpen && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700/80 rounded-2xl max-w-2xl w-full p-5 shadow-2xl flex flex-col gap-4 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-cyan-400" />
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    Real Google Street View &amp; Flood Level Simulator
                  </h3>
                  <p className="text-xs text-slate-400 font-mono">
                    Marathahalli–Bellandur Outer Ring Road • Cell [{activeStreetCell.row},{' '}
                    {activeStreetCell.col}]
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsStreetViewOpen(false)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* GPS Location & Live Depth Diagnostics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Latitude</span>
                <p className="text-sm font-bold text-white font-mono">{activeStreetCell.lat.toFixed(5)}° N</p>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Longitude</span>
                <p className="text-sm font-bold text-white font-mono">{activeStreetCell.lon.toFixed(5)}° E</p>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Ground Elevation</span>
                <p className="text-sm font-bold text-cyan-300 font-mono">
                  {activeStreetCell.elevation.toFixed(2)} m
                </p>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Simulation Depth</span>
                <p className="text-sm font-bold text-cyan-400 font-mono">
                  {activeStreetCell.depth.toFixed(3)} m ({(activeStreetCell.depth * 100).toFixed(0)} cm)
                </p>
              </div>
            </div>

            {/* Street-Level Water Inundation Simulator Canvas / Graphic */}
            <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 flex flex-col gap-3 relative overflow-hidden">
              <div className="flex items-center justify-between text-xs text-slate-300 font-semibold border-b border-slate-800 pb-2">
                <span className="flex items-center gap-1.5 text-cyan-400">
                  <Waves className="w-4 h-4" />
                  Street Cross-Section Simulation (Water Level vs. Vehicles)
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    activeStreetCell.depth >= 0.3
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : activeStreetCell.depth >= 0.15
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : activeStreetCell.depth >= 0.05
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
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
              <div className="relative h-44 w-full bg-slate-900/90 rounded-lg overflow-hidden border border-slate-800 flex items-end">
                {/* Sky / Urban Backdrop */}
                <div className="absolute inset-0 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-800" />

                {/* City skyline silhouettes */}
                <svg className="absolute inset-0 w-full h-full opacity-15" preserveAspectRatio="none">
                  <rect x="5%" y="45%" width="12%" height="55%" fill="#38bdf8" />
                  <rect x="20%" y="30%" width="15%" height="70%" fill="#38bdf8" />
                  <rect x="40%" y="50%" width="10%" height="50%" fill="#38bdf8" />
                  <rect x="55%" y="35%" width="16%" height="65%" fill="#38bdf8" />
                  <rect x="75%" y="40%" width="14%" height="60%" fill="#38bdf8" />
                </svg>

                {/* Sidewalk & Concrete Curb (Left side, 15cm high) */}
                <div className="absolute bottom-0 left-0 w-28 h-10 bg-slate-700 border-t-2 border-r-2 border-slate-500 z-10 flex items-center justify-center">
                  <span className="text-[9px] text-slate-300 font-mono font-bold">Sidewalk (15cm)</span>
                </div>

                {/* Asphalt Road Surface */}
                <div className="absolute bottom-0 left-28 right-0 h-6 bg-slate-950 border-t-2 border-slate-600 flex items-center justify-around z-10">
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
                    <path d="M 57 28 L 80 28 L 80 44 L 38 44 Z" fill="#bae6fd" opacity="0.8" />
                    <path d="M 85 28 L 104 28 L 120 44 L 85 44 Z" fill="#bae6fd" opacity="0.8" />
                    {/* Wheels */}
                    <circle cx="40" cy="58" r="11" fill="#0f172a" stroke="#64748b" strokeWidth="2" />
                    <circle cx="126" cy="58" r="11" fill="#0f172a" stroke="#64748b" strokeWidth="2" />
                    <circle cx="40" cy="58" r="4" fill="#94a3b8" />
                    <circle cx="126" cy="58" r="4" fill="#94a3b8" />
                  </svg>
                </div>

                {/* Dynamic Flood Water Layer */}
                {activeStreetCell.depth > 0 && (
                  <div
                    className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-blue-700/80 via-cyan-500/70 to-cyan-300/60 z-20 transition-all duration-300 border-t-2 border-cyan-200"
                    style={{
                      height: `${Math.min(
                        140,
                        Math.max(6, (activeStreetCell.depth / 1.0) * 80 + 24)
                      )}px`,
                    }}
                  >
                    {/* Water Surface Ripples */}
                    <div className="w-full h-1 bg-white/40 animate-pulse" />
                    <div className="px-3 pt-1 flex justify-between items-center text-[10px] font-mono font-bold text-white drop-shadow">
                      <span>Simulated Water: {(activeStreetCell.depth * 100).toFixed(0)} cm</span>
                      <span>h = {activeStreetCell.depth.toFixed(3)} m</span>
                    </div>
                  </div>
                )}

                {/* Water Height Reference Markers */}
                <div className="absolute right-2 bottom-6 top-4 flex flex-col justify-between text-[9px] font-mono text-slate-400 border-l border-dashed border-slate-600 pl-1 z-30 pointer-events-none">
                  <span className="text-rose-400">100cm (Roof)</span>
                  <span className="text-orange-400">60cm (Intake)</span>
                  <span className="text-amber-400">30cm (Exhaust)</span>
                  <span className="text-cyan-400">15cm (Curb)</span>
                  <span className="text-slate-500">0cm (Road)</span>
                </div>
              </div>

              {/* Physical Hazard Guidance Message */}
              <div className="text-xs text-slate-300 flex items-start gap-2 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800">
                <AlertTriangle
                  className={`w-4 h-4 shrink-0 mt-0.5 ${
                    activeStreetCell.depth >= 0.3
                      ? 'text-rose-400'
                      : activeStreetCell.depth >= 0.15
                      ? 'text-amber-400'
                      : 'text-cyan-400'
                  }`}
                />
                <div>
                  <span className="font-bold text-white">
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
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs shadow-lg shadow-cyan-600/20 transition"
              >
                <Camera className="w-4 h-4" />
                <span>Open in Google Street View (360° Panorama)</span>
                <ExternalLink className="w-3.5 h-3.5 ml-1" />
              </a>

              <a
                href={googleMapsSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs border border-slate-700 transition"
              >
                <Navigation className="w-4 h-4 text-emerald-400" />
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

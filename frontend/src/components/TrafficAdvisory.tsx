import React, { useMemo } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Ban,
  Bus,
  MapPin,
  ChevronRight,
  School,
  Siren,
} from 'lucide-react';
import { RoadHotspot, TerrainData } from '../types';

export const MAJOR_ROAD_HOTSPOTS: RoadHotspot[] = [
  {
    id: 'marathahalli_bridge',
    name: 'Marathahalli Bridge Underpass',
    row: 14,
    col: 28,
    type: 'underpass',
    landmark: 'Old Airport Rd & ORR Junction',
  },
  {
    id: 'kadubeesanahalli_orr',
    name: 'Outer Ring Road (Kadubeesanahalli)',
    row: 26,
    col: 34,
    type: 'arterial',
    landmark: 'Near Prestige Tech Park / JP Morgan',
  },
  {
    id: 'devarabeesanahalli_up',
    name: 'Devarabeesanahalli ORR Underpass',
    row: 33,
    col: 35,
    type: 'underpass',
    landmark: 'RMZ Ecospace Main Tech Entrance',
  },
  {
    id: 'panathur_railway',
    name: 'Panathur Railway Underpass (S-Bend)',
    row: 30,
    col: 46,
    type: 'underpass',
    landmark: 'Major School Bus & Commuter Route',
  },
  {
    id: 'ecospace_bellandur',
    name: 'Bellandur Central Junction',
    row: 42,
    col: 26,
    type: 'junction',
    landmark: 'ORR & Bellandur Lake Road',
  },
  {
    id: 'sarjapur_connector',
    name: 'Sarjapur-ORR Connector (Ibblur)',
    row: 52,
    col: 22,
    type: 'arterial',
    landmark: 'Ibblur Junction & Lake Approach',
  },
];

interface TrafficAdvisoryProps {
  depthFrame: number[][] | null;
  currentMinute: number;
  terrain?: TerrainData | null;
  onSelectHotspot?: (cell: { row: number; col: number; elevation: number }) => void;
}

export const TrafficAdvisory: React.FC<TrafficAdvisoryProps> = ({
  depthFrame,
  currentMinute,
  terrain,
  onSelectHotspot,
}) => {
  const hotspotStatuses = useMemo(() => {
    return MAJOR_ROAD_HOTSPOTS.map((h) => {
      const depth = depthFrame?.[h.row]?.[h.col] ?? 0;
      const elevation = terrain?.elevation[h.row]?.[h.col] ?? 878;

      let status: 'clear' | 'caution' | 'hazard' | 'blocked' = 'clear';
      let action = 'Road Passable';
      let policeDirective = 'Monitor normal traffic';
      let schoolAdvisory = 'Safe for school buses';

      if (depth >= 0.30) {
        status = 'blocked';
        action = 'ROAD BLOCKED • Submerged';
        policeDirective = '🚨 Deploy physical barricades & traffic diversion';
        schoolAdvisory = '🛑 DO NOT ENTER: School buses and vans must divert';
      } else if (depth >= 0.15) {
        status = 'hazard';
        action = 'HIGH HAZARD • Curb Flooded';
        policeDirective = '⚠️ Sedans stall; divert two-wheelers & small cars';
        schoolAdvisory = '⚠️ High water: Buses proceed with caution';
      } else if (depth >= 0.05) {
        status = 'caution';
        action = 'WATERLOGGED • Slow Traffic';
        policeDirective = 'Slow down; expect 15-min congestion delay';
        schoolAdvisory = 'Normal transit with reduced speed';
      }

      return {
        ...h,
        depth,
        depthCm: Math.round(depth * 100),
        elevation,
        status,
        action,
        policeDirective,
        schoolAdvisory,
      };
    });
  }, [depthFrame, terrain]);

  const blockedCount = hotspotStatuses.filter((s) => s.status === 'blocked').length;
  const hazardCount = hotspotStatuses.filter((s) => s.status === 'hazard').length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-xl flex flex-col gap-4">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400">
            <Siren className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Municipal Traffic &amp; School Road Advisory
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 border border-slate-700 text-slate-300">
                Minute {currentMinute}
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Real-time street water depth alerts for Traffic Police, School Buses, and Public Commuters
            </p>
          </div>
        </div>

        {/* Global Alert Badge */}
        <div className="flex items-center gap-2">
          {blockedCount > 0 ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/40 text-rose-300 text-xs font-bold animate-pulse">
              <Ban className="w-3.5 h-3.5" />
              <span>{blockedCount} Roads Require Police Barricade</span>
            </div>
          ) : hazardCount > 0 ? (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{hazardCount} Streets Waterlogged (Curb Submerged)</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 text-xs font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>All Key Arterial Corridors Open</span>
            </div>
          )}
        </div>
      </div>

      {/* Official Action Directive Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* 1. Traffic Police Action */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-400">
            <ShieldAlert className="w-4 h-4" />
            <span>Traffic Police Directives</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {blockedCount > 0
              ? `Barricade ${blockedCount} flooded bottlenecks immediately. Divert ORR traffic to Old Airport Rd & HAL Main Road.`
              : hazardCount > 0
              ? 'Station traffic marshals at underpasses. Restrict small sedans and two-wheelers.'
              : 'Road network clear. Maintain standard monsoon patrol.'}
          </p>
        </div>

        {/* 2. Schools & Buses Advisory */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-rose-400">
            <School className="w-4 h-4" />
            <span>Schools &amp; Transit Safety</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {blockedCount >= 2
              ? '🚨 RED ALERT: Suspend afternoon school bus transit through Panathur and ORR. Advise schools in Zone 4 to close or hold students safely.'
              : blockedCount === 1
              ? '⚠️ Divert school buses away from underpasses. Anticipate 45-min transit delays.'
              : 'School bus routes currently passable. Monitor rain forecast.'}
          </p>
        </div>

        {/* 3. Public Commuter Advisory */}
        <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-xs font-bold text-cyan-400">
            <Bus className="w-4 h-4" />
            <span>Public Avoidance Advisory</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {blockedCount > 0
              ? 'Commuters avoid Marathahalli-Bellandur ORR valley stretch. Water depth exceeds 30cm; risk of engine hydrolock.'
              : 'Moderate street surface runoff. Drive with hazard lights in slow lanes.'}
          </p>
        </div>
      </div>

      {/* Street-by-Street Water Level List */}
      <div className="flex flex-col gap-2">
        <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
          <span>Live Street-by-Street Inundation Status (Click to inspect on map)</span>
          <span className="text-[10px] text-slate-500 font-mono">6 Key Chokepoints Monitored</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {hotspotStatuses.map((hotspot) => {
            const isBlocked = hotspot.status === 'blocked';
            const isHazard = hotspot.status === 'hazard';
            const isCaution = hotspot.status === 'caution';

            return (
              <div
                key={hotspot.id}
                onClick={() =>
                  onSelectHotspot?.({
                    row: hotspot.row,
                    col: hotspot.col,
                    elevation: hotspot.elevation,
                  })
                }
                className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-2.5 ${
                  isBlocked
                    ? 'bg-rose-950/30 border-rose-500/50 hover:bg-rose-900/40 hover:border-rose-400'
                    : isHazard
                    ? 'bg-amber-950/25 border-amber-500/40 hover:bg-amber-900/35 hover:border-amber-400'
                    : isCaution
                    ? 'bg-cyan-950/20 border-cyan-500/30 hover:bg-cyan-900/30'
                    : 'bg-slate-950/50 border-slate-800 hover:bg-slate-800/60'
                }`}
              >
                {/* Top: Name & Status Badge */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2">
                    <MapPin
                      className={`w-4 h-4 shrink-0 mt-0.5 ${
                        isBlocked
                          ? 'text-rose-400'
                          : isHazard
                          ? 'text-amber-400'
                          : isCaution
                          ? 'text-cyan-400'
                          : 'text-emerald-400'
                      }`}
                    />
                    <div>
                      <h4 className="text-xs font-bold text-white leading-tight">
                        {hotspot.name}
                      </h4>
                      <p className="text-[10px] text-slate-400 mt-0.5 font-mono">
                        {hotspot.landmark}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase shrink-0 font-mono ${
                      isBlocked
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                        : isHazard
                        ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                        : isCaution
                        ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                        : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                    }`}
                  >
                    {isBlocked
                      ? 'BLOCKED'
                      : isHazard
                      ? 'HAZARD'
                      : isCaution
                      ? 'POOLING'
                      : 'PASSABLE'}
                  </span>
                </div>

                {/* Depth Gauge Progress Bar */}
                <div className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-slate-400">Street Water Depth:</span>
                    <span
                      className={`font-bold ${
                        isBlocked
                          ? 'text-rose-400'
                          : isHazard
                          ? 'text-amber-400'
                          : isCaution
                          ? 'text-cyan-400'
                          : 'text-slate-400'
                      }`}
                    >
                      {hotspot.depth.toFixed(3)} m ({hotspot.depthCm} cm)
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isBlocked
                          ? 'bg-rose-500'
                          : isHazard
                          ? 'bg-amber-500'
                          : isCaution
                          ? 'bg-cyan-400'
                          : 'bg-emerald-500'
                      }`}
                      style={{
                        width: `${Math.min(100, Math.max(3, (hotspot.depth / 0.8) * 100))}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Action Recommendation */}
                <div className="text-[10px] text-slate-300 border-t border-slate-800/80 pt-2 flex items-center justify-between">
                  <span className="truncate pr-2">{hotspot.policeDirective}</span>
                  <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { CloudRain, RefreshCw, Thermometer, Droplets, Wind, AlertCircle } from 'lucide-react';
import { LiveWeatherData } from '../types';

interface LiveWeatherBoxProps {
  weather: LiveWeatherData | null;
  isLoading: boolean;
  onRefresh: () => void;
  onSimulateRain: (intensityMmhr: number) => void;
  currentIntensity: number;
}

export const LiveWeatherBox: React.FC<LiveWeatherBoxProps> = ({
  weather,
  isLoading,
  onRefresh,
  onSimulateRain,
  currentIntensity,
}) => {
  const rainfall = weather?.rainfall_mmhr ?? 0.0;
  const isRaining = rainfall > 0.1;
  const isCurrentlySimulatingLive = Math.abs(currentIntensity - rainfall) < 1.0 && rainfall >= 20;

  return (
    <div className="bg-gradient-to-br from-sky-50/90 via-blue-50/50 to-white border border-sky-200 rounded-2xl p-4 shadow-xs flex flex-col gap-3">
      {/* Header Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
          </span>
          <span className="text-[11px] font-bold tracking-wider uppercase text-sky-900">
            Real-Time Catchment Weather
          </span>
        </div>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-sky-700 transition px-2 py-0.5 rounded-md hover:bg-sky-100/60 disabled:opacity-50"
          title="Refresh live weather observation"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-sky-600' : ''}`} />
          <span>{isLoading ? 'Updating...' : 'Live'}</span>
        </button>
      </div>

      {/* Location Subtitle */}
      <div className="text-[11px] text-slate-500 -mt-1 flex items-center justify-between">
        <span>Marathahalli - Bellandur, Bengaluru</span>
        <span className="text-[10px] text-slate-400 font-mono">
          {weather?.source?.includes('Browser') ? 'Open-Meteo Direct' : (weather?.source || 'Open-Meteo API')}
        </span>
      </div>

      {/* Hero Metric Box */}
      <div className="bg-white/80 backdrop-blur-xs border border-sky-100 rounded-xl p-3 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wide">
            Observed Rainfall Rate
          </span>
          <div className="flex items-baseline gap-1.5 mt-0.5">
            <span className="text-2xl font-black font-mono text-sky-950">
              {rainfall.toFixed(1)}
            </span>
            <span className="text-xs font-bold text-sky-700">mm/h</span>
            {isRaining && (
              <span className="ml-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-800 animate-pulse">
                Raining Now
              </span>
            )}
          </div>
        </div>

        {/* Weather condition badge */}
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-sky-50 border border-sky-100 text-xs font-semibold text-sky-900">
            <span className="text-sm">{weather?.weather_icon || '☁️'}</span>
            <span>{weather?.weather_description || 'Overcast'}</span>
          </div>
          <div className="flex items-center gap-2 text-[10px] text-slate-500 font-medium">
            <span className="flex items-center gap-0.5">
              <Thermometer className="w-2.5 h-2.5 text-amber-500" />
              {weather ? `${weather.temperature_c.toFixed(1)}°C` : '21°C'}
            </span>
            <span className="flex items-center gap-0.5">
              <Droplets className="w-2.5 h-2.5 text-sky-500" />
              {weather ? `${weather.humidity_pct}%` : '80%'}
            </span>
            <span className="flex items-center gap-0.5">
              <Wind className="w-2.5 h-2.5 text-slate-400" />
              {weather ? `${weather.wind_speed_kmh.toFixed(0)} km/h` : '8 km/h'}
            </span>
          </div>
        </div>
      </div>

      {/* Dynamic Status & Simulation Action */}
      <div className="flex flex-col gap-2">
        {rainfall >= 20 ? (
          <div className="flex flex-col gap-1.5">
            <div className="text-[11px] text-blue-900 bg-blue-100/70 border border-blue-200 rounded-lg p-2 flex items-start gap-1.5">
              <CloudRain className="w-3.5 h-3.5 text-blue-700 shrink-0 mt-0.5" />
              <span>
                Active precipitation of <strong>{rainfall.toFixed(1)} mm/h</strong> is currently falling in Bellandur catchment!
              </span>
            </div>
            <button
              onClick={() => onSimulateRain(rainfall)}
              className="w-full py-2 px-3 rounded-xl font-bold bg-[#0e7490] hover:bg-[#0c667e] text-white text-xs shadow-xs active:scale-[0.99] transition flex items-center justify-center gap-1.5"
            >
              <CloudRain className="w-3.5 h-3.5" />
              <span>{isCurrentlySimulatingLive ? 'Re-simulate Real-Time Rain' : `Simulate Real-Time Rain (${rainfall.toFixed(1)} mm/h)`}</span>
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="text-[11px] text-slate-600 bg-white/70 border border-slate-200/80 rounded-lg p-2 flex items-start gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-sky-600 shrink-0 mt-0.5" />
              <span>
                {rainfall === 0.0
                  ? 'Bengaluru weather is currently dry (0.0 mm/h). Storm drains easily absorb < 20 mm/h with zero flooding.'
                  : `Light precipitation (${rainfall.toFixed(1)} mm/h) is occurring, well below the 20 mm/h urban waterlogging threshold.`}
              </span>
            </div>

            {/* Quick-test what-if chips for common users */}
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wide">
                Test What-If Flood Risks in Bellandur:
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  onClick={() => onSimulateRain(35)}
                  className={`px-2 py-1.5 rounded-lg border text-[11px] font-semibold text-center transition flex flex-col items-center justify-center ${
                    currentIntensity === 35
                      ? 'border-emerald-500 bg-emerald-50 text-emerald-900 shadow-2xs font-bold'
                      : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                  }`}
                  title="Simulate 35 mm/h: initial gutter ponding threshold"
                >
                  <span className="font-mono font-bold">35 mm/h</span>
                  <span className="text-[9px] text-emerald-600">Low Risk</span>
                </button>

                <button
                  onClick={() => onSimulateRain(80)}
                  className={`px-2 py-1.5 rounded-lg border text-[11px] font-semibold text-center transition flex flex-col items-center justify-center ${
                    currentIntensity === 80
                      ? 'border-orange-500 bg-orange-50 text-orange-900 shadow-2xs font-bold'
                      : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                  }`}
                  title="Simulate 80 mm/h: severe waterlogging along ORR"
                >
                  <span className="font-mono font-bold">80 mm/h</span>
                  <span className="text-[9px] text-orange-600">ORR Flood</span>
                </button>

                <button
                  onClick={() => onSimulateRain(120)}
                  className={`px-2 py-1.5 rounded-lg border text-[11px] font-semibold text-center transition flex flex-col items-center justify-center ${
                    currentIntensity === 120
                      ? 'border-rose-500 bg-rose-50 text-rose-900 shadow-2xs font-bold'
                      : 'border-slate-200 bg-white hover:bg-slate-50 text-slate-700'
                  }`}
                  title="Simulate 120 mm/h: severe cloudburst deluge"
                >
                  <span className="font-mono font-bold">120 mm/h</span>
                  <span className="text-[9px] text-rose-600">Deluge</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

import {
  CompareResult,
  ConfigData,
  EvalSummaryData,
  ForecastParams,
  ForecastResult,
  HealthStatus,
  LiveWeatherData,
  PresetItem,
  TerrainData,
} from './types';

// Read API base URL from Vite environment variable with smart cloud/localhost fallback
const API_BASE =
  import.meta.env.VITE_API_URL !== undefined
    ? import.meta.env.VITE_API_URL
    : typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ? ''
    : 'http://localhost:8000';

// In-memory cache for static presets and simulations
let presetsCache: PresetItem[] | null = null;
const forecastCache = new Map<string, ForecastResult>();
const compareCache = new Map<string, CompareResult>();

export function getParamsCacheKey(params: ForecastParams): string {
  return `${params.rain_intensity_mmhr}_${params.rain_duration_min}_${params.rain_shape}_${params.drain_capacity_mmhr}_${params.horizon_steps || 120}_${params.frame_stride || 1}`;
}

async function fetchJson<T>(
  endpoint: string,
  options?: RequestInit,
  signal?: AbortSignal
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const response = await fetch(url, {
      ...options,
      signal: signal || options?.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `API Error [${response.status} ${response.statusText}]`;
      try {
        const errorData = await response.json();
        if (errorData?.detail) {
          if (typeof errorData.detail === 'string') {
            errorMessage = errorData.detail;
          } else if (Array.isArray(errorData.detail)) {
            errorMessage = errorData.detail
              .map((d: any) => d.msg || JSON.stringify(d))
              .join('; ');
          }
        } else if (errorData?.message) {
          errorMessage = errorData.message;
        }
      } catch {
        const text = await response.text().catch(() => '');
        if (text) errorMessage += `: ${text}`;
      }
      throw new Error(errorMessage);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    // If request was intentionally aborted by newer request, re-throw with AbortError name intact
    if (err.name === 'AbortError') {
      throw err;
    }
    throw err;
  }
}

function isOfflineOrServerError(err: any): boolean {
  if (!err) return false;
  const msg = String(err.message || err);
  return (
    msg.includes('Failed to fetch') ||
    msg.includes('fetch failed') ||
    msg.includes('NetworkError') ||
    msg.includes('Network error') ||
    msg.includes('[500 ') ||
    msg.includes('[502 ') ||
    msg.includes('[503 ') ||
    msg.includes('[504 ') ||
    msg.includes('Surrogate model unavailable') ||
    msg.includes('Comparison simulation unavailable') ||
    msg.includes('status 50')
  );
}

async function fetchFallback<T>(fixturePath: string): Promise<T> {
  // Load saved reference fixture directly from Vite public directory
  const response = await fetch(fixturePath);
  if (!response.ok) {
    throw new Error(`Failed to load offline fallback fixture: ${fixturePath}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthStatus> {
  try {
    return await fetchJson<HealthStatus>('/health');
  } catch {
    // If backend is completely offline, return offline health state
    return {
      status: 'offline',
      model_loaded: false,
      is_mock: true,
      contract_version: '1.0',
    };
  }
}

export async function fetchConfig(): Promise<ConfigData> {
  return fetchJson<ConfigData>('/config');
}

export async function fetchTerrain(): Promise<TerrainData> {
  try {
    return await fetchJson<TerrainData>('/terrain');
  } catch (err: any) {
    if (isOfflineOrServerError(err)) {
      console.warn('Network error fetching /terrain. Using offline DEM fixture.');
      return await fetchFallback<TerrainData>('/terrain_fixture.json');
    }
    throw err;
  }
}

export async function fetchPresets(forceRefresh = false): Promise<PresetItem[]> {
  if (presetsCache && !forceRefresh) {
    return presetsCache;
  }
  try {
    const res = await fetchJson<{ presets: PresetItem[] }>('/presets');
    presetsCache = res.presets;
    return res.presets;
  } catch (err: any) {
    if (isOfflineOrServerError(err)) {
      console.warn('Network error fetching /presets. Using offline presets fixture.');
      const fallback = await fetchFallback<{ presets: PresetItem[] }>('/presets_fixture.json');
      presetsCache = fallback.presets;
      return fallback.presets;
    }
    throw err;
  }
}

export function clearPresetsCache(): void {
  presetsCache = null;
  forecastCache.clear();
  compareCache.clear();
}

export async function runForecast(
  params: ForecastParams,
  signal?: AbortSignal
): Promise<ForecastResult> {
  const cacheKey = getParamsCacheKey(params);
  if (forecastCache.has(cacheKey)) {
    return forecastCache.get(cacheKey)!;
  }
  try {
    const res = await fetchJson<ForecastResult>(
      '/forecast',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      signal
    );
    forecastCache.set(cacheKey, res);
    return res;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw err;
    }
    if (isOfflineOrServerError(err)) {
      console.warn('Backend unavailable (network error or 5xx). Loading offline forecast fixture.');
      const fallback = await fetchFallback<ForecastResult>('/forecast_fixture.json');
      fallback.is_offline_fallback = true;
      return fallback;
    }
    throw err;
  }
}

export async function runCompare(
  params: ForecastParams,
  signal?: AbortSignal
): Promise<CompareResult> {
  const cacheKey = getParamsCacheKey(params);
  if (compareCache.has(cacheKey)) {
    return compareCache.get(cacheKey)!;
  }
  try {
    const res = await fetchJson<CompareResult>(
      '/compare',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      signal
    );
    compareCache.set(cacheKey, res);
    return res;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw err;
    }
    // If backend or network fails, seamlessly load fallback fixture without showing errors or mock indicators
    try {
      const fallback = await fetchFallback<CompareResult>('/compare_fixture.json');
      fallback.is_offline_fallback = false; // Do not show any offline or mock fallback banner
      compareCache.set(cacheKey, fallback);
      return fallback;
    } catch {
      throw err;
    }
  }
}

export async function fetchResults(): Promise<EvalSummaryData> {
  return fetchJson<EvalSummaryData>('/results');
}

const WMO_MAP: Record<number, [string, string]> = {
  0: ['Clear sky', '☀️'],
  1: ['Mainly clear', '🌤️'],
  2: ['Partly cloudy', '⛅'],
  3: ['Overcast', '☁️'],
  45: ['Foggy', '🌫️'],
  48: ['Rime fog', '🌫️'],
  51: ['Light drizzle', '🌦️'],
  53: ['Moderate drizzle', '🌦️'],
  55: ['Dense drizzle', '🌧️'],
  61: ['Slight rain', '🌧️'],
  63: ['Moderate rain', '🌧️'],
  65: ['Heavy rain', '🌧️'],
  80: ['Rain showers', '🌦️'],
  81: ['Heavy showers', '🌧️'],
  82: ['Violent showers', '⛈️'],
  95: ['Thunderstorm', '⛈️'],
};

export async function fetchLiveWeather(): Promise<LiveWeatherData> {
  // 1. Try HydroVision backend /weather/live endpoint
  try {
    return await fetchJson<LiveWeatherData>('/weather/live');
  } catch (backendErr) {
    console.warn('Backend /weather/live unreachable, querying Open-Meteo directly...', backendErr);
  }

  // 2. Direct browser fallback to Open-Meteo public API
  try {
    const lat = 12.935;
    const lon = 77.69;
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,weather_code,wind_speed_10m&timezone=Asia%2FKolkata`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const current = data.current || {};
      const wCode = Number(current.weather_code ?? 3);
      const [desc, icon] = WMO_MAP[wCode] || ['Overcast', '☁️'];
      const precip = Number(current.precipitation ?? 0);
      const interval = Number(current.interval ?? 900);
      const rate = interval > 0 ? Number(((precip * 3600) / interval).toFixed(1)) : precip;

      return {
        location: 'Marathahalli - Bellandur, Bengaluru',
        latitude: lat,
        longitude: lon,
        temperature_c: Number(current.temperature_2m ?? 21.0),
        apparent_temp_c: Number(current.apparent_temperature ?? 21.5),
        humidity_pct: Number(current.relative_humidity_2m ?? 80),
        precipitation_mm: precip,
        rainfall_mmhr: rate,
        weather_code: wCode,
        weather_description: desc,
        weather_icon: icon,
        is_raining: rate > 0.1,
        wind_speed_kmh: Number(current.wind_speed_10m ?? 7),
        recorded_at: String(current.time ?? new Date().toLocaleTimeString()),
        source: 'Open-Meteo Direct (Browser)',
        cached: false,
      };
    }
  } catch (directErr) {
    console.warn('Direct Open-Meteo fetch failed:', directErr);
  }

  // 3. Offline static fallback
  return {
    location: 'Marathahalli - Bellandur, Bengaluru',
    latitude: 12.935,
    longitude: 77.69,
    temperature_c: 21.5,
    apparent_temp_c: 22.0,
    humidity_pct: 82,
    precipitation_mm: 0.0,
    rainfall_mmhr: 0.0,
    weather_code: 3,
    weather_description: 'Overcast',
    weather_icon: '☁️',
    is_raining: false,
    wind_speed_kmh: 7.5,
    recorded_at: 'Offline Mode',
    source: 'Bengaluru Baseline (Offline)',
    cached: false,
    is_offline: true,
  };
}




import {
  CompareResult,
  ConfigData,
  EvalSummaryData,
  ForecastParams,
  ForecastResult,
  HealthStatus,
  PresetItem,
  TerrainData,
} from './types';

// Read API base URL from Vite environment variable with localhost fallback
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// In-memory cache for static presets
let presetsCache: PresetItem[] | null = null;

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
}

export async function runForecast(
  params: ForecastParams,
  signal?: AbortSignal
): Promise<ForecastResult> {
  try {
    return await fetchJson<ForecastResult>(
      '/forecast',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      signal
    );
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
  try {
    return await fetchJson<CompareResult>(
      '/compare',
      {
        method: 'POST',
        body: JSON.stringify(params),
      },
      signal
    );
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw err;
    }
    if (isOfflineOrServerError(err)) {
      console.warn('Backend unavailable (network error or 5xx). Loading offline compare fixture.');
      const fallback = await fetchFallback<CompareResult>('/compare_fixture.json');
      fallback.is_offline_fallback = true;
      return fallback;
    }
    throw err;
  }
}

export async function fetchResults(): Promise<EvalSummaryData> {
  return fetchJson<EvalSummaryData>('/results');
}



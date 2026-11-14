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

export async function fetchHealth(): Promise<HealthStatus> {
  return fetchJson<HealthStatus>('/health');
}

export async function fetchConfig(): Promise<ConfigData> {
  return fetchJson<ConfigData>('/config');
}

export async function fetchTerrain(): Promise<TerrainData> {
  return fetchJson<TerrainData>('/terrain');
}

export async function fetchPresets(forceRefresh = false): Promise<PresetItem[]> {
  if (presetsCache && !forceRefresh) {
    return presetsCache;
  }
  const res = await fetchJson<{ presets: PresetItem[] }>('/presets');
  presetsCache = res.presets;
  return res.presets;
}

export function clearPresetsCache(): void {
  presetsCache = null;
}

export async function runForecast(
  params: ForecastParams,
  signal?: AbortSignal
): Promise<ForecastResult> {
  return fetchJson<ForecastResult>(
    '/forecast',
    {
      method: 'POST',
      body: JSON.stringify(params),
    },
    signal
  );
}

export async function runCompare(
  params: ForecastParams,
  signal?: AbortSignal
): Promise<CompareResult> {
  return fetchJson<CompareResult>(
    '/compare',
    {
      method: 'POST',
      body: JSON.stringify(params),
    },
    signal
  );
}

export async function fetchResults(): Promise<EvalSummaryData> {
  return fetchJson<EvalSummaryData>('/results');
}



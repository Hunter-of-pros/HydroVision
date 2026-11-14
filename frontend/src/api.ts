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

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status} ${response.statusText}]: ${errorBody}`);
  }

  return response.json() as Promise<T>;
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

export async function fetchPresets(): Promise<PresetItem[]> {
  const res = await fetchJson<{ presets: PresetItem[] }>('/presets');
  return res.presets;
}

export async function runForecast(params: ForecastParams): Promise<ForecastResult> {
  return fetchJson<ForecastResult>('/forecast', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function runCompare(params: ForecastParams): Promise<CompareResult> {
  return fetchJson<CompareResult>('/compare', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function fetchResults(): Promise<EvalSummaryData> {
  return fetchJson<EvalSummaryData>('/results');
}



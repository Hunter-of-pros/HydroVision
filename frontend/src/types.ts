/**
 * Data contracts and interfaces conforming to docs/CONTRACT.md v1.0
 */

export interface HealthStatus {
  status: string;
  model_loaded: boolean;
  is_mock: boolean;
  contract_version: string;
}

export interface GridConfig {
  rows: number;
  cols: number;
  cell_size_m: number;
}

export interface TimeConfig {
  dt_s: number;
  horizon_steps: number;
}

export interface ParamRange {
  min: number;
  max: number;
  default: number;
}

export interface RainShapeOption {
  allowed: ('constant' | 'triangular' | 'double_peak')[];
  default: 'constant';
}

export interface ConfigData {
  contract_version: string;
  grid: GridConfig;
  time: TimeConfig;
  wet_threshold_m: number;
  params: {
    rain_intensity_mmhr: ParamRange;
    rain_duration_min: ParamRange;
    rain_shape: RainShapeOption;
    drain_capacity_mmhr: ParamRange;
    horizon_steps: ParamRange;
  };
}

export interface TerrainData {
  elevation: number[][]; // 64x64 row 0=north, col 0=west
  dx_m: number;
  bounds: [number, number, number, number]; // [min_lat, min_lon, max_lat, max_lon]
  shape: [number, number];
  min_elevation: number;
  max_elevation: number;
}

export interface ForecastParams {
  rain_intensity_mmhr: number;
  rain_duration_min: number;
  rain_shape: 'constant' | 'triangular' | 'double_peak';
  drain_capacity_mmhr: number;
  horizon_steps: number;
  frame_stride?: number;
}

export interface PresetItem {
  id: string;
  name: string;
  description: string;
  params: ForecastParams;
}

export interface ForecastResult {
  times_s: number[];
  depth_frames: number[][][]; // T x 64 x 64
  rain_series_mmhr: number[];
  peak_depth_m: number;
  flooded_area_m2: number;
  inference_time_ms: number;
  model_name: string;
  frame_stride: number;
  // Additive Contract v1.1 fields
  volume_m3_series?: number[];
  cum_rain_m3_series?: number[];
  cum_drain_m3_series?: number[];
  cum_outflow_m3_series?: number[];
  mass_residual_series?: number[];
}

export interface SolverResult {
  times_s: number[];
  depth_frames: number[][][];
  rain_series_mmhr: number[];
  peak_depth_m: number;
  solve_time_s: number;
  solver_name: string;
  frame_stride: number;
  // Additive Contract v1.1 fields
  volume_m3_series?: number[];
  cum_rain_m3_series?: number[];
  cum_drain_m3_series?: number[];
  cum_outflow_m3_series?: number[];
  mass_residual_series?: number[];
}

export interface ComparisonMetrics {
  mae: number;
  rmse: number;
  peak_depth_error: number;
  wet_iou: number;
  mass_error: number;
  arrival_time_error_s: number;
  speedup: number;
  // Additive Contract v1.1 fields
  mae_series?: number[];
  mass_residual_series?: number[];
  solver_mass_residual_series?: number[];
  peak_extent_iou?: number;
}


export interface CompareResult {
  surrogate: ForecastResult;
  solver: SolverResult;
  metrics: ComparisonMetrics;
  model_name?: string;
}



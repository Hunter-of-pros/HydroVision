"""Pydantic data validation schemas conforming to docs/CONTRACT.md v1.0.

Owner: Backend (Vikas)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health and active model runtime status."""

    status: str = Field(..., json_schema_extra={"example": "ok"})
    model_loaded: bool = Field(..., description="Whether surrogate model weights are loaded in memory.")
    is_mock: bool = Field(..., description="True if mock backend is serving responses.")
    contract_version: str = Field("1.0", description="Contract specification version.")


class GridConfig(BaseModel):
    rows: int = Field(64, description="Grid row count (North to South).")
    cols: int = Field(64, description="Grid column count (West to East).")
    cell_size_m: float = Field(40.0, description="Spatial resolution of each cell in meters.")


class TimeConfig(BaseModel):
    dt_s: int = Field(60, description="Time step duration in seconds.")
    horizon_steps: int = Field(120, description="Total number of prediction intervals.")


class HazardThresholdsConfig(BaseModel):
    source: str = Field(
        "ILLUSTRATIVE, not an official standard",
        description="Source disclaimer regarding classification authority.",
    )
    wet_m: float = Field(0.05, description="Surface runoff wet cell threshold in meters.")
    impassable_m: float = Field(0.15, description="Illustrative vehicle/pedestrian threshold (15 cm).")
    critical_m: float = Field(0.30, description="Illustrative deep inundation threshold (30 cm).")


class ConfigResponse(BaseModel):
    """Simulation parameters and configuration contract."""

    contract_version: str = "1.0"
    grid: GridConfig
    time: TimeConfig
    wet_threshold_m: float = 0.05
    hazard_thresholds: Optional[HazardThresholdsConfig] = None
    params: Dict[str, Any]


class TerrainResponse(BaseModel):
    """Digital Elevation Model and geographic metadata."""

    elevation: List[List[float]] = Field(
        ...,
        description="64x64 2D elevation grid in meters above sea level (row 0 = north, col 0 = west).",
    )
    dx_m: float = Field(40.0, description="Cell size in meters.")
    bounds: List[float] = Field(
        ...,
        description="Geographic boundary [min_lat, min_lon, max_lat, max_lon].",
    )
    shape: List[int] = Field([64, 64], description="Grid dimensions [rows, cols].")
    min_elevation: float = Field(..., description="Minimum elevation in meters.")
    max_elevation: float = Field(..., description="Maximum elevation in meters.")
    is_synthetic: Optional[bool] = Field(
        True,
        description="True if digital elevation model is synthetic/illustrative.",
    )


class ForecastRequest(BaseModel):
    """Simulation input parameters submitted from the frontend UI sliders."""

    rain_intensity_mmhr: float = Field(
        80.0,
        ge=20.0,
        le=150.0,
        description="Peak rainfall rate in mm/hr.",
    )
    rain_duration_min: float = Field(
        45.0,
        ge=15.0,
        le=90.0,
        description="Duration of rainfall event in minutes.",
    )
    rain_shape: Literal["constant", "triangular", "double_peak"] = Field(
        "constant",
        description="Storm hyetograph profile.",
    )
    drain_capacity_mmhr: float = Field(
        0.0,
        ge=0.0,
        le=30.0,
        description="Uniform storm drainage infiltration sink in mm/hr.",
    )
    horizon_steps: int = Field(
        120,
        ge=10,
        le=120,
        description="Number of time steps to simulate (default: 120 steps = 2 hours).",
    )
    frame_stride: int = Field(
        1,
        ge=1,
        le=30,
        description="Temporal subsampling stride for bandwidth optimization (default 1 = all 121 frames).",
    )


class ForecastResponse(BaseModel):
    """Fast surrogate prediction output payload."""

    times_s: List[int] = Field(
        ...,
        description="Elapsed simulation time in seconds for each returned frame (length 121 / stride).",
    )
    depth_frames: List[List[List[float]]] = Field(
        ...,
        description="Water depth in meters for each frame (shape: num_frames x 64 x 64).",
    )
    rain_series_mmhr: List[float] = Field(
        ...,
        description="Rainfall intensity at each interval (length 120).",
    )
    peak_depth_m: float = Field(..., description="Maximum depth in meters across all cells.")
    flooded_area_m2: float = Field(
        ...,
        description="Total surface area with depth >= wet_threshold_m at final frame.",
    )
    inference_time_ms: float = Field(..., description="Surrogate inference latency in milliseconds.")
    model_name: str = Field(..., description="Model identifier used to produce forecast.")
    frame_stride: int = Field(1, description="Stride applied to returned frames.")
    volume_m3_series: Optional[List[float]] = Field(
        None, description="Domain total water volume in m3 per frame (sum(h) * dx * dy)."
    )
    cum_rain_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative precipitation volume in m3."
    )
    cum_drain_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative drainage volume in m3."
    )
    cum_outflow_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative boundary outflow volume in m3."
    )
    mass_residual_series: Optional[List[float]] = Field(
        None, description="Normalized mass conservation residual series over time."
    )


class SolverResponse(BaseModel):
    """High-fidelity numerical solver verification output payload."""

    times_s: List[int]
    depth_frames: List[List[List[float]]]
    rain_series_mmhr: List[float]
    peak_depth_m: float
    solve_time_s: float
    solver_name: str
    frame_stride: int = 1
    volume_m3_series: Optional[List[float]] = Field(
        None, description="Domain total water volume in m3 per frame."
    )
    cum_rain_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative precipitation volume in m3."
    )
    cum_drain_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative drainage volume in m3."
    )
    cum_outflow_m3_series: Optional[List[float]] = Field(
        None, description="Cumulative boundary outflow volume in m3."
    )
    mass_residual_series: Optional[List[float]] = Field(
        None, description="Normalized mass conservation residual series over time."
    )


class MetricsResponse(BaseModel):
    """Verification metrics comparing surrogate forecast against numerical solver."""

    mae: float = Field(..., description="Mean absolute depth error in meters.")
    rmse: float = Field(..., description="Root mean squared depth error in meters.")
    peak_depth_error: float = Field(..., description="Discrepancy in peak water depth in meters.")
    wet_iou: float = Field(..., description="Intersection-over-Union of inundated area (>0.05m).")
    mass_error: float = Field(..., description="Relative mass balance error at final horizon.")
    arrival_time_error_s: float = Field(
        ...,
        description="Discrepancy in wetting front arrival time in seconds.",
    )
    speedup: float = Field(..., description="Speedup factor (solver_time / surrogate_time).")
    mae_series: Optional[List[float]] = Field(
        None, description="Per-frame Mean Absolute Error in meters."
    )
    mass_residual_series: Optional[List[float]] = Field(
        None, description="Mass balance residual series for surrogate."
    )
    solver_mass_residual_series: Optional[List[float]] = Field(
        None, description="Mass balance residual series for solver."
    )
    peak_extent_iou: Optional[float] = Field(
        None, description="Inundation IoU across all cells ever wet during rollout (h >= 0.05m)."
    )



class CompareRequest(ForecastRequest):
    """Request payload to execute both surrogate and solver for side-by-side verification."""

    pass


class CompareResponse(BaseModel):
    """Side-by-side verification payload with formal accuracy and speedup metrics."""

    surrogate: ForecastResponse
    solver: SolverResponse
    metrics: MetricsResponse
    model_name: Optional[str] = Field("mock-v0", description="Surrogate model identifier.")


class PresetItem(BaseModel):
    """Standard predefined weather and infrastructure scenario."""

    id: str
    name: str
    description: str
    params: ForecastRequest


class PresetsResponse(BaseModel):
    presets: List[PresetItem]


class TestSetConfig(BaseModel):
    n_runs: int = Field(50, description="Number of randomized evaluation runs.")
    rain_range_mmhr: List[float] = Field([20.0, 150.0], description="Precipitation range [min, max] in mm/hr.")


class AblationItem(BaseModel):
    name: str = Field(..., description="Ablation configuration name.")
    mae_m: float = Field(..., description="Mean absolute depth error across test set in meters.")
    rmse_m: float = Field(..., description="Root mean squared error in meters.")
    wet_iou: float = Field(..., description="Inundation extent Intersection-over-Union.")
    mass_residual_max: float = Field(..., description="Maximum mass conservation residual.")


class ErrorVsHorizon(BaseModel):
    steps: List[int] = Field(..., description="Time step indices along horizon.")
    mae_m: List[float] = Field(..., description="Per-step MAE across test set in meters.")


class SpeedupScalingItem(BaseModel):
    grid: str = Field(..., description="Grid dimension resolution.")
    solver_s: float = Field(..., description="SWE solver execution time in seconds.")
    surrogate_ms: float = Field(..., description="Surrogate inference latency in milliseconds.")


class EvalSummaryResponse(BaseModel):
    """Empirical evaluation and ablation benchmark summary conforming to docs/eval_summary.schema.json."""

    generated_at: str = Field(..., description="ISO 8601 timestamp of benchmark run.")
    hardware: str = Field(..., description="Compute environment specification.")
    is_mock: bool = Field(..., description="True if results are mock / simulated.")
    test_set: TestSetConfig
    ablation: List[AblationItem]
    error_vs_horizon: ErrorVsHorizon
    speedup_scaling: List[SpeedupScalingItem]



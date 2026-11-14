"""Deterministic mock implementation of hydrovision_ml public API.

Provides working synthetic elevation data, rainfall generation, fast flood rollout,
simulated numerical solver execution, and formal evaluation metrics for offline testing
and frontend/backend parallel development without requiring trained weights.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from hydrovision_ml.config import (
    CELL_SIZE_M,
    COLS,
    CONTRACT_VERSION,
    DT_S,
    HORIZON_STEPS,
    NUM_FRAMES,
    ROWS,
    WET_THRESHOLD_M,
)

_MOCK_LOADED: bool = True
_RANDOM_SEED: int = 42


def _generate_synthetic_dem() -> np.ndarray:
    """Generate a deterministic 64x64 synthetic DEM.

    Features:
    - Gentle regional slope descending from North-West (row 0, col 0) to South-East (row 63, col 63).
    - Two natural catchment basins/bowls that pool runoff.
    """
    rows = ROWS
    cols = COLS
    r_idx, c_idx = np.indices((rows, cols))

    # Regional slope: 100m in NW down to ~81m in SE
    base = 100.0 - 0.15 * (r_idx + c_idx)

    # Bowl 1 (primary retention basin in SE sector)
    dist1_sq = (r_idx - 42) ** 2 + (c_idx - 42) ** 2
    bowl1 = 4.5 * np.exp(-dist1_sq / (2.0 * (6.0 ** 2)))

    # Bowl 2 (secondary depression in East sector)
    dist2_sq = (r_idx - 20) ** 2 + (c_idx - 48) ** 2
    bowl2 = 3.2 * np.exp(-dist2_sq / (2.0 * (5.0 ** 2)))

    dem = base - bowl1 - bowl2
    return np.round(dem, 2)


_SYNTHETIC_DEM: np.ndarray = _generate_synthetic_dem()


def _build_rain_series(
    duration_min: float,
    intensity_mmhr: float,
    shape: str = "constant",
    total_steps: int = HORIZON_STEPS,
    dt_s: float = float(DT_S),
) -> List[float]:
    """Generate deterministic hyetograph of rainfall intensity for each 60s step."""
    duration_steps = min(total_steps, max(1, int(round((duration_min * 60.0) / dt_s))))
    series = np.zeros(total_steps, dtype=np.float64)

    if shape == "triangular":
        half = max(1, duration_steps // 2)
        for i in range(duration_steps):
            if i <= half:
                series[i] = intensity_mmhr * (i / half)
            else:
                series[i] = intensity_mmhr * max(0.0, 1.0 - (i - half) / (duration_steps - half))
    elif shape == "double_peak":
        p1 = max(1, duration_steps // 3)
        p2 = max(1, 2 * duration_steps // 3)
        for i in range(duration_steps):
            w1 = np.exp(-((i - p1) ** 2) / (2.0 * (max(1.0, duration_steps / 8.0) ** 2)))
            w2 = np.exp(-((i - p2) ** 2) / (2.0 * (max(1.0, duration_steps / 8.0) ** 2)))
            series[i] = intensity_mmhr * min(1.0, float(w1 + 0.8 * w2))
    else:  # constant
        series[:duration_steps] = intensity_mmhr

    return [round(float(v), 2) for v in series]


def load_all(model_path: str = "artifacts/models/best.pt") -> None:
    """Mock load: sets internal loaded flag to True."""
    global _MOCK_LOADED
    _MOCK_LOADED = True


def get_config() -> Dict[str, Any]:
    """Return project configuration dict."""
    from hydrovision_ml.config import CONFIG
    return CONFIG


def get_terrain() -> Dict[str, Any]:
    """Return synthetic 64x64 DEM and spatial metadata."""
    dem = _SYNTHETIC_DEM
    return {
        "elevation": dem.tolist(),
        "dx_m": float(CELL_SIZE_M),
        "bounds": [12.920, 77.560, 12.943, 77.583],
        "shape": [ROWS, COLS],
        "min_elevation": float(np.min(dem)),
        "max_elevation": float(np.max(dem)),
    }


def _simulate_water_spread(
    rain_series: List[float],
    drain_capacity_mmhr: float,
    horizon_steps: int,
    noise_seed: Optional[int] = None,
) -> Tuple[List[List[List[float]]], float, float]:
    """Simulate water depth accumulation and spreading over terrain."""
    dem = _SYNTHETIC_DEM
    min_elev = float(np.min(dem))
    max_elev = float(np.max(dem))
    elev_range = max(1.0, max_elev - min_elev)

    # Relative depression factor: lowest cells get maximum ponding weight
    low_factor = (max_elev - dem) / elev_range
    ponding_weight = (low_factor ** 2.2) * 3.5

    frames: List[List[List[float]]] = []
    # Frame 0: Dry terrain (depth is identically 0.0 everywhere)
    frame0 = np.zeros((ROWS, COLS), dtype=np.float64)
    frames.append(np.round(frame0, 3).tolist())

    rng = np.random.RandomState(noise_seed) if noise_seed is not None else None
    cumulative_water_m = 0.0

    for step in range(horizon_steps):
        rain_rate = rain_series[step] if step < len(rain_series) else 0.0
        # Convert mm/hr into meters added during this dt interval (60s)
        rain_depth_m = (rain_rate / 1000.0) * (DT_S / 3600.0)
        drain_depth_m = (drain_capacity_mmhr / 1000.0) * (DT_S / 3600.0)
        net_m = max(0.0, rain_depth_m - drain_depth_m)
        cumulative_water_m += net_m

        # Natural infiltration / recession if net input is zero
        if net_m == 0.0 and cumulative_water_m > 0.0:
            cumulative_water_m = max(0.0, cumulative_water_m - 0.00005)

        # Spatial accumulation with outward diffusion as water accumulates
        current_depth = cumulative_water_m * ponding_weight

        # Optional perturbation for solver imitation
        if rng is not None:
            spatial_jitter = rng.uniform(-0.015, 0.015, size=(ROWS, COLS))
            current_depth = current_depth + spatial_jitter * (current_depth > 0.01)

        # Enforce non-negativity and finite bounds
        current_depth = np.clip(current_depth, 0.0, 6.0)
        current_depth = np.nan_to_num(current_depth, nan=0.0, posinf=6.0, neginf=0.0)

        frames.append(np.round(current_depth, 3).tolist())

    all_frames_arr = np.array(frames)
    peak_depth = float(np.max(all_frames_arr))
    # Final frame flooded area (cells > 0.05m * cell_area)
    wet_cells_final = int(np.sum(all_frames_arr[-1] > WET_THRESHOLD_M))
    flooded_area = float(wet_cells_final * CELL_SIZE_M * CELL_SIZE_M)

    return frames, peak_depth, flooded_area


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mock fast neural surrogate forecast.

    Produces exactly 121 frames of 64x64 water depth in meters.
    """
    rain_intensity = float(params.get("rain_intensity_mmhr", 80.0))
    rain_duration = float(params.get("rain_duration_min", 45.0))
    rain_shape = str(params.get("rain_shape", "constant"))
    drain_capacity = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = int(params.get("horizon_steps", HORIZON_STEPS))

    rain_series = _build_rain_series(
        duration_min=rain_duration,
        intensity_mmhr=rain_intensity,
        shape=rain_shape,
        total_steps=horizon_steps,
    )

    frames, peak_depth, flooded_area = _simulate_water_spread(
        rain_series=rain_series,
        drain_capacity_mmhr=drain_capacity,
        horizon_steps=horizon_steps,
        noise_seed=None,
    )

    times_s = [i * DT_S for i in range(horizon_steps + 1)]

    return {
        "times_s": times_s,
        "depth_frames": frames,
        "rain_series_mmhr": rain_series,
        "peak_depth_m": round(peak_depth, 3),
        "flooded_area_m2": round(flooded_area, 1),
        "inference_time_ms": 38.5,
        "model_name": "mock-v0",
    }


def forecast_batch(params_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute batched mock forecast."""
    results = [forecast(p) for p in params_list]
    total_time = sum(r["inference_time_ms"] for r in results)
    return {
        "batch": results,
        "total_inference_time_ms": round(total_time, 2),
    }


def run_solver(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mock 2D SWE numerical solver.

    Sleeps 1.5s to imitate full hydrodynamic simulation and returns
    a slightly perturbed ground-truth depth field.
    """
    time.sleep(1.5)

    rain_intensity = float(params.get("rain_intensity_mmhr", 80.0))
    rain_duration = float(params.get("rain_duration_min", 45.0))
    rain_shape = str(params.get("rain_shape", "constant"))
    drain_capacity = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = int(params.get("horizon_steps", HORIZON_STEPS))

    rain_series = _build_rain_series(
        duration_min=rain_duration,
        intensity_mmhr=rain_intensity,
        shape=rain_shape,
        total_steps=horizon_steps,
    )

    frames, peak_depth, _ = _simulate_water_spread(
        rain_series=rain_series,
        drain_capacity_mmhr=drain_capacity,
        horizon_steps=horizon_steps,
        noise_seed=_RANDOM_SEED,
    )

    times_s = [i * DT_S for i in range(horizon_steps + 1)]

    return {
        "times_s": times_s,
        "depth_frames": frames,
        "rain_series_mmhr": rain_series,
        "peak_depth_m": round(peak_depth, 3),
        "solve_time_s": 1.52,
        "solver_name": "swe-local-inertial-mock",
    }


def compute_metrics(
    surrogate_frames: Any,
    solver_frames: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute formal evaluation metrics between surrogate and solver depth fields."""
    pred = np.asarray(surrogate_frames, dtype=np.float64)
    true = np.asarray(solver_frames, dtype=np.float64)

    # MAE and RMSE over all cells and all frames
    diff = pred - true
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))

    # Peak depth error
    pred_peak = float(np.max(pred))
    true_peak = float(np.max(true))
    peak_depth_err = float(abs(pred_peak - true_peak))

    # Wet IoU on the final time frame
    pred_wet = pred[-1] >= WET_THRESHOLD_M
    true_wet = true[-1] >= WET_THRESHOLD_M
    intersection = int(np.logical_and(pred_wet, true_wet).sum())
    union = int(np.logical_or(pred_wet, true_wet).sum())
    wet_iou = float(intersection / union) if union > 0 else 1.0

    # Mass balance relative error at final frame
    cell_area = CELL_SIZE_M * CELL_SIZE_M
    pred_vol = float(np.sum(pred[-1]) * cell_area)
    true_vol = float(np.sum(true[-1]) * cell_area)
    mass_err = float(abs(pred_vol - true_vol) / max(true_vol, 1e-6))

    # Wetting front arrival time (time frame where max depth first exceeds wet_threshold_m)
    def _find_arrival(arr: np.ndarray) -> int:
        for idx in range(arr.shape[0]):
            if np.max(arr[idx]) >= WET_THRESHOLD_M:
                return idx
        return arr.shape[0] - 1

    t_arr_pred = _find_arrival(pred) * DT_S
    t_arr_true = _find_arrival(true) * DT_S
    arrival_err_s = float(abs(t_arr_pred - t_arr_true))

    # Speedup: simulated 1.52s / 0.0385s ~ 39.5x
    speedup = 39.5

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "peak_depth_error": round(peak_depth_err, 4),
        "wet_iou": round(wet_iou, 4),
        "mass_error": round(mass_err, 4),
        "arrival_time_error_s": round(arrival_err_s, 1),
        "speedup": round(speedup, 1),
    }


def get_model_info() -> Dict[str, Any]:
    """Return model runtime metadata."""
    return {
        "model_name": "mock-v0",
        "is_mock": True,
        "device": "cpu",
        "checkpoint_path": "hydrovision_ml/mock.py",
        "contract_version": CONTRACT_VERSION,
        "parameters_count": 0,
    }


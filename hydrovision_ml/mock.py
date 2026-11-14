"""Deterministic mock implementation of hydrovision_ml public API.

Provides working synthetic elevation data, rainfall generation, fast flood rollout,
simulated numerical solver execution, and formal evaluation metrics for offline testing
and frontend/backend parallel development without requiring trained weights.

Implements Contract v1.0 and additive Contract v1.1 conservation budget series.
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
) -> Tuple[List[List[List[float]]], float, float, Dict[str, List[float]]]:
    """Simulate water depth accumulation and mass balance over terrain.

    Returns
    -------
    frames : list of 2D grids (length horizon_steps + 1)
    peak_depth : float
    flooded_area : float
    budget : dict with volume_m3_series, cum_rain_m3_series, cum_drain_m3_series,
             cum_outflow_m3_series, mass_residual_series
    """
    dem = _SYNTHETIC_DEM
    min_elev = float(np.min(dem))
    max_elev = float(np.max(dem))
    elev_range = max(1.0, max_elev - min_elev)

    # Relative depression factor: lowest cells get maximum ponding weight
    low_factor = (max_elev - dem) / elev_range
    raw_weights = (low_factor ** 2.2) * 3.5
    base_weights = raw_weights / np.sum(raw_weights)

    cell_area = float(CELL_SIZE_M * CELL_SIZE_M)
    total_area = float(ROWS * COLS * cell_area)

    frames: List[List[List[float]]] = []
    # Frame 0: Dry terrain (depth is identically 0.0 everywhere)
    frame0 = np.zeros((ROWS, COLS), dtype=np.float64)
    frames.append(frame0.tolist())

    volume_series: List[float] = [0.0]
    cum_rain_series: List[float] = [0.0]
    cum_drain_series: List[float] = [0.0]
    cum_outflow_series: List[float] = [0.0]
    mass_residual_series: List[float] = [0.0]

    cum_rain_m3 = 0.0
    cum_drain_m3 = 0.0
    cum_outflow_m3 = 0.0
    current_vol_m3 = 0.0

    rng = np.random.RandomState(noise_seed) if noise_seed is not None else None

    for step in range(horizon_steps):
        rain_rate = rain_series[step] if step < len(rain_series) else 0.0
        # Rainfall volume added during this dt interval (60s)
        delta_rain_vol = (rain_rate / 1000.0) * (DT_S / 3600.0) * total_area
        cum_rain_m3 += delta_rain_vol

        # Drainage potential during this dt interval
        delta_drain_pot = (drain_capacity_mmhr / 1000.0) * (DT_S / 3600.0) * total_area
        avail_water = current_vol_m3 + delta_rain_vol
        delta_drain_vol = min(avail_water, delta_drain_pot)
        cum_drain_m3 += delta_drain_vol

        # Domain boundary outflow (closed boundary condition: 0.0)
        cum_outflow_m3 += 0.0

        # Expected mass-conserved water volume
        expected_vol_m3 = max(0.0, cum_rain_m3 - cum_drain_m3 - cum_outflow_m3)
        current_vol_m3 = expected_vol_m3

        # Spatial distribution across grid
        if rng is not None:
            # Solver simulation: small spatial perturbation but strictly re-normalized to conserve mass
            perturb = rng.uniform(-0.015, 0.015, size=(ROWS, COLS))
            distrib = np.maximum(0.0, base_weights + perturb * (base_weights > 0.0001))
            solver_weights = distrib / np.sum(distrib)
            current_depth = (expected_vol_m3 / cell_area) * solver_weights
        else:
            # Surrogate forecast: slightly diffuse distribution imitating surrogate inference
            current_depth = (expected_vol_m3 / cell_area) * base_weights
            # Small realistic neural surrogate perturbation (reporting truthful residual)
            drift_factor = 1.0 + 0.002 * math.sin(step / 10.0)
            current_depth = current_depth * drift_factor

        # Guard against NaNs or negative depths
        current_depth = np.maximum(0.0, current_depth)
        current_depth = np.nan_to_num(current_depth, nan=0.0, posinf=6.0, neginf=0.0)

        # Actual volume on the grid
        actual_vol = float(np.sum(current_depth) * cell_area)
        
        # Calculate truthful mass residual
        if cum_rain_m3 > 1e-6:
            mass_res = float(abs(actual_vol - expected_vol_m3) / cum_rain_m3)
        else:
            mass_res = 0.0

        frames.append(current_depth.tolist())
        volume_series.append(round(actual_vol, 2))
        cum_rain_series.append(round(cum_rain_m3, 2))
        cum_drain_series.append(round(cum_drain_m3, 2))
        cum_outflow_series.append(round(cum_outflow_m3, 2))
        mass_residual_series.append(mass_res)

    all_frames_arr = np.array(frames)
    peak_depth = float(np.max(all_frames_arr))
    # Final frame flooded area (cells > 0.05m * cell_area)
    wet_cells_final = int(np.sum(all_frames_arr[-1] >= WET_THRESHOLD_M))
    flooded_area = float(wet_cells_final * cell_area)

    budget_dict = {
        "volume_m3_series": volume_series,
        "cum_rain_m3_series": cum_rain_series,
        "cum_drain_m3_series": cum_drain_series,
        "cum_outflow_m3_series": cum_outflow_series,
        "mass_residual_series": mass_residual_series,
    }

    return frames, peak_depth, flooded_area, budget_dict


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mock fast neural surrogate forecast.

    Produces exactly 121 frames of 64x64 water depth in meters with additive v1.1 series.
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

    frames, peak_depth, flooded_area, budget = _simulate_water_spread(
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
        "volume_m3_series": budget["volume_m3_series"],
        "cum_rain_m3_series": budget["cum_rain_m3_series"],
        "cum_drain_m3_series": budget["cum_drain_m3_series"],
        "cum_outflow_m3_series": budget["cum_outflow_m3_series"],
        "mass_residual_series": budget["mass_residual_series"],
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
    a slightly perturbed ground-truth depth field that strictly conserves mass.
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

    frames, peak_depth, _, budget = _simulate_water_spread(
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
        "volume_m3_series": budget["volume_m3_series"],
        "cum_rain_m3_series": budget["cum_rain_m3_series"],
        "cum_drain_m3_series": budget["cum_drain_m3_series"],
        "cum_outflow_m3_series": budget["cum_outflow_m3_series"],
        "mass_residual_series": budget["mass_residual_series"],
    }


def compute_metrics(
    surrogate_frames: Any,
    solver_frames: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute formal evaluation metrics between surrogate and solver depth fields.

    Includes all 7 v1.0 metrics plus additive v1.1 conservation & stability metrics:
    mae_series, mass_residual_series, solver_mass_residual_series, and peak_extent_iou.
    """
    pred = np.asarray(surrogate_frames, dtype=np.float64)
    true = np.asarray(solver_frames, dtype=np.float64)

    num_frames = pred.shape[0]
    cell_area = float(CELL_SIZE_M * CELL_SIZE_M)
    total_area = float(ROWS * COLS * cell_area)

    # 1. MAE and RMSE over all cells and all frames
    diff = pred - true
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))

    # Per-frame MAE series [121]
    mae_series = [float(np.mean(np.abs(diff[t]))) for t in range(num_frames)]

    # 2. Peak depth error
    pred_peak = float(np.max(pred))
    true_peak = float(np.max(true))
    peak_depth_err = float(abs(pred_peak - true_peak))

    # 3. Wet IoU on the final time frame (v1.0 Metric 4)
    pred_wet = pred[-1] >= WET_THRESHOLD_M
    true_wet = true[-1] >= WET_THRESHOLD_M
    intersection = int(np.logical_and(pred_wet, true_wet).sum())
    union = int(np.logical_or(pred_wet, true_wet).sum())
    wet_iou = float(intersection / union) if union > 0 else 1.0

    # 4. Peak Extent IoU across all frames (v1.1 Additive Metric)
    pred_ever_wet = np.any(pred >= WET_THRESHOLD_M, axis=0)
    true_ever_wet = np.any(true >= WET_THRESHOLD_M, axis=0)
    peak_intersection = int(np.logical_and(pred_ever_wet, true_ever_wet).sum())
    peak_union = int(np.logical_or(pred_ever_wet, true_ever_wet).sum())
    peak_extent_iou = float(peak_intersection / peak_union) if peak_union > 0 else 1.0

    # 5. Mass balance relative error at final frame (v1.0 Metric 5 - Final volume agreement)
    pred_vol_final = float(np.sum(pred[-1]) * cell_area)
    true_vol_final = float(np.sum(true[-1]) * cell_area)
    mass_err = float(abs(pred_vol_final - true_vol_final) / max(true_vol_final, 1e-6))

    # Reconstruct input rain and drain budget for residual series
    rain_duration = float(params.get("rain_duration_min", 45.0))
    rain_intensity = float(params.get("rain_intensity_mmhr", 80.0))
    rain_shape = str(params.get("rain_shape", "constant"))
    drain_capacity = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = num_frames - 1

    rain_series = _build_rain_series(
        duration_min=rain_duration,
        intensity_mmhr=rain_intensity,
        shape=rain_shape,
        total_steps=horizon_steps,
    )

    surr_residuals: List[float] = [0.0]
    solv_residuals: List[float] = [0.0]
    cum_rain = 0.0
    cum_drain = 0.0
    curr_expected_vol = 0.0

    for step in range(horizon_steps):
        r_mmhr = rain_series[step] if step < len(rain_series) else 0.0
        delta_rain = (r_mmhr / 1000.0) * (DT_S / 3600.0) * total_area
        cum_rain += delta_rain

        delta_drain_pot = (drain_capacity / 1000.0) * (DT_S / 3600.0) * total_area
        avail = curr_expected_vol + delta_rain
        delta_drain = min(avail, delta_drain_pot)
        cum_drain += delta_drain

        expected_vol = max(0.0, cum_rain - cum_drain)
        curr_expected_vol = expected_vol

        v_pred_t = float(np.sum(pred[step + 1]) * cell_area)
        v_true_t = float(np.sum(true[step + 1]) * cell_area)

        denom = max(cum_rain, 1e-6)
        surr_res = float(abs(v_pred_t - expected_vol) / denom)
        solv_res = float(abs(v_true_t - expected_vol) / denom)

        surr_residuals.append(surr_res)
        solv_residuals.append(solv_res)

    # 6. Wetting front arrival time
    def _find_arrival(arr: np.ndarray) -> int:
        for idx in range(arr.shape[0]):
            if np.max(arr[idx]) >= WET_THRESHOLD_M:
                return idx
        return arr.shape[0] - 1

    t_arr_pred = _find_arrival(pred) * DT_S
    t_arr_true = _find_arrival(true) * DT_S
    arrival_err_s = float(abs(t_arr_pred - t_arr_true))

    # 7. Speedup
    speedup = 39.5

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "peak_depth_error": round(peak_depth_err, 4),
        "wet_iou": round(wet_iou, 4),
        "mass_error": round(mass_err, 4),
        "arrival_time_error_s": round(arrival_err_s, 1),
        "speedup": round(speedup, 1),
        "mae_series": [round(v, 5) for v in mae_series],
        "mass_residual_series": surr_residuals,
        "solver_mass_residual_series": solv_residuals,
        "peak_extent_iou": round(peak_extent_iou, 4),
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

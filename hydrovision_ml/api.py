"""Public API interface for hydrovision_ml.

This module defines the production contract between the ML pipeline and the backend.
Wired to the trained baseline neural surrogate (best.pt), the 2D SWE numerical solver,
and the real Marathahalli-Bellandur Copernicus DEM (60.9 m resolution).

Contract conventions:
- Grid shape: 64 rows x 64 columns
- Orientation: row 0 = North, column 0 = West
- Temporal horizon: 120 steps with dt=60s -> 121 output frames (t=0 to t=7200s)
- Rain series length: 120 steps (one precipitation value per interval)
- Units: Water depth in meters (m), Rainfall intensity in mm/hr, Cell size in meters (60.9m)

Phase: Phase 4 & Phase 6 (Wired Real Production API)
Owner: ML Teammate
Contract: docs/CONTRACT.md v1.0
"""

from __future__ import annotations

import os
from pathlib import Path
import platform
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn

from hydrovision_ml.config import (
    CELL_SIZE_M,
    COLS,
    CONFIG,
    CONTRACT_VERSION,
    DT_S,
    HORIZON_STEPS,
    ROWS,
    WET_THRESHOLD_M,
)
from hydrovision_ml.eval.metrics import compute_all_metrics
from hydrovision_ml.solver.scenarios import make_rain_series
from hydrovision_ml.solver.swe_solver import run_solver_core
from hydrovision_ml.surrogate.model import Normalizer, UNetSurrogate
from hydrovision_ml.surrogate.rollout import rollout, rollout_batched
from hydrovision_ml.terrain.dem import load_terrain

class ForecastResult(dict):
    """Contract-compliant dictionary supporting both JSON serialization and ndarray access."""

    def __getitem__(self, key: str) -> Any:
        if key == "depth_frames_m":
            return np.asarray(super().__getitem__("depth_frames"), dtype=np.float32)
        return super().__getitem__(key)

    @property
    def depth_frames_m(self) -> np.ndarray:
        return np.asarray(super().__getitem__("depth_frames"), dtype=np.float32)


class BatchForecastResult(dict):
    """Contract-compliant dictionary for batched forecast."""

    def __getitem__(self, key: str) -> Any:
        if key == "depth_frames_m":
            return np.asarray(super().__getitem__("depth_frames"), dtype=np.float32)
        return super().__getitem__(key)

    @property
    def depth_frames_m(self) -> np.ndarray:
        return np.asarray(super().__getitem__("depth_frames"), dtype=np.float32)
MEASURED_SOLVER_TIME_S: float = 0.2894       # Median 10 scenarios (289.4 ms)
MEASURED_SURROGATE_TIME_S: float = 0.5816    # Median 120-step rollout (581.6 ms)
MEASURED_SPEEDUP: float = round(MEASURED_SOLVER_TIME_S / MEASURED_SURROGATE_TIME_S, 2)  # 0.50x


class ModelNotFoundError(FileNotFoundError):
    """Raised when the specified neural surrogate model checkpoint file is missing."""
    pass


# Global module caches
_CACHED_TERRAIN: Optional[Dict[str, Any]] = None
_CACHED_DEM_ARRAY: Optional[np.ndarray] = None
_MODEL: Optional[UNetSurrogate] = None
_NORMALIZER: Optional[Normalizer] = None
_MODEL_PATH: str = "artifacts/models/best.pt"
_MODEL_LOADED: bool = False
_GIT_COMMIT: str = "unknown"
_PARAM_COUNT: int = 0


def load_all(model_path: str = "artifacts/models/best.pt") -> None:
    """Load neural surrogate weights, normalization parameters, and static terrain into memory.

    Parameters
    ----------
    model_path : str
        Path to the trained PyTorch surrogate checkpoint (.pt file).

    Raises
    ------
    ModelNotFoundError
        If the checkpoint file does not exist at model_path.
    """
    global _CACHED_TERRAIN, _CACHED_DEM_ARRAY, _MODEL, _NORMALIZER
    global _MODEL_PATH, _MODEL_LOADED, _GIT_COMMIT, _PARAM_COUNT

    ckpt_file = Path(model_path)
    if not ckpt_file.is_file():
        raise ModelNotFoundError(f"Surrogate model checkpoint not found at: {model_path}")

    # Set CPU threads to 8 per contract and speed benchmark
    torch.set_num_threads(8)

    # 1. Load terrain once
    _CACHED_TERRAIN = load_terrain()
    _CACHED_DEM_ARRAY = np.array(_CACHED_TERRAIN["elevation"], dtype=np.float32)

    # 2. Load surrogate checkpoint
    ckpt = torch.load(str(ckpt_file), map_location="cpu", weights_only=False)
    config = ckpt.get("model_config", {
        "in_channels": 7,
        "out_channels": 1,
        "base_ch": 26,
        "padding_mode": "reflect",
    })
    model = UNetSurrogate(**config)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    if "normalizer" in ckpt:
        normalizer = Normalizer.from_dict(ckpt["normalizer"])
    else:
        normalizer = Normalizer.load()

    _MODEL = model
    _NORMALIZER = normalizer
    _MODEL_PATH = str(model_path)
    _GIT_COMMIT = str(ckpt.get("git_commit", "unknown"))
    _PARAM_COUNT = sum(p.numel() for p in model.parameters() if p.requires_grad)
    _MODEL_LOADED = True


def _ensure_loaded() -> None:
    """Ensure model, normalizer, and terrain are initialized."""
    global _MODEL_LOADED
    if not _MODEL_LOADED:
        load_all()


def get_config() -> Dict[str, Any]:
    """Retrieve global simulation configuration and parameter boundaries."""
    return CONFIG


def get_terrain() -> Dict[str, Any]:
    """Retrieve static elevation data and spatial metadata conforming to CONTRACT.md get_terrain()."""
    global _CACHED_TERRAIN, _CACHED_DEM_ARRAY
    if _CACHED_TERRAIN is None:
        _CACHED_TERRAIN = load_terrain()
        _CACHED_DEM_ARRAY = np.array(_CACHED_TERRAIN["elevation"], dtype=np.float32)
    return _CACHED_TERRAIN


def _validate_params(params: Dict[str, Any]) -> None:
    """Validate scenario parameters strictly against config.json boundaries."""
    # rain_intensity_mmhr: 20 to 150
    intensity = float(params.get("rain_intensity_mmhr", 80.0))
    if not (20.0 <= intensity <= 150.0):
        raise ValueError(f"rain_intensity_mmhr must be between 20.0 and 150.0 mm/hr, got {intensity}")

    # rain_duration_min: 15 to 90
    duration = float(params.get("rain_duration_min", 45.0))
    if not (15.0 <= duration <= 90.0):
        raise ValueError(f"rain_duration_min must be between 15.0 and 90.0 minutes, got {duration}")

    # rain_shape: 'constant' | 'triangular' | 'double_peak'
    shape = str(params.get("rain_shape", "constant"))
    if shape not in ["constant", "triangular", "double_peak"]:
        raise ValueError(f"rain_shape must be one of ['constant', 'triangular', 'double_peak'], got '{shape}'")

    # drain_capacity_mmhr: 0 to 30
    drain = float(params.get("drain_capacity_mmhr", 0.0))
    if not (0.0 <= drain <= 30.0):
        raise ValueError(f"drain_capacity_mmhr must be between 0.0 and 30.0 mm/hr, got {drain}")

    # horizon_steps: 10 to 120
    horizon = int(params.get("horizon_steps", HORIZON_STEPS))
    if not (10 <= horizon <= 120):
        raise ValueError(f"horizon_steps must be between 10 and 120 steps, got {horizon}")


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute fast neural surrogate inference to predict water depth evolution.

    Parameters
    ----------
    params : dict
        - rain_intensity_mmhr : float [20.0, 150.0]
        - rain_duration_min : float [15.0, 90.0]
        - rain_shape : str ("constant" | "triangular" | "double_peak")
        - drain_capacity_mmhr : float [0.0, 30.0]
        - horizon_steps : int [10, 120] (default: 120)

    Returns
    -------
    dict
        Surrogate forecast conforming to CONTRACT.md Section 3:
        - times_s : list[int]
        - depth_frames : list[list[list[float]]] (shape: [121, 64, 64])
        - depth_frames_m : np.ndarray (shape: [121, 64, 64])
        - rain_series_mmhr : list[float] (length 120)
        - peak_depth_m : float
        - flooded_area_m2 : float
        - inference_time_ms : float
        - runtime_ms : float
        - model_name : str
    """
    _ensure_loaded()
    _validate_params(params)

    intensity = float(params.get("rain_intensity_mmhr", 80.0))
    duration = float(params.get("rain_duration_min", 45.0))
    shape = str(params.get("rain_shape", "constant"))
    drain = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = int(params.get("horizon_steps", HORIZON_STEPS))

    # Generate exact rain series (length 120)
    rain_series = make_rain_series(
        duration_min=duration,
        intensity_mmhr=intensity,
        shape=shape,
        dt_s=float(DT_S),
        total_steps=horizon_steps,
    )

    # Execute trained surrogate rollout
    assert _MODEL is not None
    assert _CACHED_DEM_ARRAY is not None
    assert _NORMALIZER is not None

    rollout_res = rollout(
        model=_MODEL,
        terrain=_CACHED_DEM_ARRAY,
        rain_series=rain_series,
        drain_capacity_mmhr=drain,
        normalizer=_NORMALIZER,
        cell_size_m=float(CELL_SIZE_M),
        horizon_steps=horizon_steps,
        device="cpu",
    )

    depth_frames_arr = rollout_res["depth_frames"]  # (121, 64, 64) in float32
    inf_time_ms = round(float(rollout_res["inference_time_s"] * 1000.0), 1)

    # Physical guarantees: frame 0 dry, non-negative, no NaNs
    depth_frames_arr[0] = 0.0
    depth_frames_arr = np.nan_to_num(depth_frames_arr, nan=0.0, posinf=0.0, neginf=0.0)
    depth_frames_arr = np.maximum(depth_frames_arr, 0.0)

    times_s = [int(i * int(DT_S)) for i in range(horizon_steps + 1)]
    peak_depth = float(np.max(depth_frames_arr))
    final_frame = depth_frames_arr[-1]
    flooded_cells = int(np.sum(final_frame >= float(WET_THRESHOLD_M)))
    flooded_area = float(flooded_cells * (float(CELL_SIZE_M) ** 2))

    frames_list = [frame.tolist() for frame in depth_frames_arr]

    return ForecastResult({
        "times_s": times_s,
        "depth_frames": frames_list,
        "rain_series_mmhr": [float(r) for r in rain_series],
        "peak_depth_m": round(peak_depth, 3),
        "flooded_area_m2": round(flooded_area, 1),
        "inference_time_ms": inf_time_ms,
        "runtime_ms": inf_time_ms,
        "model_name": "unet-surrogate-v1",
    })


def forecast_batch(params_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute batched neural surrogate inference across multiple rainfall scenarios.

    Parameters
    ----------
    params_list : list[dict]
        List of scenario parameter dictionaries.

    Returns
    -------
    dict
        - depth_frames : list[list[list[list[float]]]] of shape [N, 121, 64, 64]
        - depth_frames_m : np.ndarray of shape (N, 121, 64, 64)
        - runtime_ms : float
        - inference_time_ms : float
        - model_name : str
    """
    _ensure_loaded()
    if not params_list:
        return {
            "depth_frames": [],
            "depth_frames_m": np.empty((0, 121, 64, 64), dtype=np.float32),
            "runtime_ms": 0.0,
            "inference_time_ms": 0.0,
            "model_name": "unet-surrogate-v1",
        }

    for p in params_list:
        _validate_params(p)

    N = len(params_list)
    rain_batch = np.zeros((N, HORIZON_STEPS), dtype=np.float32)
    drain_capacities = np.zeros(N, dtype=np.float32)

    for i, p in enumerate(params_list):
        r_series = make_rain_series(
            duration_min=float(p.get("rain_duration_min", 45.0)),
            intensity_mmhr=float(p.get("rain_intensity_mmhr", 80.0)),
            shape=str(p.get("rain_shape", "constant")),
            dt_s=float(DT_S),
            total_steps=HORIZON_STEPS,
        )
        rain_batch[i] = r_series
        drain_capacities[i] = float(p.get("drain_capacity_mmhr", 0.0))

    assert _MODEL is not None
    assert _CACHED_DEM_ARRAY is not None
    assert _NORMALIZER is not None

    t0 = time.perf_counter()
    rollout_res = rollout_batched(
        model=_MODEL,
        terrain=_CACHED_DEM_ARRAY,
        rain_batch=rain_batch,
        drain_capacities=drain_capacities,
        normalizer=_NORMALIZER,
        cell_size_m=float(CELL_SIZE_M),
        horizon_steps=HORIZON_STEPS,
        device="cpu",
    )
    total_time_ms = round(float(time.perf_counter() - t0) * 1000.0, 1)

    batch_depth_arr = rollout_res["depth_frames"]  # (N, 121, 64, 64)
    batch_depth_arr[:, 0] = 0.0
    batch_depth_arr = np.nan_to_num(batch_depth_arr, nan=0.0, posinf=0.0, neginf=0.0)
    batch_depth_arr = np.maximum(batch_depth_arr, 0.0)

    frames_nested = [[frame.tolist() for frame in sc] for sc in batch_depth_arr]

    return BatchForecastResult({
        "depth_frames": frames_nested,
        "runtime_ms": total_time_ms,
        "inference_time_ms": total_time_ms,
        "model_name": "unet-surrogate-v1",
    })


def run_solver(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute high-fidelity 2D Shallow Water Equations (SWE) numerical solver.

    Parameters
    ----------
    params : dict
        Simulation parameters.

    Returns
    -------
    dict
        Numerical solver ground-truth output matching CONTRACT.md schema.
    """
    _validate_params(params)

    intensity = float(params.get("rain_intensity_mmhr", 80.0))
    duration = float(params.get("rain_duration_min", 45.0))
    shape = str(params.get("rain_shape", "constant"))
    drain = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = int(params.get("horizon_steps", HORIZON_STEPS))

    terrain = get_terrain()
    dem = np.array(terrain["elevation"], dtype=np.float64)

    rain_series = make_rain_series(
        duration_min=duration,
        intensity_mmhr=intensity,
        shape=shape,
        dt_s=float(DT_S),
        total_steps=horizon_steps,
    )

    res = run_solver_core(
        dem=dem,
        rain_series_mmhr=rain_series,
        dt_s=float(DT_S),
        drain_capacity_mmhr=drain,
        cell_size_m=float(CELL_SIZE_M),
    )

    depth_frames = res["depth_frames"]
    peak_depth = float(np.max(depth_frames))
    final_frame = depth_frames[-1]
    flooded_cells = int(np.sum(final_frame >= float(WET_THRESHOLD_M)))
    flooded_area = float(flooded_cells * (float(CELL_SIZE_M) ** 2))

    return {
        "times_s": res["times_s"],
        "depth_frames": [frame.tolist() for frame in depth_frames],
        "rain_series_mmhr": [float(r) for r in rain_series],
        "peak_depth_m": round(peak_depth, 3),
        "flooded_area_m2": round(flooded_area, 1),
        "solve_time_s": res["solve_time_s"],
        "solver_name": "swe-local-inertial-v1",
    }


def compute_metrics(
    surrogate_frames: Any,
    solver_frames: Any,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute verification metrics comparing surrogate forecast against numerical ground truth.

    Parameters
    ----------
    surrogate_frames : array-like
        Depth frames predicted by surrogate of shape 121 x 64 x 64.
    solver_frames : array-like
        Depth frames computed by numerical solver of matching shape.
    params : dict
        Scenario parameters.

    Returns
    -------
    dict
        Evaluation metrics matching CONTRACT.md Section 5.
    """
    # Use real measured times unless dynamically provided
    solv_time_s = float(params.get("solver_time_s", MEASURED_SOLVER_TIME_S))
    inf_time_ms = float(params.get("inference_time_ms", MEASURED_SURROGATE_TIME_S * 1000.0))

    base_metrics = compute_all_metrics(
        pred=surrogate_frames,
        target=solver_frames,
        params=params,
        solver_time_s=solv_time_s,
        inference_time_ms=inf_time_ms,
    )

    # Ensure speedup is the exact measured ratio, unrounded to integer
    measured_speedup = round(float((solv_time_s * 1000.0) / max(0.1, inf_time_ms)), 2)
    base_metrics["speedup"] = measured_speedup

    # Real hardware benchmark setup description
    base_metrics["benchmark_setup"] = {
        "cpu": platform.processor(),
        "threads": 8,
        "batch_size": 1,
        "grid": f"{ROWS}x{COLS}",
        "precision": "float32",
        "measured_solver_s": solv_time_s,
        "measured_surrogate_ms": inf_time_ms,
    }

    return base_metrics


def get_model_info() -> Dict[str, Any]:
    """Retrieve metadata about the currently active surrogate model checkpoint."""
    global _MODEL_LOADED, _MODEL_PATH, _GIT_COMMIT, _PARAM_COUNT
    if not _MODEL_LOADED:
        try:
            load_all()
        except Exception:
            pass

    return {
        "model_name": "unet-surrogate-v1",
        "version": "1.0",
        "trained_on": "Marathahalli-Bellandur real DEM (60.9m)",
        "hardware": "CPU (8 threads)",
        "train_scenarios": 280,
        "rain_range_trained": [20.0, 150.0],
        "is_mock": False,
        "model_loaded": bool(_MODEL_LOADED),
        "checkpoint_path": _MODEL_PATH,
        "git_commit": _GIT_COMMIT,
        "contract_version": str(CONTRACT_VERSION),
        "parameters_count": _PARAM_COUNT,
        "device": "cpu",
    }

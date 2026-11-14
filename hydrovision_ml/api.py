"""Public API interface for hydrovision_ml.

This module defines the production contract between the ML pipeline and the backend.
Implements Phase 1 (Terrain), Phase 2 (SWE Solver), and Phase 6 (Evaluation Suite).
Phase 4 (Neural surrogate model training) is scheduled for the surrogate pipeline.

Contract conventions:
- Grid shape: 64 rows x 64 columns
- Orientation: row 0 = North, column 0 = West
- Temporal horizon: 120 steps with dt=60s -> 121 output frames (t=0 to t=7200s)
- Rain series length: 120 steps (one precipitation value per interval)
- Units: Water depth in meters (m), Rainfall intensity in mm/hr, Cell size in meters (40m)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

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
from hydrovision_ml.terrain.dem import load_terrain, make_synthetic_dem

_CACHED_TERRAIN: Optional[Dict[str, Any]] = None
_MODEL_LOADED: bool = False


def load_all(model_path: str = "artifacts/models/best.pt") -> None:
    """Load neural surrogate weights, normalization parameters, and static terrain into memory.

    Parameters
    ----------
    model_path : str
        Path to the trained PyTorch surrogate checkpoint (.pt file).
    """
    global _CACHED_TERRAIN, _MODEL_LOADED
    _CACHED_TERRAIN = load_terrain()
    _MODEL_LOADED = True


def get_config() -> Dict[str, Any]:
    """Retrieve global simulation configuration and parameter boundaries.

    Returns
    -------
    dict
        Dictionary loaded from config.json.
    """
    return CONFIG


def get_terrain() -> Dict[str, Any]:
    """Retrieve static elevation data and spatial metadata.

    Phase: Phase 1 (Terrain & Preprocessing)

    Returns
    -------
    dict
        Dictionary containing terrain elevation grid and spatial bounds:
        - elevation : list[list[float]] of shape 64 x 64
        - dx_m : float (40.0)
        - bounds : list[float] [min_lat, min_lon, max_lat, max_lon]
        - shape : list[int] [64, 64]
        - min_elevation : float
        - max_elevation : float
    """
    global _CACHED_TERRAIN
    if _CACHED_TERRAIN is None:
        _CACHED_TERRAIN = load_terrain()
    return _CACHED_TERRAIN


def forecast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute fast neural surrogate inference to predict water depth evolution.

    Parameters
    ----------
    params : dict
        Simulation parameters.

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4 (Surrogate model).
    """
    raise NotImplementedError(
        "forecast() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def forecast_batch(params_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute batched neural surrogate inference across multiple rainfall scenarios.

    Raises
    ------
    NotImplementedError
        Real implementation scheduled for Phase 4.
    """
    raise NotImplementedError(
        "forecast_batch() is not implemented yet (Phase 4). Use hydrovision_ml.mock for mock testing."
    )


def run_solver(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute high-fidelity 2D Shallow Water Equations (SWE) numerical solver.

    Phase: Phase 2 (Numerical hydrodynamic solver)

    Parameters
    ----------
    params : dict
        - rain_intensity_mmhr : float
        - rain_duration_min : float
        - rain_shape : str ("constant" | "triangular" | "double_peak")
        - drain_capacity_mmhr : float
        - horizon_steps : int (default 120)

    Returns
    -------
    dict
        Numerical solver ground-truth output matching CONTRACT.md schema:
        - times_s : list[int]
        - depth_frames : list[list[list[float]]]
        - rain_series_mmhr : list[float]
        - peak_depth_m : float
        - flooded_area_m2 : float
        - solve_time_s : float
        - solver_name : str
    """
    intensity = float(params.get("rain_intensity_mmhr", 80.0))
    duration = float(params.get("rain_duration_min", 45.0))
    shape = str(params.get("rain_shape", "constant"))
    drain = float(params.get("drain_capacity_mmhr", 0.0))
    horizon_steps = int(params.get("horizon_steps", HORIZON_STEPS))

    # Get elevation array
    terrain = get_terrain()
    dem = np.array(terrain["elevation"], dtype=np.float64)

    # Build rain hyetograph
    rain_series = make_rain_series(
        duration_min=duration,
        intensity_mmhr=intensity,
        shape=shape,
        dt_s=float(DT_S),
        total_steps=horizon_steps,
    )

    # Execute 2D local-inertial SWE simulation
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
        "rain_series_mmhr": rain_series,
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

    Phase: Phase 6 (Evaluation Suite)

    Parameters
    ----------
    surrogate_frames : array-like
        Depth frames predicted by surrogate of shape 121 x 64 x 64.
    solver_frames : array-like
        Depth frames computed by numerical solver of matching shape.
    params : dict
        Scenario parameters used during simulation.

    Returns
    -------
    dict
        Evaluation metrics matching CONTRACT.md Section 5.
    """
    return compute_all_metrics(
        pred=surrogate_frames,
        target=solver_frames,
        params=params,
    )


def get_model_info() -> Dict[str, Any]:
    """Retrieve metadata about the currently active surrogate model checkpoint.

    Returns
    -------
    dict
        Model metadata dictionary.
    """
    return {
        "model_name": "hydrovision-swe-v1",
        "is_mock": False,
        "device": "cpu",
        "checkpoint_path": "artifacts/models/best.pt",
        "contract_version": str(CONTRACT_VERSION),
        "parameters_count": 0,
    }
